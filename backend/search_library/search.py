from .prompts import get_basic_query, decode_assistant_response
from .types import Song
from .clients import LLMClient, TextPrompt
import numpy as np
from openai import OpenAI

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
    
    