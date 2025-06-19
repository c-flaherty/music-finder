import os
import sys
import requests
import subprocess
import json
from typing import Dict, List, Optional
import base64
from http.server import BaseHTTPRequestHandler
from dataclasses import asdict

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

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

from supabase import create_client, Client

anthropic_key = os.getenv('ANTHROPIC_API_KEY')
openai_key = os.getenv('OPENAI_API_KEY')
supabase_url = os.getenv('SUPABASE_URL')
supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

SET_MAX_SONGS_FORR_DEBUG: int | None = 5

# --------------------------- Lyrics helper ---------------------------
def get_lyrics(song_name: str, artist_names: list[str]) -> str:
    """Fetch plain-text lyrics from Genius for the given song/artist.

    This function used to be declared as *async* but was always invoked
    synchronously, leading to an un-awaited coroutine and a 500 error.
    It is now fully synchronous.
    """
    search_query = f"{song_name} {', '.join(artist_names)}"
    print(f"[spotify_search] Searching for lyrics for {search_query}")
    
    headers = {
        'accept': '*/*',
        'content-type': 'application/json',
        'x-genius-ios-version': '7.7.0',
        'x-genius-logged-out': 'true',
        'accept-language': 'en-US,en;q=0.9',
        'user-agent': 'Genius/1267 CFNetwork/3826.500.131 Darwin/24.5.0'
    }
    
    if os.getenv('GENIUS_ACCESS_TOKEN'):
        headers['Authorization'] = f"Bearer {os.getenv('GENIUS_ACCESS_TOKEN')}"

    # Search for the song
    search_url = f"https://api.genius.com/search?q={search_query}"
    search_response = requests.get(search_url, headers=headers)
    search_data = search_response.json()
    
    song_id = search_data.get('response', {}).get('hits', [{}])[0].get('result', {}).get('id')
    if not song_id:
        return ""

    # Get song details
    song_url = f"https://api.genius.com/songs/{song_id}?text_format=plain"
    song_response = requests.get(song_url, headers=headers)
    song_data = song_response.json()
    print(song_data)
    
    return song_data.get('response', {}).get('song', {}).get('lyrics', {}).get('plain', "")

def get_song_metadata(song_name: str, artist_names: list[str]) -> str:
    """Ask LLM with search tool to research the song."""
    llm_client = get_client("openai-direct", model_name="gpt-4o-mini-search-preview", enable_web_search=True) # use openai for now because it has built-in web search tool
    prompt = get_song_metadata_query(song_name, artist_names)
    response_tuple = llm_client.generate(
        [[TextPrompt(text=prompt)]],  # Note the double brackets
        max_tokens=1000
    )
    response_blocks = response_tuple[0]  # This is list[AssistantContentBlock]
    first_block = response_blocks[0]     # This is the first AssistantContentBlock
    response_text = first_block.text     # This is the text content
    return response_text

def refresh_access_token(refresh_token: str) -> str:
    response = requests.post(
        'https://accounts.spotify.com/api/token',
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f"Basic {base64.b64encode(f'{os.getenv('SPOTIFY_CLIENT_ID')}:{os.getenv('SPOTIFY_CLIENT_SECRET')}'.encode()).decode()}"
        },
        data={
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
    )
    
    if not response.ok:
        raise Exception('Failed to refresh access token')
    
    return response.json()['access_token']

