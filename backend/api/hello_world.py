import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Parse query parameters
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        name = query_params.get('name', ['World'])[0]
        
        # Set CORS headers
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        # Create response
        response_data = {
            'message': f'Hello, {name}!',
            'timestamp': datetime.now().isoformat(),
            'method': 'GET',
            'python_function': True
        }
        
        self.wfile.write(json.dumps(response_data).encode())
        
    def do_POST(self):
        # Get content length and read body
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode()) if post_data else {}
            name = data.get('name', 'World')
        except:
            name = 'World'
            data = {}
        
        # Set CORS headers
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        # Create response
        response_data = {
            'message': f'Hello, {name}!',
            'timestamp': datetime.now().isoformat(),
            'method': 'POST',
            'python_function': True,
            'received_data': data
        }
        
        self.wfile.write(json.dumps(response_data).encode())
        
    def do_OPTIONS(self):
        # Handle preflight requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers() 