from .prompts import get_basic_query, decode_assistant_response, get_individual_song_reasoning_query, decode_individual_song_reasoning
from .types import Song
from .clients import LLMClient, TextPrompt
import numpy as np
from openai import OpenAI
from supabase import create_client, Client
import os
import concurrent.futures
from typing import Tuple

def search_library(client: LLMClient, library: list[Song], user_query: str, n: int = 3, chunk_size: int = 1000, generate_song_reasoning: bool = False, verbose: bool = False) -> tuple[list[Song], dict]:
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
        chunk_results, chunk_token_usage = recursive_search(client, chunk, user_query, n=n, generate_song_reasoning=generate_song_reasoning, verbose=verbose)
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

def generate_many_song_reasoning(songs: list[Song], user_query: str, similarity_scores: list[float] = None, verbose: bool = False) -> tuple[list[Song], dict]:
    """
    Generate reasoning for multiple songs using concurrent processing.
    
    Args:
        songs: List of songs to generate reasoning for
        user_query: The user's search query
        similarity_scores: Optional list of similarity scores (one per song)
        verbose: Whether to print verbose output
        
    Returns:
        A tuple of (songs with reasoning attached, aggregated token usage)
    """
    if not songs:
        return [], {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}
    
    if verbose:
        print(f"Generating specific reasoning for {len(songs)} matched songs using {min(10, len(songs))} concurrent threads...")
    
    try:
        # Prepare data for concurrent processing
        song_data = []
        for i, song in enumerate(songs):
            similarity_score = similarity_scores[i] if similarity_scores and i < len(similarity_scores) else None
            song_data.append((song, user_query, similarity_score, verbose))
        
        # Use ThreadPoolExecutor with max 10 workers for concurrent reasoning generation
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all reasoning generation tasks
            future_to_song = {
                executor.submit(generate_individual_song_reasoning, song_info[0], song_info[1], song_info[2], song_info[3]): i 
                for i, song_info in enumerate(song_data)
            }
            
            # Collect results as they complete
            reasoned_songs = [None] * len(songs)  # Maintain original order
            total_reasoning_tokens = {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}
            
            for future in concurrent.futures.as_completed(future_to_song):
                song_index = future_to_song[future]
                try:
                    song_with_reasoning, token_usage = future.result()
                    reasoned_songs[song_index] = song_with_reasoning
                    
                    # Aggregate token usage
                    total_reasoning_tokens['input_tokens'] += token_usage.get('input_tokens', 0)
                    total_reasoning_tokens['output_tokens'] += token_usage.get('output_tokens', 0)
                    total_reasoning_tokens['total_tokens'] += token_usage.get('total_tokens', 0)
                    
                    if verbose:
                        print(f"Completed reasoning for: {song_with_reasoning.name}")
                        
                except Exception as e:
                    if verbose:
                        print(f"[WARNING] Failed to generate reasoning for song at index {song_index}: {e}")
                    # Use original song with fallback reasoning
                    original_song = song_data[song_index][0]
                    similarity_score = song_data[song_index][2]
                    fallback_reason = f"Vector similarity match based on semantic content"
                    if similarity_score is not None:
                        fallback_reason += f" (similarity: {similarity_score:.3f})"
                    original_song.reasoning = fallback_reason
                    reasoned_songs[song_index] = original_song
        
        # Filter out None entries and return
        final_songs = [song for song in reasoned_songs if song is not None]
        
        if verbose:
            print(f"Successfully generated reasoning for {len(final_songs)} songs using concurrent processing")
            for i, song in enumerate(final_songs):
                print(f"Song {i+1}: {song.name} - {song.reasoning}")
        
        return final_songs, total_reasoning_tokens
        
    except Exception as e:
        print(f"[WARNING] Failed to generate specific reasoning with concurrent processing: {e}")
        # Fallback to basic reasoning with similarity scores
        for i, song in enumerate(songs):
            similarity_score = similarity_scores[i] if similarity_scores and i < len(similarity_scores) else None
            if similarity_score is not None:
                song.reasoning = f"Vector similarity match based on semantic content (similarity: {similarity_score:.3f})"
            else:
                song.reasoning = "Vector similarity match based on semantic content"
        
        return songs, {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0, 'error': str(e)}

