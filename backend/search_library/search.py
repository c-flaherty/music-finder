from .prompts import get_basic_query, decode_assistant_response
from .types import Song
from .clients import LLMClient, TextPrompt
import numpy as np
from openai import OpenAI
from supabase import create_client, Client
import os

def search_library(client: LLMClient, library: list[Song], user_query: str, n: int = 3, chunk_size: int = 1000, verbose: bool = False) -> tuple[list[Song], dict]:
    """
    Search the library for songs that match the user's query.

    Args:
        client: The LLM client to use for the search
        library: The library of songs to search through
        user_query: The query to search for
        n: The number of songs to return
        chunk_size: The number of songs to search through at once
        verbose: Whether to print verbose output

    Returns:
        A tuple of (songs that match the user's query, token usage statistics)
    """

    min_chars_per_song_lyrics = min([len(song.lyrics) for song in library])
    max_chars_per_song_lyrics = max([len(song.lyrics) for song in library])
    avg_chars_per_song_lyrics = sum([len(song.lyrics) for song in library]) / len(library)
    median_chars_per_song_lyrics = np.median([len(song.lyrics) for song in library])
    perc25_chars_per_song_lyrics = np.percentile([len(song.lyrics) for song in library], 25)
    perc75_chars_per_song_lyrics = np.percentile([len(song.lyrics) for song in library], 75)

    max_chars_song = max(library, key=lambda x: len(x.lyrics))

    with open("/tmp/max_chars_song.txt", "w") as f:
        f.write(str(max_chars_song))
    print(f"MIN CHARS PER SONG LYRICS = {min_chars_per_song_lyrics}")
    print(f"MAX CHARS PER SONG LYRICS = {max_chars_per_song_lyrics}")
    print(f"AVG CHARS PER SONG LYRICS = {avg_chars_per_song_lyrics}")   
    print(f"MEDIAN CHARS PER SONG LYRICS = {median_chars_per_song_lyrics}")
    print(f"PERC25 CHARS PER SONG LYRICS = {perc25_chars_per_song_lyrics}")
    print(f"PERC75 CHARS PER SONG LYRICS = {perc75_chars_per_song_lyrics}")

    # Break library into chunks of chunk_size songs
    chunks = [library[i:i + chunk_size] for i in range(0, len(library), chunk_size)]

    if verbose:
        print(f"NUMBER OF CHUNKS= {len(chunks)}")
        print(f"SONGS PER CHUNK = {[len(chunk) for chunk in chunks]}")
    
    # Run recursive search on each chunk
    filtered_songs = []
    total_token_usage = {
        'total_input_tokens': 0,
        'total_output_tokens': 0,
        'total_requests': 0,
        'requests_breakdown': []
    }
    
    for chunk in chunks:
        chunk_results, chunk_token_usage = recursive_search(client, chunk, user_query, n=n, verbose=verbose)
        filtered_songs.extend(chunk_results)
        
        # Aggregate token usage
        total_token_usage['total_input_tokens'] += chunk_token_usage.get('input_tokens', 0)
        total_token_usage['total_output_tokens'] += chunk_token_usage.get('output_tokens', 0)
        total_token_usage['total_requests'] += 1
        total_token_usage['requests_breakdown'].append({
            'chunk_size': len(chunk),
            'input_tokens': chunk_token_usage.get('input_tokens', 0),
            'output_tokens': chunk_token_usage.get('output_tokens', 0)
        })
    
    if verbose:
        print(f"NUMBER OF FILTERED SONGS BEFORE REDUCING = {len(filtered_songs)}")

    # If we have more songs than requested, run recursive search again on filtered set
    if len(filtered_songs) > n:
        final_results, final_token_usage = recursive_search(client, filtered_songs, user_query, n=n, verbose=verbose)
        
        # Add final token usage
        total_token_usage['total_input_tokens'] += final_token_usage.get('input_tokens', 0)
        total_token_usage['total_output_tokens'] += final_token_usage.get('output_tokens', 0)
        total_token_usage['total_requests'] += 1
        total_token_usage['requests_breakdown'].append({
            'chunk_size': len(filtered_songs),
            'input_tokens': final_token_usage.get('input_tokens', 0),
            'output_tokens': final_token_usage.get('output_tokens', 0),
            'final_reduction': True
        })
        
        return final_results, total_token_usage
        
    return filtered_songs, total_token_usage

