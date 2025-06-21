# api/spotify_search.py
import json, asyncio, os, requests, base64, urllib.request, urllib.parse
import random
from datetime import datetime
from typing import Union, List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
import sys
import time
from dataclasses import asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load environment variables from .env file
from dotenv import load_dotenv
# Correctly load .env.local from the backend directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env.local'))

# Add the search_library directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
search_lib_dir = os.path.join(backend_dir, 'search_library')
sys.path.insert(0, backend_dir)

from search_library.search import search_library
from search_library.types import Song as SearchSong, RawSong
from search_library.clients import get_client
from search_library.prompts import get_song_metadata_query
from search_library.clients import TextPrompt

# Import utility functions from utils.py
from utils import (
    get_lyrics,
    get_song_metadata,  
    get_songs_from_playlists,
    fetch_already_processed_enriched_songs,
    save_enriched_songs_to_db,
    enrich_songs,
    get_playlist_names,
    refresh_access_token,
    SET_MAX_SONGS_FORR_DEBUG,
    SKIP_EXPENSIVE_STEPS,
    SKIP_SUPABASE_CACHE
)

# Environment variables
anthropic_key = os.getenv('ANTHROPIC_API_KEY')
openai_key = os.getenv('OPENAI_API_KEY')
supabase_url = os.getenv('SUPABASE_URL')
supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

app = FastAPI()                 # <- Vercel will pick this up
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[ "X-Experimental-Stream-Data"],  # this is needed for streaming data header to be read by the client
)

# Pydantic models for request validation
class MusicRecord(BaseModel):
    song_link: Union[str, None] = None
    song_metadata: Union[str, None] = None
    lyrics: Union[str, None] = None
    name: str
    artist: str

class UpdateTableRequest(BaseModel):
    tableName: str
    data: Union[List[MusicRecord], MusicRecord]

class SpotifyRefreshRequest(BaseModel):
    refresh_token: str

@app.post("/api/update-table")
async def update_table(request: UpdateTableRequest):
    """Insert music data into Supabase tables"""
    try:
        # Initialize Supabase client
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        # Validate environment variables
        if not supabase_url or not supabase_service_key:
            raise HTTPException(
                status_code=500, 
                detail={
                    'error': 'Missing Supabase configuration',
                    'details': 'Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables'
                }
            )
        
        supabase: Client = create_client(supabase_url, supabase_service_key)
        
        # Convert data to array format
        data_array = request.data if isinstance(request.data, list) else [request.data]
        
        if len(data_array) == 0:
            raise HTTPException(
                status_code=400,
                detail={
                    'error': 'No data provided',
                    'details': 'Data array cannot be empty'
                }
            )
        
        # Convert Pydantic models to dictionaries for Supabase
        records_to_insert = []
        for record in data_array:
            if isinstance(record, MusicRecord):
                record_dict = record.model_dump(exclude_none=True)
                records_to_insert.append(record_dict)
            else:
                records_to_insert.append(record)
        
        # Insert data into Supabase table
        try:
            response = supabase.table(request.tableName).insert(records_to_insert).execute()
            inserted_data = response.data
            
            return {
                'success': True,
                'message': f'Successfully inserted {len(inserted_data)} music record(s)',
                'data': inserted_data,
                'timestamp': datetime.now().isoformat(),
                'validated_fields': ['song_link', 'song_metadata', 'lyrics', 'name', 'artist']
            }
            
        except Exception as supabase_error:
            raise HTTPException(
                status_code=400,
                detail={
                    'error': 'Database error',
                    'details': str(supabase_error)
                }
            )
            
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'Internal server error',
                'details': str(error)
            }
        )

@app.get("/api/spotify/playlists")
async def get_user_playlists(authorization: str = Header(...), refresh_token: Union[str, None] = Header(None, alias="refresh-token")):
    """Get user's Spotify playlists"""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Unauthorized")

    access_token = authorization.split(' ')[1]

    try:
        response = requests.get(
            'https://api.spotify.com/v1/me/playlists?limit=50',
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
        )

        if response.status_code == 401 and refresh_token:
            try:
                new_token = refresh_access_token(refresh_token)
                response = requests.get(
                    'https://api.spotify.com/v1/me/playlists?limit=50',
                    headers={
                        'Authorization': f'Bearer {new_token}',
                        'Content-Type': 'application/json'
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=401, detail="Failed to refresh access token")

        if not response.ok:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch library")

        return response.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/spotify/playlist/{playlist_id}")
async def get_playlist(playlist_id: str, authorization: str = Header(...)):
    """Get a specific Spotify playlist by ID"""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Unauthorized")

    access_token = authorization.split(' ')[1]

    try:
        response = requests.get(
            f'https://api.spotify.com/v1/playlists/{playlist_id}',
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
        )

        if not response.ok:
            raise HTTPException(status_code=response.status_code, detail=f"Failed to fetch playlist: {response.status_code}")

        return response.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/test_ping")
async def test_ping():
    async def event_stream():
        total = 10
        for i in range(total + 1):
            data = f"data: {json.dumps({'type':'progress','processed':i,'total':total})}\n\n"
            yield data
            await asyncio.sleep(0.25)                 # simulate work
        
        final_data = f"data: {json.dumps({'type':'results','results':['Track A','Track B']})}\n\n"
        yield final_data

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # CORS for your Next.js front-end
            "Access-Control-Allow-Origin":  "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Refresh-Token",
            "X-Experimental-Stream-Data": "true"
        },
    )

