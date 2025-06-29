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

IMPORTANT: Search through the lyrics carefully for exact phrase matches. If the user is looking for a specific lyric, prioritize songs that contain that exact phrase or very close variations.

For each song you select, provide a brief explanation of why it matches the query. Consider the lyrics, title, artist, and any other relevant information.

Rank songs with direct lyric or title matches above those with only thematic or emotional relevance.
If any song contains the exact phrase or a very close match to the user's query in its lyrics or title, list it first.

CRITICAL: Use the EXACT song ID numbers from the library above. Do not make up IDs or use generic numbers.

Return the songs in the following format, ordered from most relevant to least relevant:
<song_id>EXACT_ID_FROM_LIBRARY</song_id>
<reason>brief explanation of why this song matches the query</reason>
<song_id>EXACT_ID_FROM_LIBRARY</song_id>
<reason>brief explanation of why this song matches the query</reason>
<song_id>EXACT_ID_FROM_LIBRARY</song_id>
<reason>brief explanation of why this song matches the query</reason>

Example: If a song has ID "12345" in the library, use <song_id>12345</song_id>
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

def get_individual_song_reasoning_query(user_query: str, song: 'Song', similarity_score: float = None) -> str:
    """
    Generate a prompt for explaining why a single song matches a user's query.
    
    Args:
        user_query: The user's search query
        song: The Song object with all its information
        similarity_score: Optional similarity score from vector search
        
    Returns:
        A formatted prompt string for the LLM
    """
    
    return f"""
Hello, I am a music library assistant. I need to explain why this song matches the user's query.

Song Information:
- ID: {song.id}
- Title: {song.name}
- Artist(s): {', '.join(song.artists)}
- Album: {song.album}
- Song Metadata: {song.song_metadata if song.song_metadata else 'N/A'}
- Lyrics: {song.lyrics if song.lyrics else 'N/A'}

User's Query: {user_query}

Provide a CONCISE, specific explanation (1 sentence) of why this song matches the user's query.

Consider:
- Lyrical content and themes that match the query
- Musical style and genre (if mentioned in metadata)
- Emotional tone that aligns with the query  
- Specific phrases or concepts in the lyrics that relate to the query
- Cultural or historical significance that connects to the query

IMPORTANT: Be concise but specific. Focus on the most relevant connection between the song and the query.

Return your explanation in this exact format:
<reason>your specific explanation here</reason>
"""

def decode_individual_song_reasoning(response: str) -> str:
    """
    Decode the assistant response to extract individual song reasoning.
    
    Returns:
        The reasoning string, or a fallback message if parsing fails
    """
    lines = response.split("\n")
    
    for line in lines:
        line = line.strip()
        if line.startswith("<reason>") and line.endswith("</reason>"):
            return line.split("<reason>")[1].split("</reason>")[0]
    
    # Fallback: return the first non-empty line if parsing fails
    for line in lines:
        line = line.strip()
        if line:
            return line
    
    return "Matches the query based on semantic similarity"