def vector_search_library(user_query: str, n: int = 10, match_threshold: float = 0.5, verbose: bool = False) -> tuple[list[Song], dict]:
    """
    Search the song library using vector similarity search.

    Args:
        user_query: The query to search for
        n: The number of songs to return
        match_threshold: The minimum similarity threshold (0.0 to 1.0)
        verbose: Whether to print verbose output

    Returns:
        A tuple of (songs that match the user's query, token usage statistics)
    """
    # Initialize Supabase client
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_service_key:
        raise Exception("Missing Supabase configuration")
    
    supabase: Client = create_client(supabase_url, supabase_service_key)
    
    # Generate embedding for the user query
    query_embedding, embedding_token_usage = create_query_embedding(user_query, verbose=verbose)
    
    if verbose:
        print(f"Generated query embedding with {len(query_embedding)} dimensions")
        print(f"Using match threshold: {match_threshold}")
        print(f"Requesting {n} matches")
    
    try:
        # Call the Supabase function to find similar songs
        response = supabase.rpc('match_songs', {
            'query_embedding': query_embedding,
            'match_threshold': match_threshold,
            'match_count': n
        }).execute()
        
        if verbose:
            print(f"Found {len(response.data)} matching songs")
        
        # Convert database results to Song objects
        songs = []
        for db_song in response.data:
            # Convert comma-delimited artists string back to list
            artists_list = [artist.strip() for artist in db_song['artists'].split(',')]
            
            song = Song(
                id=db_song['id'],
                name=db_song['name'],
                artists=artists_list,
                album=db_song['album'],
                song_link=db_song['song_link'],
                lyrics=db_song.get('lyrics', ''),
                song_metadata=db_song.get('song_metadata', ''),
                embedding=db_song.get('embedding', [])
            )
            # Add reasoning for vector search
            song.reasoning = f"Vector similarity match (similarity score based on semantic content)"
            songs.append(song)
        
        # Token usage summary
        token_usage = {
            'total_input_tokens': embedding_token_usage.get('input_tokens', 0),
            'total_output_tokens': embedding_token_usage.get('output_tokens', 0),
            'total_requests': 1,  # Only the embedding generation request
            'vector_search': True,
            'embedding_tokens': embedding_token_usage
        }
        
        if verbose:
            print(f"Vector search completed. Found {len(songs)} songs.")
            print(f"Token usage: {token_usage}")
        
        return songs, token_usage
        
    except Exception as e:
        print(f"Error in vector search: {e}")
        # Return empty results with token usage for embedding generation
        return [], {
            'total_input_tokens': embedding_token_usage.get('input_tokens', 0),
            'total_output_tokens': embedding_token_usage.get('output_tokens', 0),
            'total_requests': 1,
            'vector_search': True,
            'error': str(e)
        }