def vector_search_library(user_id: str, user_query: str, n: int = 10, match_threshold: float = 0.5, generate_song_reasoning: bool = False, verbose: bool = False) -> tuple[list[Song], dict]:
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
        response = supabase.rpc('match_songs_v2', {
            'query_emb': query_embedding,
            'p_user_id': user_id,
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
            songs.append(song)
        
        # Generate specific reasoning for each matched song using the utility function
        cleaned_reasoning_tokens = {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}
        
        if generate_song_reasoning and songs:
            # Extract similarity scores for reasoning generation
            similarity_scores = [response.data[i].get('similarity', None) for i in range(len(songs))]
            
            # Use the new utility function for concurrent reasoning generation
            songs, cleaned_reasoning_tokens = generate_many_song_reasoning(
                songs, user_query, similarity_scores, verbose
            )
        
        # Token usage summary
        token_usage = {
            'total_input_tokens': embedding_token_usage.get('input_tokens', 0) + cleaned_reasoning_tokens.get('input_tokens', 0),
            'total_output_tokens': embedding_token_usage.get('output_tokens', 0) + cleaned_reasoning_tokens.get('output_tokens', 0),
            'total_requests': 1 + (1 if cleaned_reasoning_tokens.get('input_tokens', 0) > 0 else 0),  # Embedding + reasoning (if generated)
            'vector_search': True,
            'embedding_tokens': embedding_token_usage,
            'reasoning_tokens': cleaned_reasoning_tokens
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

def recursive_search(client: LLMClient, sublibrary: list[Song], user_query: str, n: int = 3, generate_song_reasoning: bool = False, verbose: bool = False) -> tuple[list[Song], dict]:
    prompt = get_basic_query(sublibrary, user_query, n, generate_song_reasoning=generate_song_reasoning)

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

    song_reasons = decode_assistant_response(response_text, generate_song_reasoning=generate_song_reasoning)

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

def generate_individual_song_reasoning(song: Song, user_query: str, similarity_score: float = None, verbose: bool = False) -> Tuple[Song, dict]:
    """
    Generate reasoning for why a single song matches the user's query.
    
    Args:
        song: The song to generate reasoning for
        user_query: The user's search query
        similarity_score: Optional similarity score from vector search
        verbose: Whether to print verbose output
        
    Returns:
        A tuple of (song with reasoning attached, token usage)
    """
    try:
        # Import here to avoid circular imports
        from .clients import get_client, TextPrompt
        
        llm_client = get_client("openai-direct", model_name="gpt-4o")
        
        # Generate prompt for this specific song
        reasoning_prompt = get_individual_song_reasoning_query(user_query, song, similarity_score)
        
        if verbose:
            print(f"Generating reasoning for song: {song.name} by {', '.join(song.artists)}")
        
        # Generate reasoning
        response_tuple = llm_client.generate(
            [[TextPrompt(text=reasoning_prompt)]],
            max_tokens=200  # Reduced since we only need 1-2 sentences
        )
        
        response_blocks = response_tuple[0]
        reasoning_text = response_blocks[0].text
        token_usage = response_tuple[1] if len(response_tuple) > 1 else {}
        
        # Decode the reasoning
        reason = decode_individual_song_reasoning(reasoning_text)
        
        # Add similarity score to reasoning if available
        if similarity_score is not None:
            song.reasoning = f"{reason} (similarity: {similarity_score:.3f})"
        else:
            song.reasoning = reason
            
        # Clean up token usage
        cleaned_token_usage = {
            'input_tokens': token_usage.get('input_tokens', 0),
            'output_tokens': token_usage.get('output_tokens', 0),
            'total_tokens': token_usage.get('input_tokens', 0) + token_usage.get('output_tokens', 0)
        }
        
        if verbose:
            print(f"Generated reasoning for {song.name}: {reason}")
        
        return song, cleaned_token_usage
        
    except Exception as e:
        if verbose:
            print(f"[WARNING] Failed to generate reasoning for {song.name}: {e}")
        
        # Fallback reasoning
        fallback_reason = f"Vector similarity match based on semantic content"
        if similarity_score is not None:
            fallback_reason += f" (similarity: {similarity_score:.3f})"
        song.reasoning = fallback_reason
        
        return song, {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0, 'error': str(e)}
    
    