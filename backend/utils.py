import json, asyncio, os, requests, base64, urllib.request, urllib.parse
import random
from datetime import datetime
from typing import Union, List, Dict, Any, Optional, Tuple
from supabase import create_client, Client
import sys
import time
from dataclasses import asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add the search_library directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
search_lib_dir = os.path.join(backend_dir, 'search_library')
sys.path.insert(0, backend_dir)

from search_library.search import search_library, create_song_embedding, vector_search_library
from search_library.types import Song as SearchSong, RawSong
from search_library.clients import get_client
from search_library.prompts import get_song_metadata_query
from search_library.clients import TextPrompt
from search_library.web_search import search_internet

# Environment variables
supabase_url = os.getenv('SUPABASE_URL')
supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

SKIP_EXPENSIVE_STEPS: bool = False
SKIP_SUPABASE_CACHE: bool = False
SKIP_WEB_SEARCH_ENRICHMENT: bool = False
HARDCODE_SONG_COUNT: int | None = 100
ADD_RERANKER_TO_VECTOR_SEARCH: bool = True

# --------------------------- Lyrics helper ---------------------------
def get_lyrics(song_name: str, artist_names: list[str]) -> str:
    """Fetch plain-text lyrics from Genius for the given song/artist."""

    if SKIP_EXPENSIVE_STEPS:
        time.sleep(0.2)
        return f"these are lyrics for {song_name} by {', '.join(artist_names)}"
    
    search_query = f"{song_name} {artist_names[0]}"
    print(f"[DEBUG] Searching for lyrics for: {search_query}")
    
    headers = {
        'accept': '*/*',
        'content-type': 'application/json',
        'x-genius-ios-version': '7.7.0',
        'x-genius-logged-out': 'true',
        'accept-language': 'en-US,en;q=0.9',
        'user-agent': 'Genius/1267 CFNetwork/3826.500.131 Darwin/24.5.0'
    }
    
    genius_token = os.getenv('GENIUS_ACCESS_TOKEN')
    if genius_token:
        headers['Authorization'] = f"Bearer {genius_token}"

    proxies = None
    verify_ssl = True
    use_proxy = False
    isp_username = os.getenv('BD_ISP_USERNAME')
    isp_password = os.getenv('BD_ISP_PASSWORD')
    print(f"[DEBUG] ISP USER: {isp_username}, ISP PASS: {'set' if isp_password else 'not set'}")
    if isp_username and isp_password:
        proxy_url = f'http://{isp_username}:{isp_password}@brd.superproxy.io:33335'
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

    # Headers for the song details request (no Authorization for this request)
    song_headers = {
        'accept': '*/*',
        'content-type': 'application/json',
        'x-genius-ios-version': '7.7.0',
        'x-genius-logged-out': 'true',
        'accept-language': 'en-US,en;q=0.9',
        'user-agent': 'Genius/1267 CFNetwork/3826.500.131 Darwin/24.5.0'
    }

    song_url = f"https://api.genius.com/songs/{song_id}?text_format=plain"
    print(f"[DEBUG] Song URL: {song_url}")
    try:
        song_response = requests.get(song_url, headers=song_headers, proxies=proxies, verify=verify_ssl, timeout=10)
        print(f"[DEBUG] Song response status: {song_response.status_code}")
    except Exception as proxy_error:
        print(f"[DEBUG] Proxy request for song details failed: {proxy_error}")
        if use_proxy:
            song_response = requests.get(song_url, headers=song_headers, timeout=10)
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
    # if len(lyrics) > 1600:
    #     lyrics = lyrics[:1600]
    return lyrics

