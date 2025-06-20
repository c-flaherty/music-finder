# api/spotify_search.py
import json, asyncio, os, requests, base64, urllib.request, urllib.parse
import random
from datetime import datetime
from typing import Union, List, Dict, Any
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

SET_MAX_SONGS_FORR_DEBUG: int | None = 50

# --------------------------- Lyrics helper ---------------------------
def get_lyrics(song_name: str, artist_names: list[str]) -> str:
    """Fetch plain-text lyrics from Genius for the given song/artist."""
    search_query = f"{song_name} {', '.join(artist_names)}"
    print(f"[DEBUG] Searching for lyrics for: {search_query}")
    
    headers = {
        'accept': '*/*',
        'content-type': 'application/json',
        'x-genius-ios-version': '7.7.0',
        'x-genius-logged-out': 'true',
        'accept-language': 'en-US,en;q=0.9',
        'user-agent': 'Genius/1267 CFNetwork/3826.500.131 Darwin/24.5.0'
    }
    # Never send Authorization header for Genius API requests

    proxies = None
    verify_ssl = True
    use_proxy = False
    isp_username = os.getenv('BD_ISP_USERNAME')
    isp_password = os.getenv('BD_ISP_PASSWORD')
    print(f"[DEBUG] ISP USER: {isp_username}, ISP PASS: {'set' if isp_password else 'not set'}")
    if isp_username and isp_password:
        proxy_url = f'http://{isp_username}:{isp_password}@brd.superproxy.io:22225'
        proxies = {'http': proxy_url, 'https': proxy_url}
        verify_ssl = False
        use_proxy = True
        print(f"[DEBUG] Using ISP proxy: {proxy_url}")

    search_url = f"https://api.genius.com/search?q={search_query}"
    print(f"[DEBUG] Search URL: {search_url}")
    try:
        search_response = requests.get(search_url, headers=headers, proxies=proxies, verify=verify_ssl, timeout=10)
        print(f"[DEBUG] Search response status: {search_response.status_code}")
    except Exception as proxy_error:
        print(f"[DEBUG] Proxy request failed: {proxy_error}")
        if use_proxy:
            search_response = requests.get(search_url, headers=headers, timeout=10)
        else:
            return ""
    if not search_response.ok:
        print(f"[DEBUG] Genius search request failed. Status: {search_response.status_code}, Response: {search_response.text[:200]}")
        return ""
    try:
        search_data = search_response.json()
        print(f"[DEBUG] Search data: {json.dumps(search_data)[:200]}")
    except json.JSONDecodeError:
        print(f"[DEBUG] Genius search returned non-JSON. Status: {search_response.status_code}, Response: {search_response.text[:200]}")
        return ""
    song_id = search_data.get('response', {}).get('hits', [{}])[0].get('result', {}).get('id')
    print(f"[DEBUG] Song ID: {song_id}")
    if not song_id:
        print(f"[DEBUG] No song ID found for {search_query}")
        return ""
    song_url = f"https://api.genius.com/songs/{song_id}?text_format=plain"
    print(f"[DEBUG] Song URL: {song_url}")
    try:
        song_response = requests.get(song_url, headers=headers, proxies=proxies, verify=verify_ssl, timeout=10)
        print(f"[DEBUG] Song response status: {song_response.status_code}")
    except Exception as proxy_error:
        print(f"[DEBUG] Proxy request for song details failed: {proxy_error}")
        if use_proxy:
            song_response = requests.get(song_url, headers=headers, timeout=10)
        else:
            return ""
    if not song_response.ok:
        print(f"[DEBUG] Genius song details request failed. Status: {song_response.status_code}, Response: {song_response.text[:200]}")
        return ""
    try:
        song_data = song_response.json()
        print(f"[DEBUG] Song data: {json.dumps(song_data)[:200]}")
    except json.JSONDecodeError:
        print(f"[DEBUG] Genius song details returned non-JSON. Status: {song_response.status_code}, Response: {song_response.text[:200]}")
        return ""
    lyrics = song_data.get('response', {}).get('song', {}).get('lyrics', {}).get('plain', "")
    print(f"[DEBUG] Lyrics length: {len(lyrics)}")
    if len(lyrics) > 1600:
        lyrics = lyrics[:1600]
    return lyrics

def get_song_metadata(song_name: str, artist_names: list[str]) -> str:
    """Ask LLM with search tool to research the song."""
    llm_client = get_client("openai-direct", model_name="gpt-4o-mini-search-preview", enable_web_search=True)
    prompt = get_song_metadata_query(song_name, artist_names)
    response_tuple = llm_client.generate(
        [[TextPrompt(text=prompt)]], # Note the double brackets
        max_tokens=1000
    )
    response_blocks = response_tuple[0] # This is list[AssistantContentBlock]
    first_block = response_blocks[0] # This is the first AssistantContentBlock
    response_text = first_block.text # This is the text content
    return response_text

