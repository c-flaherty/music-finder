from .types import Song

def get_basic_query(library: list[Song], user_query: str, n: int = 3) -> str:
    song_str = "\n".join([str(song) for song in library])
    return f"""
Hello, I am a music library assistant. I am here to help you find songs in my library.

Here is the library:
{song_str}

Here is the user's query:
{user_query}

Which {n} songs in the library best match the user's query?

For each song you select, provide a brief explanation of why it matches the query. Consider the lyrics, title, artist, and any other relevant information.

Rank songs with direct lyric or title matches above those with only thematic or emotional relevance.
If any song contains the exact phrase or a very close match to the user's query in its lyrics or title, list it first.

Return the songs in the following format, ordered from most relevant to least relevant:
<song_id>song id 1</song_id>
<reason>brief explanation of why this song matches the query</reason>
<song_id>song id 2</song_id>
<reason>brief explanation of why this song matches the query</reason>
<song_id>song id 3</song_id>
<reason>brief explanation of why this song matches the query</reason>
"""

def decode_assistant_response(response: str) -> list[tuple[str, str]]:
    """
    Decode the assistant response to extract song IDs and their reasoning.
    
    Returns:
        List of tuples containing (song_id, reasoning)
    """
    song_reasons = []
    lines = response.split("\n")
    current_song_id = None
    
    for line in lines:
        line = line.strip()
        if line.startswith("<song_id>"):
            current_song_id = line.split("<song_id>")[1].split("</song_id>")[0]
        elif line.startswith("<reason>") and current_song_id:
            reason = line.split("<reason>")[1].split("</reason>")[0]
            song_reasons.append((current_song_id, reason))
            current_song_id = None
    
    return song_reasons

def get_song_metadata_query(song_name: str, artist_names: list[str]) -> str:
    return f"""
Here is a song: "{song_name}" by {', '.join(artist_names)}.

Can you provide background info about this song / artist? 
What is the genre? What time period was it written in? 
What is the musical movement it comes from? 
What does it reference? What is its cultural significance?
"""