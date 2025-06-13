import os
import sys
from http.server import HTTPServer
from dotenv import load_dotenv
from api.search_songs import handler

# Load environment variables from .env file
load_dotenv()

def run(server_class=HTTPServer, handler_class=handler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting server on port {port}...")
    httpd.serve_forever()

if __name__ == '__main__':
    run() 