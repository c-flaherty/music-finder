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
from search_library.types import Song as SearchSong
from search_library.clients import get_client

class SpotifyArtist:
    def __init__(self, name: str):
        self.name = name

class SpotifyTrack:
    def __init__(self, data: Dict):
        self.id = data['id']
        self.name = data['name']
        self.artists = [SpotifyArtist(artist['name']) for artist in data['artists']]
        self.external_urls = data['external_urls']
        self.album = data['album']
        self.duration_ms = data['duration_ms']
        self.popularity = data['popularity']
        self.preview_url = data['preview_url']

# --------------------------- Lyrics helper ---------------------------
def get_lyrics(song_name: str, artist_name: str) -> str:
    """Fetch plain-text lyrics from Genius for the given song/artist.

    This function used to be declared as *async* but was always invoked
    synchronously, leading to an un-awaited coroutine and a 500 error.
    It is now fully synchronous.
    """
    search_query = f"{song_name} {artist_name}"
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

def process_playlists(playlists_data: Dict, access_token: str, query: str):
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
            track = SpotifyTrack(track_data)
            # Lyrics look-ups are slow; skip by default to prevent timeouts.
            lyrics = get_lyrics(track.name, ', '.join(artist.name for artist in track.artists))
            
            song = SearchSong(
                id=track.id,
                name=track.name,
                artist=', '.join(artist.name for artist in track.artists),
                song_link=track.external_urls['spotify'],
                song_metadata=json.dumps({
                    'album': track.album['name'],
                    'duration_ms': track.duration_ms,
                    'popularity': track.popularity,
                    'preview_url': track.preview_url
                }),
                lyrics=lyrics
            )
            all_songs.append(song)

    # Remove duplicates
    unique_songs = list({song.id: song for song in all_songs}.values())

    # Debug: how many unique songs were collected
    print(f"[spotify_search] Collected {len(unique_songs)} unique tracks from playlists")

    # Check for LLM API key
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')

    if not anthropic_key and not openai_key:
        raise Exception('Missing LLM API configuration.')

    llm_client = get_client("anthropic-direct") if anthropic_key else get_client("openai-direct")
    
    print(f"[spotify_search] Searching with {llm_client.__class__.__name__} for query: '{query}'")
    search_results = search_library(llm_client, unique_songs, query)
    
    results_data = [asdict(song) for song in search_results]

    result_dict = {
        'results': results_data
    }

    # Debug: print top few result names to verify content
    if results_data:
        sample_names = [s['name'] for s in results_data[:5]]
        print(f"[spotify_search] Returning {len(results_data)} results. Sample: {sample_names}")

    return result_dict

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

            playlists_response = requests.get(
                'https://api.spotify.com/v1/me/playlists?limit=10',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                }
            )

            if playlists_response.status_code == 401 and refresh_token:
                try:
                    new_token = refresh_access_token(refresh_token)
                    playlists_response = requests.get(
                        'https://api.spotify.com/v1/me/playlists?limit=10',
                        headers={
                            'Authorization': f'Bearer {new_token}',
                            'Content-Type': 'application/json'
                        }
                    )
                    access_token = new_token
                except Exception as e:
                    self.send_response(401)
                    self._cors()
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'Failed to refresh access token'}).encode())
                    return

            if not playlists_response.ok:
                self.send_response(playlists_response.status_code)
                self._cors()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Failed to fetch playlists'}).encode())
                return

            playlists_data = playlists_response.json()
            result = process_playlists(playlists_data, access_token, query)
            
            self.send_response(200)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())

        except Exception as e:
            self.send_response(500)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode()) 