def get_song_metadata(
    song_name: str,
    artist_names: list[str],
    album: str = "",
    max_retries: int = 2
) -> tuple[str, dict]:
    """
    Return an LLM-generated summary of a song, using web evidence when available.

    Fallback order:
      1. `"song_name" by artist background`
      2. `"album" by first_artist album background`
      3. `first_artist background music`
      4. Ask the model to answer from prior knowledge even without evidence.
    """
    print(f"[DEBUG] Getting song metadata for: {song_name} by {', '.join(artist_names)}")
    if SKIP_EXPENSIVE_STEPS or SKIP_WEB_SEARCH_ENRICHMENT:
        time.sleep(0.2)
        return "", {}

    first_artist = artist_names[0] if artist_names else ""
    query_chain = [
        f'"{song_name}" by {", ".join(artist_names)} background',
        f'"{album}" by {first_artist} album background' if album else None,
        f'{first_artist} background music'
    ]
    # Remove any Nones that slipped in (e.g. no album supplied)
    query_chain = [q for q in query_chain if q]

    combined_search_text = ""
    for q_idx, query in enumerate(query_chain):
        try:
            start = time.time()
            search_results = search_internet(query, top_n=3)
            print(f"[DEBUG] Query [{q_idx+1}/{len(query_chain)}] \"{query}\" "
                  f"-> {len(search_results)} docs in {time.time()-start:.2f}s")
            if search_results:
                combined_search_text = "\n\n---\n\n".join(search_results)
                break
        except Exception as e:
            print(f"[WARN] Web search failed for '{query}': {e}")

    # ---------------- LLM call ----------------
    llm_client = get_client("openai-direct", model_name="gpt-4o-mini")
    if combined_search_text:
        summarization_prompt = f"""
Based on the following web search results about the song "{song_name}" by {', '.join(artist_names)}, answer *concisely*:

1. Genre
2. Time period written
3. Musical movement
4. References (lyrical / musical / cultural)
5. Cultural significance

Web search results:
{combined_search_text[:6000]}
"""
    else:
        summarization_prompt = f"""
No relevant web pages were found, but please use your own knowledge to
answer *concisely* the same five questions about:

  • Song: "{song_name}"
  • Artist(s): {', '.join(artist_names)}
  • Album: "{album}"

If any point is genuinely unknown, reply “Unknown” for that bullet.
"""

    start = time.time()
    response_tuple = llm_client.generate(
        [[TextPrompt(text=summarization_prompt)]],
        max_tokens=700
    )
    print(f"[DEBUG] LLM call took {time.time()-start:.2f}s")
    response_text = response_tuple[0][0].text
    token_usage = response_tuple[1] if len(response_tuple) > 1 else {}

    return response_text, token_usage

def get_songs_from_playlists(playlists_data: Dict, access_token: str, query: str) -> list[RawSong]:
    all_songs = []

    for playlist in playlists_data['items'][:100]:  # Limit to first 100 playlists
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
        
        for item in tracks_data['items'][:2000]:  # Safety cap per playlist
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

            if HARDCODE_SONG_COUNT and len(all_songs) >= HARDCODE_SONG_COUNT:
                break
        
        if HARDCODE_SONG_COUNT and len(all_songs) >= HARDCODE_SONG_COUNT:
            break

    # Remove duplicates
    unique_songs = list({song.id: song for song in all_songs}.values())

    if HARDCODE_SONG_COUNT and len(unique_songs) < HARDCODE_SONG_COUNT:
        def create_random_songs(count: int) -> list[RawSong]:
            return [RawSong(
                id=f"random-{i}",
                name=f"Random Song {i}",
                artists=[f"Artist {i}"],
                album=f"Album {i}",
                song_link=f"https://google.com"
            ) for i in range(count)]

        random_songs = create_random_songs(HARDCODE_SONG_COUNT - len(unique_songs))
        unique_songs.extend(random_songs)

    # Debug: how many unique songs were collected
    print(f"[spotify_search] Collected {len(unique_songs)} unique tracks from playlists")

    return unique_songs

