import os
import requests
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

class handler(BaseHTTPRequestHandler):
    # ------------------------------------------------------------------
    def _cors(self):
        """Attach CORS headers for browser requests."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Refresh-Token, refresh-token")

    # ------------------------------- Pre-flight -------------------------------
    def do_OPTIONS(self):  # noqa: N802
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        try:
            parsed_path = urlparse(self.path)
            path_components = parsed_path.path.strip('/').split('/')
            
            # The playlist ID is the last component of the path
            playlist_id = None
            if path_components:
                last = path_components[-1]
                # Ignore the python filename itself (e.g., spotify_playlist.py)
                if not last.endswith('.py'):
                    playlist_id = last
            
            # Fallback: allow ?id=<playlist_id> in query string
            if not playlist_id:
                qs_id = parse_qs(parsed_path.query).get('id', [None])[0]
                playlist_id = qs_id

            if not playlist_id:
                self.send_response(400)
                self._cors()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Playlist ID is missing'}).encode())
                return
            
            auth_header = self.headers.get('Authorization')
            
            if not auth_header or not auth_header.startswith('Bearer '):
                self.send_response(401)
                self._cors()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Unauthorized'}).encode())
                return

            access_token = auth_header.split(' ')[1]

            response = requests.get(
                f'https://api.spotify.com/v1/playlists/{playlist_id}',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                }
            )

            if not response.ok:
                self.send_response(response.status_code)
                self._cors()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': f'Failed to fetch playlist: {response.status_code}'}).encode())
                return

            self.send_response(200)
            self._cors()
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response.json()).encode())
        except Exception as e:
            self.send_response(500)
            self._cors()
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode()) 