def create_query_embedding(query: str, openai_client: OpenAI = None, model: str = "text-embedding-ada-002", verbose: bool = False) -> tuple[list[float], dict]:
    """
    Create an embedding for a search query using OpenAI's embedding API.
    
    Args:
        query: The search query to create an embedding for
        openai_client: Optional OpenAI client instance. If None, creates a new one.
        model: The embedding model to use (default: text-embedding-ada-002)
        verbose: Whether to print verbose output
    
    Returns:
        A tuple of (embedding vector, token usage)
    """
    if openai_client is None:
        openai_client = OpenAI()
    
    if verbose:
        print(f"Creating embedding for query: '{query[:100]}...'")
    
    try:
        # Create embedding using OpenAI API
        response = openai_client.embeddings.create(
            model=model,
            input=query,
            encoding_format="float"
        )
        
        # Extract the embedding vector from the response
        embedding = response.data[0].embedding
        
        # Extract token usage
        token_usage = {
            'input_tokens': response.usage.prompt_tokens if hasattr(response, 'usage') else 0,
            'output_tokens': 0,  # Embedding endpoints don't have output tokens
            'total_tokens': response.usage.total_tokens if hasattr(response, 'usage') else 0
        }
        
        if verbose:
            print(f"Successfully created embedding with {len(embedding)} dimensions")
            print(f"Token usage: {token_usage}")
        
        return embedding, token_usage
        
    except Exception as e:
        print(f"Error creating query embedding: {e}")
        # Return empty embedding and token usage on error
        return [], {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0, 'error': str(e)}

def recursive_search(client: LLMClient, sublibrary: list[Song], user_query: str, n: int = 3, verbose: bool = False) -> tuple[list[Song], dict]:
    prompt = get_basic_query(sublibrary, user_query, n)

    if verbose:
        print("PROMPT LENGTH")
        print(len(prompt))
    
    # The generate method expects list[list[GeneralContentBlock]]
    # So we need to wrap the TextPrompt in another list
    response_tuple = client.generate(
        [[TextPrompt(text=prompt)]],  # Note the double brackets
        max_tokens=1000
    )
    
    # response_tuple is (list[AssistantContentBlock], dict)
    # We want the first AssistantContentBlock's text
    response_blocks = response_tuple[0]  # This is list[AssistantContentBlock]
    first_block = response_blocks[0]     # This is the first AssistantContentBlock
    response_text = first_block.text     # This is the text content
    
    # Extract token usage from metadata
    token_usage = response_tuple[1] if len(response_tuple) > 1 else {}
    
    if verbose:
        print("RESPONSE TEXT LENGTH")
        print(len(response_text))
        print("TOKEN USAGE:")
        print(f"  Input tokens: {token_usage.get('input_tokens', 'N/A')}")
        print(f"  Output tokens: {token_usage.get('output_tokens', 'N/A')}")

    song_reasons = decode_assistant_response(response_text)

    if verbose:
        print("SONG REASONS LENGTH")
        print(len(song_reasons))
        print("SONG REASONS:")
        for song_id, reason in song_reasons:
            print(f"  ID: {song_id}, Reason: {reason}")

    # Create a mapping of song IDs to their reasoning
    id_to_song = {song.id: song for song in sublibrary}
    result_songs = []
    for song_id, reason in song_reasons:
        if song_id in id_to_song:
            song = id_to_song[song_id]
            song.reasoning = reason
            result_songs.append(song)
            if verbose:
                print(f"MATCHED: ID {song_id} -> {song.name} by {', '.join(song.artists)}")
        else:
            if verbose:
                print(f"NO MATCH: ID {song_id} not found in library")

    if verbose:
        print("SONGS WITH REASONING LENGTH")
        print(len(result_songs))

    return result_songs, token_usage

def create_song_embedding(song: Song, openai_client: OpenAI = None, model: str = "text-embedding-ada-002") -> list[float]:
    """
    Create an embedding for a song using OpenAI's embedding API.
    
    Args:
        song: The song object to create an embedding for
        openai_client: Optional OpenAI client instance. If None, creates a new one.
        model: The embedding model to use (default: text-embedding-ada-002)
    
    Returns:
        A list of floats representing the song's embedding
    """
    if openai_client is None:
        openai_client = OpenAI()
    
    song_serialization = str(song)
    
    # Create embedding using OpenAI API
    response = openai_client.embeddings.create(
        model=model,
        input=song_serialization,
        encoding_format="float"
    )
    
    # Extract the embedding vector from the response
    embedding = response.data[0].embedding
    
    return embedding
    
    