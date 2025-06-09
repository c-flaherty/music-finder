import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def do_POST(self):
        """Test POST handler without Supabase"""
        
        try:
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
            
            table_name = body.get('tableName')
            data = body.get('data')
            
            # Mock successful response
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            success_response = {
                'success': True,
                'message': 'Test function working!',
                'received_table': table_name,
                'received_data': data,
                'timestamp': datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(success_response).encode())
                
        except Exception as error:
            print(f'Unexpected error: {error}')
            self.send_response(500)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = {
                'error': 'Internal server error',
                'details': str(error)
            }
            self.wfile.write(json.dumps(error_response).encode())

    def do_GET(self):
        """Test GET handler"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        response = {
            'message': 'Simple test function is working!',
            'timestamp': datetime.now().isoformat()
        }
        self.wfile.write(json.dumps(response).encode()) 