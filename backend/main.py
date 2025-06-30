# api/spotify_search.py
import copy
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

from search_library.search import search_library, vector_search_library, generate_many_song_reasoning
from search_library.types import Song as SearchSong, RawSong
from search_library.clients import get_client
from search_library.prompts import get_song_metadata_query
from search_library.clients import TextPrompt

# Import instant search functionality
from instant_llm import instant_search

# Import utility functions from utils.py
from utils import (
    ADD_RERANKER_TO_VECTOR_SEARCH,
    get_lyrics,
    get_song_metadata,  
    get_songs_from_playlists,
    fetch_already_processed_enriched_songs,
    save_enriched_songs_to_db,
    enrich_songs,
    get_playlist_names,
    refresh_access_token,
    SKIP_EXPENSIVE_STEPS,
    SKIP_SUPABASE_CACHE
)

# MusixMatch scraper endpoints
from musixmatch_scraper import MusixMatchScraper

# Initialize MusixMatch scraper
musixmatch_scraper = MusixMatchScraper()

def get_user_id(access_token) -> str:
    """Get the user ID from the access token"""
    user_response = requests.get(
        'https://api.spotify.com/v1/me',
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    )
    if not user_response.ok:
        raise HTTPException(status_code=user_response.status_code, detail="Failed to fetch user profile")
    user_id = user_response.json().get('id')
    if not user_id:
        raise HTTPException(status_code=400, detail="No user ID found")
    return user_id

def update_users_songs_join_table(user_id: str, raw_songs: list[RawSong]) -> None:
    """Update the users_songs join table with new songs for the user"""
    try:            
        print(f"[update_users_songs_join_table] Processing songs for user: {user_id}")
        
        # Initialize Supabase client
        supabase: Client = create_client(supabase_url, supabase_service_key)
        
        # Get existing song IDs for this user from users_songs table
        existing_songs_response = supabase.table('users_songs').select('song_id').eq('user_id', user_id).execute()
        existing_song_ids = set()
        if existing_songs_response.data:
            existing_song_ids = {song['song_id'] for song in existing_songs_response.data}
            
        print(f"[update_users_songs_join_table] Found {len(existing_song_ids)} existing songs for user")
        
        # Find new songs that aren't in the existing list
        new_songs = []
        for raw_song in raw_songs:
            song_id = raw_song.id
            if song_id and song_id not in existing_song_ids:
                new_songs.append({
                    'user_id': user_id,
                    'song_id': song_id
                })
                
        print(f"[update_users_songs_join_table] Found {len(new_songs)} new songs to add")
        
        # Insert new songs into users_songs table
        if new_songs:
            insert_response = supabase.table('users_songs').insert(new_songs).execute()
            print(f"[update_users_songs_join_table] Successfully inserted {len(new_songs)} new songs")
        else:
            print(f"[update_users_songs_join_table] No new songs to insert")
            
    except Exception as e:
        print(f"[update_users_songs_join_table] Error: {e}")
        # Don't raise exception - this is not critical for the main flow

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

class MusixMatchLyricsRequest(BaseModel):
    artist_name: str
    track_name: str

class MusixMatchUrlRequest(BaseModel):
    lyrics_url: str

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