def get_songs_from_playlists(playlists_data: Dict, access_token: str, query: str) -> list[RawSong]:
    all_songs = []

    for playlist in playlists_data['items'][:5]:
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
        
        for item in tracks_data['items'][:100]:  # safety cap
            track_data = item.get('track')
            if not track_data or not track_data.get('id'):
                continue

            """
            Track data dict keys:
                - id: Spotify track ID
                - name: Track name
                - artists: List of artist objects, each containing 'name'
                - external_urls: Dict of external URLs
                - album: Album object
                - duration_ms: Track duration in milliseconds
                - popularity: Track popularity score
                - preview_url: URL for 30 second preview
            """

            track = RawSong(
                id=track_data['id'],
                song_link=track_data['external_urls']['spotify'],
                name=track_data['name'],
                artists=[artist['name'] for artist in track_data['artists']],
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

def enrich_songs(songs: list[RawSong]) -> list[SearchSong]:
    """Enrich raw songs with lyrics and metadata."""
    enriched = []
    for song in songs:
        lyrics = get_lyrics(song.name, song.artists)
        song_metadata = get_song_metadata(song.name, song.artists)
        enriched_song = SearchSong(
            **song.__dict__,
            lyrics=lyrics,
            song_metadata=song_metadata
        )
        enriched.append(enriched_song)
    return enriched

def get_playlist_names(access_token: str, refresh_token: Optional[str] = None) -> tuple[Dict, str]:
    """
    Fetch user's playlists from Spotify API with automatic token refresh if needed.
    
    Args:
        access_token: The current Spotify access token
        refresh_token: Optional refresh token for automatic token renewal
        
    Returns:
        Tuple of (playlists_data, access_token) where access_token may be refreshed
        
    Raises:
        Exception: If unable to fetch playlists or refresh token
    """
    playlists_response = requests.get(
        'https://api.spotify.com/v1/me/playlists?limit=10',
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    )

    if playlists_response.status_code == 401 and refresh_token:
        # Token expired, try to refresh
        new_token = refresh_access_token(refresh_token)
        playlists_response = requests.get(
            'https://api.spotify.com/v1/me/playlists?limit=10',
            headers={
                'Authorization': f'Bearer {new_token}',
                'Content-Type': 'application/json'
            }
        )
        access_token = new_token

    if not playlists_response.ok:
        raise Exception(f'Failed to fetch playlists: {playlists_response.status_code}')

    return playlists_response.json(), access_token

def fetch_already_processed_enriched_songs(raw_songs: list[RawSong]) -> tuple[list[SearchSong], list[RawSong]]:
    """Fetch already processed enriched songs from the database.
    
    Args:
        raw_songs: The raw songs to fetch already processed enriched songs for

    Returns:
        A tuple of (already_processed_enriched_songs, unprocessed_enriched_songs)
    """
    

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
        
        # Create a dictionary of processed songs by ID for quick lookup
        processed_songs_dict = {song['id']: song for song in response.data}
        
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
                    song_metadata=db_song.get('song_metadata', '')
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
                'song_metadata': song.song_metadata
            }
            songs_data.append(song_data)
        
        # Insert songs into database (upsert to handle potential duplicates)
        response = supabase.table('songs').upsert(songs_data).execute()
        print(f"[spotify_search] Successfully saved {len(songs_data)} songs to database")
        
    except Exception as e:
        print(f"[spotify_search] Error saving songs to database: {str(e)}")

class handler(BaseHTTPRequestHandler):
    # ------------------------------------------------------------------
    def _cors(self):
        """Attach CORS headers allowing browser access from any origin."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        # Allow custom header used for refresh token in addition to standard ones
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, refresh-token")

    # ------------------------------- Pre-flight -------------------------------
    def do_OPTIONS(self):  # noqa: N802
        """Handle CORS pre-flight requests from the browser."""
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        try:
            auth_header = self.headers.get('Authorization')
            refresh_token = self.headers.get('refresh-token')
            
            if not auth_header or not auth_header.startswith('Bearer '):
                self.send_response(401)
                self._cors()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Unauthorized'}).encode())
                return

            access_token = auth_header.split(' ')[1]
            
            # Gracefully handle missing header to avoid KeyError
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            query = data.get('query')
            
            if not query:
                self.send_response(400)
                self._cors()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Missing query parameter'}).encode())
                return

            playlists_data, access_token = get_playlist_names(access_token, refresh_token)
            print(f"[spotify_search] Found {len(playlists_data['items'])} playlists")
            raw_songs = get_songs_from_playlists(playlists_data, access_token, query)
            
            already_processed_enriched_songs, unprocessed_raw_songs = fetch_already_processed_enriched_songs(raw_songs)
            
            print(f"[spotify_search] Found {len(raw_songs)} total songs")
            
            # Only enrich unprocessed songs
            newly_enriched_songs = enrich_songs(unprocessed_raw_songs)
            
            # Save newly enriched songs to database
            save_enriched_songs_to_db(newly_enriched_songs)
            
            # Combine already processed and newly enriched songs
            all_enriched_songs = already_processed_enriched_songs + newly_enriched_songs
            
            llm_client = get_client("openai-direct", model_name="gpt-4o-mini")
            result = search_library(llm_client, all_enriched_songs, query, n=3, chunk_size=1000)
            
            # Convert Song objects to dictionaries for JSON serialization
            result_dicts = []
            for song in result:
                song_dict = asdict(song)
                # Convert artists list to single artist string for frontend compatibility
                song_dict['artist'] = ', '.join(song.artists) if song.artists else ''
                # Ensure reasoning field is present
                song_dict['reasoning'] = getattr(song, 'reasoning', '')
                result_dicts.append(song_dict)

            self.send_response(200)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'results': result_dicts}).encode())

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.send_response(500)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode()) 