def fetch_already_processed_enriched_songs(raw_songs: list[RawSong]) -> tuple[list[SearchSong], list[RawSong]]:
    """Fetch already processed enriched songs from the database.
    
    Args:
        raw_songs: The raw songs to fetch already processed enriched songs for

    Returns:
        A tuple of (already_processed_enriched_songs, unprocessed_enriched_songs)
    """
    print(f"[spotify_search check] Supabase URL: {supabase_url}")
    print(f"[spotify_search check] Supabase service key: {supabase_service_key}")
    if not supabase_url or not supabase_service_key:
        print("[spotify_search] Database credentials not available, treating all songs as unprocessed")
        return ([], raw_songs)
    
    print(f"[spotify_search] Fetching already processed enriched songs from database")

    supabase: Client = create_client(supabase_url, supabase_service_key)

    already_processed_enriched_songs = []
    unprocessed_enriched_songs = []
    
    # Get all song IDs from raw_songs
    song_ids = [song.id for song in raw_songs]
    
    if not song_ids:
        return ([], [])
    
    try:
        # Query the database for all songs with matching IDs
        response = supabase.table('songs').select('*').in_('id', song_ids).execute()
        #print(f"[spotify_search] Response: {response}")
        
        # Create a dictionary of processed songs by ID for quick lookup
        processed_songs_dict = {song['id']: song for song in response.data}
        #print(f"[spotify_search] Processed songs dict: {processed_songs_dict}")
        
        # Iterate through raw songs and categorize them
        for raw_song in raw_songs:
            if raw_song.id in processed_songs_dict:
                # Song is already processed, convert database record to SearchSong
                db_song = processed_songs_dict[raw_song.id]
                
                # Convert comma-delimited artists string back to list
                artists_list = [artist.strip() for artist in db_song['artists'].split(',')]
                
                enriched_song = SearchSong(
                    id=db_song['id'],
                    name=db_song['name'],
                    artists=artists_list,
                    album=db_song['album'],
                    song_link=db_song['song_link'],
                    lyrics=db_song.get('lyrics', ''),
                    song_metadata=db_song.get('song_metadata', ''),
                    embedding=db_song.get('embedding', [])
                )
                already_processed_enriched_songs.append(enriched_song)
            else:
                # Song is not processed yet
                unprocessed_enriched_songs.append(raw_song)
        
        print(f"[spotify_search] Found {len(already_processed_enriched_songs)} already processed songs in database")
        print(f"[spotify_search] Found {len(unprocessed_enriched_songs)} unprocessed songs")
        
    except Exception as e:
        print(f"[spotify_search] Error fetching from database: {str(e)}")
        # If there's an error, treat all songs as unprocessed
        return ([], raw_songs)
    
    return (already_processed_enriched_songs, unprocessed_enriched_songs)

def save_enriched_songs_to_db(enriched_songs: list[SearchSong]) -> None:
    """Save enriched songs to the database.
    
    Args:
        enriched_songs: List of enriched songs to save
    """
    if not enriched_songs:
        return
    
    if not supabase_url or not supabase_service_key:
        print("[spotify_search] Database credentials not available, skipping save")
        return
    
    supabase: Client = create_client(supabase_url, supabase_service_key)
    
    try:
        # Prepare data for batch insert
        songs_data = []
        for song in enriched_songs:
            # Convert artists list to comma-delimited string
            artists_str = ', '.join(song.artists)
            
            song_data = {
                'id': song.id,
                'name': song.name,
                'artists': artists_str,
                'album': song.album,
                'song_link': song.song_link,
                'lyrics': song.lyrics,
                'song_metadata': song.song_metadata,
                'embedding': song.embedding
            }
            songs_data.append(song_data)
        
        # Insert songs into database (upsert to handle potential duplicates)
        response = supabase.table('songs').upsert(songs_data).execute()
        print(f"[spotify_search] Successfully saved {len(songs_data)} songs to database")
        
    except Exception as e:
        print(f"[spotify_search] Error saving songs to database: {str(e)}")