def get_songs_from_playlists(playlists_data: Dict, access_token: str, query: str) -> list[RawSong]:
    all_songs = []

    for playlist in playlists_data['items']:
        tracks_response = requests.get(
            f"https://api.spotify.com/v1/playlists/{playlist['id']}/tracks",
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
        )

        if not tracks_response.ok:
            continue

        tracks_data = tracks_response.json()
        
        for item in tracks_data['items']:
            track_data = item.get('track')
            if not track_data or not track_data.get('id'):
                continue

            track = RawSong(
                id=track_data['id'],
                song_link=track_data['external_urls']['spotify'],
                name=track_data['name'],
                artists=[artist['name'] for artist in track_data['artists'] if artist['name'] is not None],
                album=track_data['album']['name'],
            )
            all_songs.append(track)

            if SET_MAX_SONGS_FORR_DEBUG and len(all_songs) >= SET_MAX_SONGS_FORR_DEBUG:
                break
        
        if SET_MAX_SONGS_FORR_DEBUG and len(all_songs) >= SET_MAX_SONGS_FORR_DEBUG:
            break

    # Remove duplicates
    unique_songs = list({song.id: song for song in all_songs}.values())

    # Debug: how many unique songs were collected
    print(f"[spotify_search] Collected {len(unique_songs)} unique tracks from playlists")

    return unique_songs

def enrich_songs(songs: list[RawSong]):
    """Enrich raw songs with lyrics and metadata in parallel, yielding results as they complete."""
    processed_count = 0
    total_count = len(songs)
    lyrics_success_count = 0
    
    def enrich_single_song(song: RawSong) -> SearchSong:
        """Enrich a single song with lyrics and metadata."""
        lyrics = ""  # Initialize lyrics variable
        try:
            ## Commented out for now to test frontend quickly
            # lyrics = get_lyrics(song.name, song.artists)
            # if lyrics:
            #     print(f"[LYRICS SUCCESS] {song.name} - {', '.join(song.artists)}")
            # else:
            #     print(f"[LYRICS FAIL] {song.name} - {', '.join(song.artists)}")
            return SearchSong(
                **song.__dict__,
                lyrics=lyrics,
                song_metadata=""
            )
        except Exception as e:
            print(f"[LYRICS FAIL] {song.name} - {', '.join(song.artists)} (error: {e})")
            return SearchSong(
                **song.__dict__,
                lyrics=lyrics,  # Now lyrics is always defined
                song_metadata=""
            )
    
    if not songs:
        return

    # Process songs in parallel with a reasonable number of workers
    max_workers = min(50, len(songs))
    last_emit_time = time.time()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all enrichment tasks
        future_to_song = {executor.submit(enrich_single_song, song): song for song in songs}
        
        # Collect results as they complete and yield them
        for future in as_completed(future_to_song):
            try:
                enriched_song = future.result()
                if enriched_song.lyrics:
                    lyrics_success_count += 1
                yield enriched_song
            except Exception as e:
                song = future_to_song[future]
                print(f"[LYRICS FAIL] {song.name} - {', '.join(song.artists)} (error: {e})")
                yield SearchSong(
                    **song.__dict__,
                    lyrics="these are some lyrics",
                    song_metadata="this is a song deep-dive"
                )
            
            processed_count += 1
    print(f"[LYRICS SUMMARY] Processed {total_count} songs, got lyrics for {lyrics_success_count} songs.")

def get_playlist_names_internal(access_token: str, refresh_token: str = None) -> tuple[Dict, str]:
    """
    Fetch user's playlists from Spotify API with automatic token refresh if needed.
    """
    playlists_response = requests.get(
        'https://api.spotify.com/v1/me/playlists?limit=50',
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    )

    if playlists_response.status_code == 401 and refresh_token:
        # Token expired, try to refresh
        new_token = refresh_access_token(refresh_token)
        playlists_response = requests.get(
            'https://api.spotify.com/v1/me/playlists?limit=50',
            headers={
                'Authorization': f'Bearer {new_token}',
                'Content-Type': 'application/json'
            }
        )
        access_token = new_token

    if not playlists_response.ok:
        print("=== SPOTIFY API ERROR DEBUG ===")
        print(f"Status Code: {playlists_response.status_code}")
        print(f"Response Headers: {dict(playlists_response.headers)}")
        print(f"Request URL: {playlists_response.url}")
        print(f"Request Headers: Authorization: Bearer {access_token[:20]}..." if access_token else "No access token")
        try:
            print(f"Response JSON: {playlists_response.json()}")
        except:
            print(f"Response Text: {playlists_response.text}")
        print("================================")
        raise Exception(f'Failed to fetch playlists: {playlists_response.status_code}')

    return playlists_response.json(), access_token

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

