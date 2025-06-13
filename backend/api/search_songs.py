import os
import json
import sys
from datetime import datetime
from vercel_helpers.request import VercelRequest
from vercel_helpers.response import VercelResponse

# Add the search_library directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
search_lib_dir = os.path.join(backend_dir, 'search_library')
sys.path.insert(0, backend_dir)

from search_library.search import search_library
from search_library.types import Song
from search_library.clients import get_client, TextPrompt

def handler(request: VercelRequest) -> VercelResponse:
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        }
        return VercelResponse(status_code=200, headers=headers)

    try:
        # Check for LLM API key
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        openai_key = os.getenv('OPENAI_API_KEY')

        if not anthropic_key and not openai_key:
            return VercelResponse(
                status_code=500,
                body={
                    'error': 'Missing LLM API configuration',
                    'details': 'Please set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable'
                }
            )

        # Parse request body
        try:
            body = request.json
        except json.JSONDecodeError as e:
            return VercelResponse(
                status_code=400,
                body={'error': 'Invalid JSON in request body', 'details': str(e)}
            )

        query = body.get('query')
        songs_data = body.get('songs', [])

        if not query or not isinstance(query, str):
            return VercelResponse(
                status_code=400,
                body={'error': 'Missing or invalid query', 'details': 'Please provide a query string'}
            )

        if not isinstance(songs_data, list) or not songs_data:
            return VercelResponse(
                status_code=400,
                body={'error': 'Invalid songs data', 'details': 'Please provide a non-empty array of songs'}
            )

        # Convert songs data to Song objects
        songs = [Song(**s) for s in songs_data]
        
        # Initialize LLM client
        llm_client = get_client("anthropic-direct") if anthropic_key else get_client("openai-direct")
        
        # Perform search
        search_results = search_library(llm_client, songs, query)
        
        # Convert results back to dicts
        results_data = [song.dict() for song in search_results]

        success_response = {
            'success': True,
            'message': f'Found {len(results_data)} matching songs',
            'query': query,
            'total_songs_searched': len(songs),
            'results': results_data,
            'timestamp': datetime.now().isoformat()
        }
        
        return VercelResponse(status_code=200, body=success_response)

    except Exception as e:
        return VercelResponse(
            status_code=500,
            body={'error': 'Internal server error', 'details': str(e)}
        ) 