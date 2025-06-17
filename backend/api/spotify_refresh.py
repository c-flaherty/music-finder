# Built-ins only: no external deps.
import os
import base64
import json
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    """Refresh a Spotify access token given a refresh token (POST)."""

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    # --------------------------------- Pre-flight ---------------------------------
    def do_OPTIONS(self):  # noqa: N802
        self.send_response(204)
        self._cors()
        self.end_headers()

    # ------------------------------------ POST ------------------------------------
    def do_POST(self):  # noqa: N802
        # Read and parse body ------------------------------------------------------
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length) if content_length else b"{}"
        try:
            body = json.loads(raw_body.decode() or "{}")
        except json.JSONDecodeError:
            body = {}

        refresh_token = body.get("refresh_token")

        if not refresh_token:
            self._json_response({"error": "Refresh token is required"}, 400)
            return

        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

        if not client_id or not client_secret:
            self._json_response({"error": "Server mis-configuration: missing Spotify credentials"}, 500)
            return

        # Spotify token request ----------------------------------------------------
        auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        response = urllib.request.Request(
            "https://accounts.spotify.com/api/token",
            urllib.parse.urlencode({
                "grant_type": "refresh_token",
                "refresh_token": refresh_token
            }).encode(),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {auth_header}",
            },
        )

        with urllib.request.urlopen(response) as response:
            if response.status != 200:
                self._json_response({"error": "Failed to refresh token"}, response.status)
                return

            data = json.loads(response.read().decode())
            self._json_response(data)

    # -----------------------------------------------------------------------------
    def _json_response(self, payload: dict, status: int = 200):
        """Helper to write JSON response with CORS headers."""
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode()) 