def get_progress_update_copy(processed: int, total: int, song: SearchSong):
    schemas = [
        "Cannoli is listening to your music...",
        f"Just listened to {song.name} by {', '.join(song.artists)}! So good",
        "Cannoli is taking a nap!",
        "Cannoli is eating a snack!",
        f"I'm {processed} songs in!",

        *[f"Cannoli has listened to {processed} out of {total} new songs..."] * 10,
    ]
    return random.choice(schemas)

@app.get("/api/spotify_search")
async def spotify_search(
    query: str = Query(..., description="Search query for songs"),
    authorization: str = Header(...),
    refresh_token: str = Header(None, alias="refresh-token")
):
    """Search user's Spotify library for songs matching the query with streaming results"""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Unauthorized")

    access_token = authorization.split(' ')[1]
    
    if not query:
        raise HTTPException(status_code=400, detail="Missing query parameter")

    async def event_stream():
        try:
            # Emit explicit start event to reset frontend progress
            yield f"data: {json.dumps({'type': 'start', 'message': 'Starting search...'})}\n\n"
            await asyncio.sleep(0.1)
            
            # Emit status update
            yield f"data: {json.dumps({'type': 'status', 'message': 'Fetching playlists...'})}\n\n"
            await asyncio.sleep(0.1)

            # Get user's playlists
            playlists_data, updated_access_token = get_playlist_names(access_token, refresh_token)
            print(f"[spotify_search] Found {len(playlists_data['items'])} playlists")
            
            playlist_count = len(playlists_data["items"])
            yield f"data: {json.dumps({'type': 'status', 'message': f'Found {playlist_count} playlists. Extracting songs...'})}\n\n"
            await asyncio.sleep(0.1)
            
            # Get songs from playlists
            raw_songs = get_songs_from_playlists(playlists_data, updated_access_token, query)
            print(f"[spotify_search] Found {len(raw_songs)} total songs")
            
            song_count = len(raw_songs)
            yield f"data: {json.dumps({'type': 'status', 'message': f'Found {song_count} songs. Checking database...'})}\n\n"
            await asyncio.sleep(0.1)
            
            # Check database for already processed songs
            if not SKIP_SUPABASE_CACHE:
                already_processed_enriched_songs, unprocessed_raw_songs = fetch_already_processed_enriched_songs(raw_songs)
            else:
                already_processed_enriched_songs, unprocessed_raw_songs = [], raw_songs
                
            print(f"[spotify_search] Found {len(already_processed_enriched_songs)} already processed songs")
            print(f"[spotify_search] Found {len(unprocessed_raw_songs)} unprocessed songs")
            print(f"[spotify_search] Found {len(raw_songs)} total songs")

            # Calculate total progress steps: song processing + LLM search + result processing
            total_progress_steps = len(unprocessed_raw_songs + already_processed_enriched_songs) + 2  # +1 for LLM search
            
            # Emit initial progress
            yield f"data: {json.dumps({'type': 'progress', 'processed': 0, 'total': total_progress_steps, 'message': f'Cannoli is listening to your music...'})}\n\n"
            await asyncio.sleep(0.1)

            # Process unprocessed songs with progress updates
            enriched_songs = []
            total_enrichment_tokens = {
                'total_input_tokens': 0,
                'total_output_tokens': 0,
                'total_requests': 0
            }
            
            if len(unprocessed_raw_songs) > 0:
                print(f"[spotify_search] Enriching {len(unprocessed_raw_songs)} songs")
                last_yield_time = time.time()
                for song, token_usage in enrich_songs(unprocessed_raw_songs):                
                    enriched_songs.append(song)
                    # Update token usage
                    total_enrichment_tokens = token_usage

                    current_time = time.time()
                    if current_time - last_yield_time >= 1:
                        progress_update_copy = get_progress_update_copy(len(enriched_songs), total_progress_steps, song)
                        yield f"data: {json.dumps({'type': 'progress', 'processed': len(enriched_songs), 'total': total_progress_steps, 'message': progress_update_copy})}\n\n"
                        await asyncio.sleep(0.1)
                        last_yield_time = current_time
                    else:
                        yield f"data: {json.dumps({'type': 'progress', 'processed': len(enriched_songs), 'total': total_progress_steps})}\n\n"
                        await asyncio.sleep(0.1)
                
                # Save newly enriched songs to database
                if not SKIP_SUPABASE_CACHE:
                    save_enriched_songs_to_db(enriched_songs)
            else:
                print(f"[spotify_search] No unprocessed songs found, using already processed songs")
                # Simulate progress for already processed songs to show smooth progress bar
                batch_size = max(1, len(already_processed_enriched_songs) // 10)  # Show ~10 progress updates
                for i in range(0, len(already_processed_enriched_songs), batch_size):
                    current_processed = min(i + batch_size, len(already_processed_enriched_songs))
                    song = already_processed_enriched_songs[min(i, len(already_processed_enriched_songs) - 1)]
                    progress_update_copy = get_progress_update_copy(current_processed, total_progress_steps, song)
                    yield f"data: {json.dumps({'type': 'progress', 'processed': current_processed, 'total': total_progress_steps, 'message': progress_update_copy})}\n\n"
                    await asyncio.sleep(0.2)  # Slightly longer delay to make progress visible

            
            # Combine all enriched songs
            all_enriched_songs = already_processed_enriched_songs + enriched_songs
            
            yield f"data: {json.dumps({'type': 'status', 'message': 'Cannoli is searching through your music...'})}\n\n"
            await asyncio.sleep(0.1)
            
            # Update progress for LLM search step
            llm_search_progress = len(all_enriched_songs) + 1
            yield f"data: {json.dumps({'type': 'progress', 'processed': llm_search_progress, 'total': total_progress_steps, 'message': f'Cannoli is analyzing your music...'})}\n\n"
            await asyncio.sleep(0.1)
            
            # Search through the enriched songs using LLM
            llm_client = get_client("openai-direct", model_name="gpt-4o-mini")
            if SKIP_EXPENSIVE_STEPS:
                relevant_songs, search_token_usage = all_enriched_songs[:3], {}
                time.sleep(3)
            else:
                relevant_songs, search_token_usage = search_library(llm_client, all_enriched_songs, query, n=3, chunk_size=100, verbose=True)

            print(f"[spotify_search] Done searching")
            
            yield f"data: {json.dumps({'type': 'status', 'message': 'Processing results...'})}\n\n"
            await asyncio.sleep(0.1)
            
            # Combine token usage from both processes
            combined_token_usage = {
                'total_input_tokens': search_token_usage.get('total_input_tokens', 0) + total_enrichment_tokens.get('total_input_tokens', 0),
                'total_output_tokens': search_token_usage.get('total_output_tokens', 0) + total_enrichment_tokens.get('total_output_tokens', 0),
                'total_requests': search_token_usage.get('total_requests', 0) + total_enrichment_tokens.get('total_requests', 0),
                'requests_breakdown': search_token_usage.get('requests_breakdown', []),
                'enrichment_requests': total_enrichment_tokens.get('total_requests', 0),
                'search_requests': search_token_usage.get('total_requests', 0),
                'enrichment_input_tokens': total_enrichment_tokens.get('total_input_tokens', 0),
                'enrichment_output_tokens': total_enrichment_tokens.get('total_output_tokens', 0),
                'search_input_tokens': search_token_usage.get('total_input_tokens', 0),
                'search_output_tokens': search_token_usage.get('total_output_tokens', 0)
            }
            
            print(f"[spotify_search] Token usage summary:")
            print(f"  Enrichment: {total_enrichment_tokens}")
            print(f"  Search: {search_token_usage}")
            print(f"  Combined: {combined_token_usage}")
            
            # Convert Song objects to dictionaries for JSON serialization
            result_dicts = []
            for song in relevant_songs:
                song_dict = asdict(song)
                # Convert artists list to single artist string for frontend compatibility
                song_dict['artist'] = ', '.join(song.artists) if song.artists else ''
                # Ensure reasoning field is present
                song_dict['reasoning'] = getattr(song, 'reasoning', '')
                result_dicts.append(song_dict)

            # Emit final results
            final_data = {
                'type': 'results',
                'results': [asdict(song) for song in relevant_songs],
                'token_usage': combined_token_usage
            }
            yield f"data: {json.dumps(final_data)}\n\n"
            print(f"[spotify_search] Done streaming")

        except Exception as e:
            import traceback
            traceback.print_exc()
            # Emit error event
            error_data = {
                'type': 'error',
                'error': str(e)
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, refresh-token",
            "X-Experimental-Stream-Data": "true",
            "X-Accel-Buffering": "no"
        },
    )

@app.post("/api/spotify/refresh")
async def refresh_spotify_token(request: SpotifyRefreshRequest):
    """Refresh a Spotify access token given a refresh token"""
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="Server mis-configuration: missing Spotify credentials")

    try:
        auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        
        data = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": request.refresh_token
        }).encode()
        
        req = urllib.request.Request(
            "https://accounts.spotify.com/api/token",
            data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {auth_header}",
            },
        )

        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                raise HTTPException(status_code=response.status, detail="Failed to refresh token")

            data = json.loads(response.read().decode())
            return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing token: {str(e)}")
