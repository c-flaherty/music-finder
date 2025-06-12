import os
import json
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from supabase import create_client, Client

# Add the search_library directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
search_lib_dir = os.path.join(backend_dir, 'search_library')
sys.path.insert(0, backend_dir)

from search_library.search import search_library
from search_library.types import Song
from search_library.clients import get_client, TextPrompt

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def do_POST(self):
        """
        Handle POST requests to search songs using LLM.
        Expected request body:
        {
            "query": "user search query",
            "songs": [
                {
                    "id": "song_id",
                    "name": "song_name",
                    "artist": "artist_name",
                    "song_link": "spotify_link",
                    "song_metadata": "metadata_json_string",
                    "lyrics": "song_lyrics"
                },
                ...
            ]
        }
        """
        
        try:
            # Check for LLM API key
            anthropic_key = os.getenv('ANTHROPIC_API_KEY')
            openai_key = os.getenv('OPENAI_API_KEY')
            
            if not anthropic_key and not openai_key:
                self.send_response(500)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                error_response = {
                    'error': 'Missing LLM API configuration',
                    'details': 'Please set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable'
                }
                self.wfile.write(json.dumps(error_response).encode())
                return
            
            # Parse request body
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                body = json.loads(post_data.decode('utf-8')) if post_data else {}
            except json.JSONDecodeError as e:
                self.send_response(400)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                error_response = {
                    'error': 'Invalid JSON in request body',
                    'details': str(e)
                }
                self.wfile.write(json.dumps(error_response).encode())
                return
            
            query = body.get('query')
            songs_data = body.get('songs', [])
            
            # Validate request body
            if not query or not isinstance(query, str):
                self.send_response(400)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                error_response = {
                    'error': 'Missing or invalid query',
                    'details': 'Please provide a query string in the request body'
                }
                self.wfile.write(json.dumps(error_response).encode())
                return
            
            if not isinstance(songs_data, list) or not songs_data:
                self.send_response(400)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                error_response = {
                    'error': 'Invalid songs data',
                    'details': 'Please provide a non-empty array of songs'
                }
                self.wfile.write(json.dumps(error_response).encode())
                return
            
            # Convert songs data to Song objects
            songs = []
            for song_data in songs_data:
                try:
                    song = Song(
                        id=str(song_data['id']),
                        song_link=song_data['song_link'],
                        song_metadata=song_data['song_metadata'],
                        lyrics=song_data.get('lyrics', ''),
                        name=song_data['name'],
                        artist=song_data['artist']
                    )
                    songs.append(song)
                except Exception as e:
                    # Skip invalid song records
                    print(f"Skipping invalid song record: {song_data}, error: {e}")
                    continue
            
            if not songs:
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                empty_response = {
                    'success': True,
                    'message': 'No valid songs found in request',
                    'query': query,
                    'results': [],
                    'timestamp': datetime.now().isoformat()
                }
                self.wfile.write(json.dumps(empty_response).encode())
                return
            
            # Initialize LLM client
            try:
                if anthropic_key:
                    llm_client = get_client("anthropic-direct")
                else:
                    llm_client = get_client("openai-direct")
            except Exception as e:
                self.send_response(500)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                error_response = {
                    'error': 'Failed to initialize LLM client',
                    'details': str(e)
                }
                self.wfile.write(json.dumps(error_response).encode())
                return
            
            # Perform search using LLM
            try:
                search_results = search_library(llm_client, songs, query)
                
                # Convert Song objects to dictionaries for JSON response
                results_data = []
                for song in search_results:
                    results_data.append({
                        'id': song.id,
                        'name': song.name,
                        'artist': song.artist,
                        'song_link': song.song_link,
                        'song_metadata': song.song_metadata,
                        'lyrics': song.lyrics
                    })
                
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                success_response = {
                    'success': True,
                    'message': f'Found {len(results_data)} matching songs',
                    'query': query,
                    'total_songs_searched': len(songs),
                    'results': results_data,
                    'timestamp': datetime.now().isoformat()
                }
                self.wfile.write(json.dumps(success_response).encode())
                
            except Exception as search_error:
                self.send_response(500)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                error_response = {
                    'error': 'Search failed',
                    'details': str(search_error)
                }
                self.wfile.write(json.dumps(error_response).encode())
                
        except Exception as error:
            self.send_response(500)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = {
                'error': 'Internal server error',
                'details': str(error)
            }
            self.wfile.write(json.dumps(error_response).encode()) 