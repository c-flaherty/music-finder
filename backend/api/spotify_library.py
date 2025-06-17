import os
import requests
import base64
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

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

class handler(BaseHTTPRequestHandler):
    def _cors(self):
        """Attach CORS headers so the browser can call this endpoint from any origin."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        # Accept the custom refresh-token header in addition to standard ones
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Refresh-Token, refresh-token")

    def do_OPTIONS(self):  # noqa: N802
        """Handle CORS pre-flight requests from the browser."""
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        try:
            auth_header = self.headers.get('Authorization')
            refresh_token = self.headers.get('refresh-token')
            
            if not auth_header or not auth_header.startswith('Bearer '):
                self.send_response(401)
                self._cors()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Unauthorized'}).encode())
                return

            access_token = auth_header.split(' ')[1]

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
                        self.send_response(401)
                        self._cors()
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'error': 'Failed to refresh access token'}).encode())
                        return

                if not response.ok:
                    self.send_response(response.status_code)
                    self._cors()
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'Failed to fetch library'}).encode())
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
        except Exception as e:
            self.send_response(500)
            self._cors()
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode()) 