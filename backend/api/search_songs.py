import os
import sys
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv
from dataclasses import asdict

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

# Add the search_library directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
search_lib_dir = os.path.join(backend_dir, 'search_library')
sys.path.insert(0, backend_dir)

from search_library.search import search_library
from search_library.types import Song as SearchSong
from search_library.clients import get_client

# Define Pydantic models for request body validation
class SongModel(BaseModel):
    id: str
    name: str
    artist: str
    song_link: str
    song_metadata: str
    lyrics: str

class SearchRequest(BaseModel):
    query: str
    songs: List[SongModel]

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.post("/api/search_songs")
async def search_songs_endpoint(search_request: SearchRequest):
    try:
        # Check for LLM API key
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        openai_key = os.getenv('OPENAI_API_KEY')

        if not anthropic_key and not openai_key:
            raise HTTPException(
                status_code=500,
                detail="Missing LLM API configuration. Please set ANTHROPIC_API_KEY or OPENAI_API_KEY."
            )

        # Convert Pydantic models to the search_library's Song objects
        songs_to_search = [SearchSong(**s.dict()) for s in search_request.songs]

        # Initialize LLM client
        llm_client = get_client("anthropic-direct") if anthropic_key else get_client("openai-direct")
        
        # Perform search
        search_results = search_library(llm_client, songs_to_search, search_request.query)
        
        # Convert results back to dicts for the JSON response
        results_data = [asdict(song) for song in search_results]

        return {
            'success': True,
            'results': results_data,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")

# This app object is the ASGI application that Vercel will run.
# To test locally, run: uvicorn backend.api.search_songs:app --reload 