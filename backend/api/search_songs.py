import os
import sys
from datetime import datetime
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
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

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            search_request = json.loads(post_data)

            # Check for LLM API key
            anthropic_key = os.getenv('ANTHROPIC_API_KEY')
            openai_key = os.getenv('OPENAI_API_KEY')

            if not anthropic_key and not openai_key:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Missing LLM API configuration.'}).encode())
                return

            songs_to_search = [SearchSong(**s) for s in search_request['songs']]
            llm_client = get_client("anthropic-direct") if anthropic_key else get_client("openai-direct")
            
            search_results = search_library(llm_client, songs_to_search, search_request['query'])
            
            results_data = [asdict(song) for song in search_results]

            response_data = {
                'success': True,
                'results': results_data,
                'timestamp': datetime.now().isoformat()
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

# This app object is the ASGI application that Vercel will run.
# To test locally, run: uvicorn backend.api.search_songs:app --reload 