def enrich_songs(songs: list[RawSong]):
    """Enrich raw songs with lyrics and metadata in parallel, yielding results as they complete.
    Now saves each song to database immediately after enrichment."""
    processed_count = 0
    total_count = len(songs)
    lyrics_success_count = 0
    db_save_success_count = 0
    total_enrichment_tokens = {
        'total_input_tokens': 0,
        'total_output_tokens': 0,
        'total_requests': 0
    }
    
    def enrich_single_song(song: RawSong) -> tuple[SearchSong, dict]:
        """Enrich a single song with lyrics and metadata."""
        print(f"[spotify_search] Enriching song: {song.name} - {', '.join(song.artists)}")
        lyrics = ""  # Initialize lyrics variable
        song_metadata = ""
        token_usage = {}
        embedding = []
        try:
            ## Commented out for now to test frontend quickly
            lyrics = get_lyrics(song.name, song.artists)
            song_metadata, token_usage = get_song_metadata(song.name, song.artists, song.album)
            embedding = create_song_embedding(song)
            # if lyrics:
            #     print(f"[LYRICS SUCCESS] {song.name} - {', '.join(song.artists)}")
            # else:
            #     print(f"[LYRICS FAIL] {song.name} - {', '.join(song.artists)}")
            print(f"[LYRICS SUCCESS] {song.name} - {', '.join(song.artists)} {len(embedding)}")
            return SearchSong(
                **song.__dict__,
                lyrics=lyrics,
                song_metadata=song_metadata,
                embedding=embedding
            ), token_usage
        except Exception as e:
            print(f"[LYRICS FAIL] {song.name} - {', '.join(song.artists)} (error: {e})")
            return SearchSong(
                **song.__dict__,
                lyrics=lyrics,  # Now lyrics is always defined
                song_metadata=song_metadata,
                embedding=embedding
            ), {}
    
    if not songs:
        return

    # Reduce concurrency to prevent memory corruption issues
    max_workers = min(5, len(songs))  # Much lower concurrency for safety
    last_emit_time = time.time()
    print(f"[spotify_search] Enriching {len(songs)} songs with {max_workers} workers (reduced for safety)")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all enrichment tasks
        future_to_song = {executor.submit(enrich_single_song, song): song for song in songs}
        
        # Collect results as they complete and yield them
        for future in as_completed(future_to_song):
            try:
                enriched_song, token_usage = future.result()
                if enriched_song.lyrics:
                    lyrics_success_count += 1
                
                # Aggregate token usage
                total_enrichment_tokens['total_input_tokens'] += token_usage.get('input_tokens', 0)
                total_enrichment_tokens['total_output_tokens'] += token_usage.get('output_tokens', 0)
                total_enrichment_tokens['total_requests'] += 1 if not SKIP_EXPENSIVE_STEPS else 0
                
                # Save to database immediately after enrichment
                if not SKIP_SUPABASE_CACHE:
                    try:
                        save_enriched_songs_to_db([enriched_song])  # Save single song
                        db_save_success_count += 1
                        print(f"[DB SUCCESS] Saved {enriched_song.name} to database")
                    except Exception as db_error:
                        print(f"[DB ERROR] Failed to save {enriched_song.name} to database: {db_error}")
                        # Continue processing even if database save fails
                
                yield enriched_song, total_enrichment_tokens
            except Exception as e:
                song = future_to_song[future]
                print(f"[LYRICS FAIL] {song.name} - {', '.join(song.artists)} (error: {e})")
                # Still try to save the empty song to database to avoid reprocessing
                empty_song = SearchSong(
                    **song.__dict__,
                    lyrics="",
                    song_metadata=""
                )
                
                if not SKIP_SUPABASE_CACHE:
                    try:
                        save_enriched_songs_to_db([empty_song])
                        print(f"[DB SUCCESS] Saved empty {song.name} to database (to avoid reprocessing)")
                    except Exception as db_error:
                        print(f"[DB ERROR] Failed to save empty {song.name} to database: {db_error}")
                
                yield empty_song, total_enrichment_tokens
            
            processed_count += 1
    
    print(f"[ENRICHMENT SUMMARY] Processed {total_count} songs:")
    print(f"  - Got lyrics for {lyrics_success_count} songs")
    print(f"  - Successfully saved {db_save_success_count} songs to database")
    print(f"  - Failed to save {total_count - db_save_success_count} songs to database")

def get_playlist_names(access_token: str, refresh_token: Optional[str] = None) -> tuple[Dict, str]:
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