@app.post("/api/login-or-create-user")
async def login_or_create_user(authorization: str = Header(...), refresh_token: Union[str, None] = Header(None, alias="refresh-token")):
    """Get user info from Spotify API and save/update user in Supabase"""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Unauthorized")

    access_token = authorization.split(' ')[1]

    try:
        # Get user info from Spotify API
        response = requests.get(
            'https://api.spotify.com/v1/me',
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
        )

        # Handle token refresh if needed
        if response.status_code == 401 and refresh_token:
            try:
                new_token = refresh_access_token(refresh_token)
                response = requests.get(
                    'https://api.spotify.com/v1/me',
                    headers={
                        'Authorization': f'Bearer {new_token}',
                        'Content-Type': 'application/json'
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=401, detail="Failed to refresh access token")

        if not response.ok:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch user profile")

        user_data = response.json()
        
        # Initialize Supabase client for vault operations
        if not supabase_url or not supabase_service_key:
            raise HTTPException(
                status_code=500, 
                detail={'error': 'Missing Supabase configuration'}
            )
        
        supabase: Client = create_client(supabase_url, supabase_service_key)

        # Check if user already exists - early exit if they do
        existing_user_response = supabase.table('users').select('*').eq('id', user_data.get('id')).execute()
        if existing_user_response.data and len(existing_user_response.data) > 0:
            existing_user = existing_user_response.data[0]
            print(f"[login-or-create-user] User already exists: {existing_user.get('id')}")
            return {
                'success': True,
                'user_id': existing_user.get('id'),
                'message': 'User already exists - logged in successfully',
                'user': existing_user,
                'timestamp': datetime.now().isoformat()
            }
        
        # Store refresh token in Supabase Vault if provided
        vault_secret_id = None
        if refresh_token:
            try:
                # Use direct SQL to call vault.create_secret function
                secret_name = f"spotify_refresh_token_{user_data.get('id')}"
                secret_description = f"Spotify refresh token for user {user_data.get('id')}"
                
                # Call our wrapper function that calls vault.create_secret
                vault_response = supabase.rpc('create_vault_secret', {
                    'secret': refresh_token,
                    'name': secret_name,
                    'description': secret_description
                }).execute()
                print(f"[login-or-create-user] Vault response: {vault_response.data}")
                vault_secret_id = vault_response.data if vault_response.data else None
            except Exception as vault_error:
                print(f"Warning: Failed to store refresh token in vault: {vault_error}")
                # Continue without vault storage - this is not a critical failure
        else:
            print(f"Warning: No refresh token provided")
        
        # Extract user information
        user_info = {
            'id': user_data.get('id'),
            'display_name': user_data.get('display_name'),
            'email': user_data.get('email'),
            'country': user_data.get('country'),
            'vault_secret_id': vault_secret_id,
        }
        
        try:
            # Try to insert user (upsert to handle existing users)
            response = supabase.table('users').upsert(user_info, on_conflict='id').execute()
            saved_user = response.data[0] if response.data else user_info
            
            return {
                'success': True,
                'user_id': user_info.get('id'),
                'message': 'User successfully logged in/created',
                'user': saved_user,
                'timestamp': datetime.now().isoformat()
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
            yield f"data: {json.dumps({'type': 'start', 'message': 'Listening to new songs...'})}\n\n"
            await asyncio.sleep(0.1)
            
            # Try instant search first for lyric-heavy queries
            yield f"data: {json.dumps({'type': 'status', 'message': 'Checking for instant match...'})}\n\n"
            await asyncio.sleep(0.1)
            
            instant_result, instant_token_usage = instant_search(query)
            
            if instant_result:
                # We found an instant match! Return it immediately
                print(f"[spotify_search] Found instant match: {instant_result.name} by {', '.join(instant_result.artists)}")
                
                yield f"data: {json.dumps({'type': 'status', 'message': 'Found instant match!'})}\n\n"
                await asyncio.sleep(0.1)
                
                # Convert to dictionary format for frontend
                song_dict = asdict(instant_result)
                song_dict['artist'] = ', '.join(instant_result.artists) if instant_result.artists else ''
                song_dict['reasoning'] = getattr(instant_result, 'reasoning', '')
                
                # Emit final results with instant match
                final_data = {
                    'type': 'results',
                    'results': [song_dict],
                    'token_usage': {
                        'total_input_tokens': instant_token_usage.get('total_input_tokens', 0),
                        'total_output_tokens': instant_token_usage.get('total_output_tokens', 0),
                        'total_requests': instant_token_usage.get('total_requests', 0),
                        'instant_search': True,
                        'instant_input_tokens': instant_token_usage.get('total_input_tokens', 0),
                        'instant_output_tokens': instant_token_usage.get('total_output_tokens', 0),
                        'instant_requests': instant_token_usage.get('total_requests', 0)
                    }
                }
                yield f"data: {json.dumps(final_data)}\n\n"
                print(f"[spotify_search] Instant search completed successfully")
                return
            
            # No instant match found, continue with full search
            yield f"data: {json.dumps({'type': 'status', 'message': 'No instant match found. Searching your playlists...'})}\n\n"
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

            # Calculate total progress steps
            total_progress_steps = len(unprocessed_raw_songs)
            
            # Emit initial progress
            yield f"data: {json.dumps({'type': 'progress', 'processed': 0, 'total': total_progress_steps, 'message': f'Cannoli is listening to your music...'})}\n\n"
            await asyncio.sleep(0.1)

            # get user id
            user_id = get_user_id(access_token)

            # update users_songs join table
            update_users_songs_join_table(user_id, raw_songs)

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
                    if current_time - last_yield_time >= 4:
                        progress_update_copy = get_progress_update_copy(len(enriched_songs), total_progress_steps, song)
                        yield f"data: {json.dumps({'type': 'progress', 'processed': len(enriched_songs), 'total': total_progress_steps, 'message': progress_update_copy})}\n\n"
                        await asyncio.sleep(0.1)
                        last_yield_time = current_time
                    else:
                        yield f"data: {json.dumps({'type': 'progress', 'processed': len(enriched_songs), 'total': total_progress_steps})}\n\n"
                        await asyncio.sleep(0.1)
                
                # Save newly enriched songs to database
                # NOTE: Individual songs are now saved to database during enrichment process
                # No need for batch save anymore - this prevents data loss if process crashes
                # if not SKIP_SUPABASE_CACHE:
                #     save_enriched_songs_to_db(enriched_songs)
            #else:
                #print(f"[spotify_search] No unprocessed songs found, using already processed songs")
                ## Simulate progress for already processed songs to show smooth progress bar
                #batch_size = max(1, len(already_processed_enriched_songs) // 10)  # Show ~10 progress updates
                #for i in range(0, len(already_processed_enriched_songs), batch_size):
                #   current_processed = min(i + batch_size, len(already_processed_enriched_songs))
                #    song = already_processed_enriched_songs[min(i, len(already_processed_enriched_songs) - 1)]
                #    progress_update_copy = get_progress_update_copy(current_processed, total_progress_steps, song)
                #     yield f"data: {json.dumps({'type': 'progress', 'processed': current_processed, 'total': total_progress_steps, 'message': progress_update_copy})}\n\n"
                #    await asyncio.sleep(0.2)  # Slightly longer delay to make progress visible

            
            # Combine all enriched songs
            all_enriched_songs = already_processed_enriched_songs + enriched_songs
            
            yield f"data: {json.dumps({'type': 'completion', 'prev_stage': 'enrichment'})}\n\n"
            yield f"data: {json.dumps({'type': 'status', 'message': 'Cannoli is searching through your music...'})}\n\n"
            await asyncio.sleep(0.1)
            
            # Search through the songs using vector similarity search
            if SKIP_EXPENSIVE_STEPS:
                relevant_songs, search_token_usage = copy.deepcopy(all_enriched_songs[:10]), {}
                for song in relevant_songs:
                    song.reasoning = f"this is why I think {song.name} by {', '.join(song.artists)} is relevant to the query"
                time.sleep(3)
            else:
                start_time = time.time()
                relevant_songs, search_token_usage = vector_search_library(
                    user_id=user_id,
                    user_query=query, 
                    n=20, 
                    match_threshold=0.5,  # Adjust this threshold as needed
                    generate_song_reasoning=False,
                    verbose=True
                )
                end_time = time.time()
                print(f"[spotify_search] Vector search result count: {len(relevant_songs)}, time taken: {end_time - start_time} seconds")
                
                # now run LLM search on the remaining songs
                if ADD_RERANKER_TO_VECTOR_SEARCH:
                    llm_client = get_client("openai-direct", model_name="gpt-4o-mini")
                    start_time = time.time()
                    relevant_songs, llm_search_token_usage = search_library(llm_client, relevant_songs, query, n=10, chunk_size=100, generate_song_reasoning=False, verbose=True)
                    end_time = time.time()
                    print(f"[spotify_search] LLM reranker result count: {len(relevant_songs)}, time taken: {end_time - start_time} seconds")
                    # Combine token usage from both vector and LLM search
                    search_token_usage['total_input_tokens'] += llm_search_token_usage.get('total_input_tokens', 0)
                    search_token_usage['total_output_tokens'] += llm_search_token_usage.get('total_output_tokens', 0)
                    search_token_usage['total_requests'] += llm_search_token_usage.get('total_requests', 0)
                    search_token_usage['fallback_llm_search'] = True
                    search_token_usage['llm_search_tokens'] = llm_search_token_usage
                else:
                    print(f"[spotify_search] Skipping LLM reranker")
                
                # Generate reasoning for all relevant songs at once
                yield f"data: {json.dumps({'type': 'status', 'message': 'Generating song explanations...'})}\n\n"
                await asyncio.sleep(0.1)
                
                # Generate reasoning for all songs at once using batch processing
                start_time = time.time()
                relevant_songs, reasoning_token_usage = generate_many_song_reasoning(
                    songs=relevant_songs,
                    user_query=query,
                    similarity_scores=None,  # We don't have individual similarity scores here
                    verbose=True
                )
                end_time = time.time()
                print(f"[spotify_search] Generated reasoning for {len(relevant_songs)} songs, time taken: {end_time - start_time} seconds")
                print(f"[spotify_search] Reasoning token usage: {reasoning_token_usage}")

            print(f"[spotify_search] Done searching")
            
            yield f"data: {json.dumps({'type': 'status', 'message': 'Processing results...'})}\n\n"
            await asyncio.sleep(0.1)
            
            # Combine token usage from all processes (including instant search tokens)
            combined_token_usage = {
                'total_input_tokens': search_token_usage.get('total_input_tokens', 0) + total_enrichment_tokens.get('total_input_tokens', 0) + instant_token_usage.get('total_input_tokens', 0) + reasoning_token_usage.get('total_input_tokens', 0),
                'total_output_tokens': search_token_usage.get('total_output_tokens', 0) + total_enrichment_tokens.get('total_output_tokens', 0) + instant_token_usage.get('total_output_tokens', 0) + reasoning_token_usage.get('total_output_tokens', 0),
                'total_requests': search_token_usage.get('total_requests', 0) + total_enrichment_tokens.get('total_requests', 0) + instant_token_usage.get('total_requests', 0) + reasoning_token_usage.get('total_requests', 0),
                'requests_breakdown': search_token_usage.get('requests_breakdown', []),
                'enrichment_requests': total_enrichment_tokens.get('total_requests', 0),
                'search_requests': search_token_usage.get('total_requests', 0),
                'instant_requests': instant_token_usage.get('total_requests', 0),
                'reasoning_requests': reasoning_token_usage.get('total_requests', 0),
                'enrichment_input_tokens': total_enrichment_tokens.get('total_input_tokens', 0),
                'enrichment_output_tokens': total_enrichment_tokens.get('total_output_tokens', 0),
                'search_input_tokens': search_token_usage.get('total_input_tokens', 0),
                'search_output_tokens': search_token_usage.get('total_output_tokens', 0),
                'instant_input_tokens': instant_token_usage.get('total_input_tokens', 0),
                'instant_output_tokens': instant_token_usage.get('total_output_tokens', 0),
                'reasoning_input_tokens': reasoning_token_usage.get('total_input_tokens', 0),
                'reasoning_output_tokens': reasoning_token_usage.get('total_output_tokens', 0),
                'vector_search': search_token_usage.get('vector_search', False),
                'embedding_tokens': search_token_usage.get('embedding_tokens', {}),
                'reasoning_tokens': search_token_usage.get('reasoning_tokens', {}),
                'fallback_llm_search': search_token_usage.get('fallback_llm_search', False),
                'llm_search_tokens': search_token_usage.get('llm_search_tokens', {}),
                'vector_search_failed': search_token_usage.get('vector_search_failed', False),
                'error': search_token_usage.get('error', '')
            }
            
            print(f"[spotify_search] Token usage summary:")
            print(f"  Instant: {instant_token_usage}")
            print(f"  Enrichment: {total_enrichment_tokens}")
            print(f"  Search: {search_token_usage}")
            print(f"  Reasoning: {reasoning_token_usage}")
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
                'results': result_dicts,
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

@app.post("/musixmatch/get-lyrics")
async def musixmatch_get_lyrics(request: MusixMatchLyricsRequest):
    """Get track lyrics using MusixMatch scraper"""
    try:
        result = musixmatch_scraper.get_track_lyrics(request.artist_name, request.track_name)
        
        if result is None:
            raise HTTPException(
                status_code=404, 
                detail=f"Could not find lyrics for '{request.track_name}' by '{request.artist_name}'"
            )
        
        # Transform the result to match frontend expectations
        return {
            'track_id': result['track'].get('spotify_id', ''),
            'track_name': result['track']['title'],
            'artist_name': result['track']['artist'],
            'album_name': result['album']['title'],
            'lyrics_body': result['lyrics'],
            'lyrics_copyright': '',
            'track_share_url': f"https://www.musixmatch.com/lyrics/{result['track']['artist'].replace(' ', '-')}/{result['track']['title'].replace(' ', '-')}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting lyrics: {str(e)}")

@app.post("/musixmatch/get-track-by-url")
async def musixmatch_get_track_by_url(request: MusixMatchUrlRequest):
    """Get track information from a direct MusixMatch lyrics URL"""
    try:
        result = musixmatch_scraper.get_track_by_url(request.lyrics_url)
        
        if result is None:
            raise HTTPException(
                status_code=404, 
                detail=f"Could not find track information from URL: {request.lyrics_url}"
            )
        
        # Transform the result to match frontend expectations
        return {
            'track_id': result['track'].get('spotify_id', ''),
            'track_name': result['track']['title'],
            'artist_name': result['track']['artist'],
            'album_name': result['album']['title'],
            'lyrics_body': result['lyrics'],
            'lyrics_copyright': '',
            'track_share_url': request.lyrics_url
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting track by URL: {str(e)}")
