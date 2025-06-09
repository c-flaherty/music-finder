import os
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from supabase import create_client, Client

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
        Handle POST requests to insert music data into Supabase tables.
        Expected table fields:
        - song_link (text)
        - song_metadata (text)
        - lyrics (text)
        - name (text)
        - artist (text)
        """
        
        try:
            # Initialize Supabase client
            supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
            supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            
            # Validate environment variables
            if not supabase_url or not supabase_service_key:
                self.send_response(500)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                error_response = {
                    'error': 'Missing Supabase configuration',
                    'details': 'Please set NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables'
                }
                self.wfile.write(json.dumps(error_response).encode())
                return
            
            supabase: Client = create_client(supabase_url, supabase_service_key)
            
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
            
            # Validate request body
            if not table_name or data is None:
                self.send_response(400)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                error_response = {
                    'error': 'Missing required fields',
                    'details': 'Please provide tableName and data in the request body'
                }
                self.wfile.write(json.dumps(error_response).encode())
                return
            
            # Validate data is an array or single object
            data_array = data if isinstance(data, list) else [data]
            
            if len(data_array) == 0:
                self.send_response(400)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                error_response = {
                    'error': 'No data provided',
                    'details': 'Data array cannot be empty'
                }
                self.wfile.write(json.dumps(error_response).encode())
                return
            
            # Define expected fields for music table
            expected_fields = ['song_link', 'song_metadata', 'lyrics', 'name', 'artist']
            
            # Validate each record has the required structure
            validation_errors = []
            for i, record in enumerate(data_array):
                if not isinstance(record, dict):
                    validation_errors.append(f'Record {i}: must be an object')
                    continue
                
                # Check for required fields (at least name and artist should be present)
                if not record.get('name') or not record.get('artist'):
                    validation_errors.append(f'Record {i}: missing required fields "name" and "artist"')
                
                # Validate field types
                for field in record:
                    if field in expected_fields and record[field] is not None:
                        if not isinstance(record[field], str):
                            validation_errors.append(f'Record {i}: field "{field}" must be text/string')
                    elif field not in expected_fields:
                        validation_errors.append(f'Record {i}: unexpected field "{field}". Expected fields: {expected_fields}')
            
            if validation_errors:
                self.send_response(400)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                error_response = {
                    'error': 'Data validation failed',
                    'details': validation_errors
                }
                self.wfile.write(json.dumps(error_response).encode())
                return
            
            # Insert data into Supabase table
            try:
                response = supabase.table(table_name).insert(data_array).execute()
                inserted_data = response.data
                
                self.send_response(201)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                success_response = {
                    'success': True,
                    'message': f'Successfully inserted {len(inserted_data)} music record(s)',
                    'data': inserted_data,
                    'timestamp': datetime.now().isoformat(),
                    'validated_fields': expected_fields
                }
                self.wfile.write(json.dumps(success_response).encode())
                
            except Exception as supabase_error:
                self.send_response(400)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                error_response = {
                    'error': 'Database error',
                    'details': str(supabase_error)
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