def refresh_access_token(refresh_token: str) -> str:
    """Refresh Spotify access token using refresh token"""
    client_id = os.getenv('SPOTIFY_CLIENT_ID')
    client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
    auth_string = f"{client_id}:{client_secret}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    
    response = requests.post(
        'https://accounts.spotify.com/api/token',
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f"Basic {auth_header}"
        },
        data={
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
    )

    if not response.ok:
        raise Exception('Failed to refresh access token')

    return response.json()['access_token']

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

@app.post("/api/update-table")
async def update_table(request: UpdateTableRequest):
    """Insert music data into Supabase tables"""
    try:
        # Initialize Supabase client
        supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
        supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        # Validate environment variables
        if not supabase_url or not supabase_service_key:
            raise HTTPException(
                status_code=500, 
                detail={
                    'error': 'Missing Supabase configuration',
                    'details': 'Please set NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables'
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
            # Emit status update
            yield f"data: {json.dumps({'type': 'status', 'message': 'Fetching playlists...'})}\n\n"
            await asyncio.sleep(0.1)

            # Get user's playlists
            playlists_data, updated_access_token = get_playlist_names_internal(access_token, refresh_token)
            print(f"[spotify_search] Found {len(playlists_data['items'])} playlists")
            
            playlist_count = len(playlists_data["items"])
            yield f"data: {json.dumps({'type': 'status', 'message': f'Found {playlist_count} playlists. Extracting songs...'})}\n\n"
            await asyncio.sleep(0.1)
            
            # Get songs from playlists
            raw_songs = get_songs_from_playlists(playlists_data, updated_access_token, query)
            print(f"[spotify_search] Found {len(raw_songs)} total songs")
            
            song_count = len(raw_songs)
            yield f"data: {json.dumps({'type': 'status', 'message': f'Found {song_count} songs. Processing...'})}\n\n"
            await asyncio.sleep(0.1)
            
            # For now, skip database lookup and just process all songs
            already_processed_enriched_songs = []
            unprocessed_raw_songs = raw_songs
            
            # Calculate total progress steps: song processing + LLM search + result processing
            total_progress_steps = len(unprocessed_raw_songs) + 2  # +1 for LLM search
            
            # Emit initial progress
            yield f"data: {json.dumps({'type': 'progress', 'processed': 0, 'total': total_progress_steps, 'message': f'Cannoli is listening to your music...'})}\n\n"
            await asyncio.sleep(0.1)

            
            # Process songs with progress updates (song processing takes most of the progress)
            enriched_songs = []
            perc5_unprocessed_songs_ct = max(len(unprocessed_raw_songs) // 20, 5)
            for song in enrich_songs(unprocessed_raw_songs):
                enriched_songs.append(song)
                if len(enriched_songs) % perc5_unprocessed_songs_ct == 0:

                    # with a 5% chance emit a progress update with the message
                    # "Just listened to song.title by song.artist!"
                    if random.random() < 0.05:
                        yield f"data: {json.dumps({'type': 'progress', 'processed': len(enriched_songs), 'total': total_progress_steps, 'message': f'Just listened to {song.name} by {', '.join(song.artists)}...'})}\n\n"
                        await asyncio.sleep(0.1)
                    else:
                        yield f"data: {json.dumps({'type': 'progress', 'processed': len(enriched_songs), 'total': total_progress_steps, 'message': f'Cannoli has listened to {len(enriched_songs)} out of {len(unprocessed_raw_songs)} new songs...'})}\n\n"
                        await asyncio.sleep(0.1)
            
            # Combine all enriched songs
            all_enriched_songs = already_processed_enriched_songs + enriched_songs
            
            yield f"data: {json.dumps({'type': 'status', 'message': 'Cannoli is searching through your music...'})}\n\n"
            await asyncio.sleep(0.1)
            
            # Update progress for LLM search step
            llm_search_progress = len(unprocessed_raw_songs) + 1
            yield f"data: {json.dumps({'type': 'progress', 'processed': llm_search_progress, 'total': total_progress_steps, 'message': f'Cannoli is analyzing your music...'})}\n\n"
            await asyncio.sleep(0.1)
            
            # Search through the enriched songs using LLM
            llm_client = get_client("openai-direct", model_name="gpt-4o-mini")
            relevant_songs, token_usage = search_library(llm_client, all_enriched_songs, query, n=3, chunk_size=250, verbose=True)
            
            print(f"[spotify_search] Done searching")
            
            yield f"data: {json.dumps({'type': 'status', 'message': 'Processing results...'})}\n\n"
            await asyncio.sleep(0.1)
            
            # Update progress for result processing step
            #final_progress = len(unprocessed_raw_songs) + 2
            #yield f"data: {json.dumps({'type': 'progress', 'processed': final_progress, 'total': total_progress_steps, 'message': f'Done!'})}\n\n"
            #await asyncio.sleep(0.1)
            
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
                'token_usage': token_usage
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
