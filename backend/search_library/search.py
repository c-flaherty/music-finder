from .prompts import get_basic_query, decode_assistant_response
from .types import Song
from .clients import LLMClient, TextPrompt
import numpy as np

def search_library(client: LLMClient, library: list[Song], user_query: str, n: int = 3, chunk_size: int = 1000, verbose: bool = False) -> list[Song]:
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
        A list of songs that match the user's query
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
    for chunk in chunks:
        chunk_results = recursive_search(client, chunk, user_query, n=n, verbose=verbose)
        filtered_songs.extend(chunk_results)
    
    if verbose:
        print(f"NUMBER OF FILTERED SONGS BEFORE REDUCING = {len(filtered_songs)}")

    # If we have more songs than requested, run recursive search again on filtered set
    if len(filtered_songs) > n:
        filtered_songs = recursive_search(client, filtered_songs, user_query, n=n, verbose=verbose)
        
    return filtered_songs

def recursive_search(client: LLMClient, sublibrary: list[Song], user_query: str, n: int = 3, verbose: bool = False) -> list[Song]:
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
    
    if verbose:
        print("RESPONSE TEXT LENGTH")
        print(len(response_text))

    song_reasons = decode_assistant_response(response_text)

    if verbose:
        print("SONG REASONS LENGTH")
        print(len(song_reasons))

    # Create a mapping of song IDs to their reasoning
    id_to_song = {song.id: song for song in sublibrary}
    result_songs = []
    for song_id, reason in song_reasons:
        if song_id in id_to_song:
            song = id_to_song[song_id]
            song.reasoning = reason
            result_songs.append(song)

    if verbose:
        print("SONGS WITH REASONING LENGTH")
        print(len(result_songs))

    return result_songs
    
    