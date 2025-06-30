from .types import Song

def get_basic_query(library: list[Song], user_query: str, n: int = 3, generate_song_reasoning: bool = False) -> str:
    song_str = "\n".join([str(song) for song in library])

    if generate_song_reasoning:
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
    else:
        return f"""
Hello, I am a music library assistant. I am here to help you find songs in my library.

Here is the library:
{song_str}

Here is the user's query:
{user_query}

Which {n} songs in the library best match the user's query?

IMPORTANT: Search through the lyrics carefully for exact phrase matches. If the user is looking for a specific lyric, prioritize songs that contain that exact phrase or very close variations.

Rank songs with direct lyric or title matches above those with only thematic or emotional relevance.
If any song contains the exact phrase or a very close match to the user's query in its lyrics or title, list it first.

CRITICAL: Use the EXACT song ID numbers from the library above. Do not make up IDs or use generic numbers.

Return the songs in the following format, ordered from most relevant to least relevant:
<song_id>EXACT_ID_FROM_LIBRARY</song_id>
<song_id>EXACT_ID_FROM_LIBRARY</song_id>
<song_id>EXACT_ID_FROM_LIBRARY</song_id>

Example: If a song has ID "12345" in the library, use <song_id>12345</song_id>
"""


def decode_assistant_response(response: str, generate_song_reasoning: bool = False) -> list[tuple[str, str]]:
    """
    Decode the assistant response to extract song IDs and their reasoning.
    
    Returns:
        List of tuples containing (song_id, reasoning)
    """
    if generate_song_reasoning:
        song_reasons = []
        lines = response.split("\n")
        current_song_id = None
        
        for line in lines:
            line = line.strip()
            if line.startswith("<song_id>"):
                current_song_id = line.split("<song_id>")[1].split("</song_id>")[0]
                song_reasons.append((current_song_id, ""))
    else:
        song_reasons = []
        lines = response.split("\n")
        current_song_id = None
        for line in lines:
            line = line.strip()
            if line.startswith("<song_id>"):
                current_song_id = line.split("<song_id>")[1].split("</song_id>")[0]
                song_reasons.append((current_song_id, ""))
    
    return song_reasons

def get_song_metadata_query(song_name: str, artist_names: list[str]) -> str:
    return f"""
Here is a song: "{song_name}" by {', '.join(artist_names)}.

Can you provide background info about this song / artist? 
What is the genre? What time period was it written in? 
What is the musical movement it comes from? 
What does it reference? What is its cultural significance?
"""

def get_song_doc_embedding_prompt(song: Song) -> str:
    return f"""
You are a music expert filing away information about all the music in the world.

Here is a song: "{song.name}" by {', '.join(song.artists)}.

Here are its lyrics:
{song.lyrics}

Here are some more details about the song:
{song.song_metadata}
"""

def get_song_query_embedding_prompt(user_query: str) -> str:
    return f"""
You are a music expert working at a record store.. You are speaking to a customer who is trying to remember the name of a song.
Here is the customer's description of the song:
{user_query}

Can you help the customer remember the name of the song?
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
Hello, I am a music library assistant. I need to explain why this song matches the user's query. If it doesn't match, I have a mechanism
to filter it out.

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

Tips on the tone:
- Keep your tone casual and conversational. Don't be too formal. Don't be too verbose.
- Don't recite the song name or artist name in your explanation. The user already knows it.
- If the query is just "patti", then an explanation for a song by Patti Smith should simply be "Matching first name".
- Always use proper punctuation. In particular, use a period at the end of your explanation.

Return your explanation in this exact format:
<filter_out>true</filter_out>
<reason>your specific explanation here</reason>

Note that there are two XML tags in the response. The first one is <filter_out> and the second one is <reason>.
- If the song should be filtered out, set <filter_out> to true.
- If the song should not be filtered out, set <filter_out> to false.
- If the song should be filtered out, the <reason> tag should be empty.
- If the song should not be filtered out, the <reason> tag should be the explanation for why the song matches the query.

----
HERE IS AN EXAMPLE OF AN EXPLANATION THAT IS TOO VERBOSE:
The song "Suzanne" by Hope Sandoval & The Warm Inventions reflects themes of longing and personal connections, 
evoking a similar emotional tone as works by artists like Patti Smith, making it resonate with listeners who appreciate introspective and emotionally rich music.
"""

def decode_individual_song_reasoning(response: str) -> tuple[bool, str]:
    """
    Decode the assistant response to extract individual song reasoning.
    
    Returns:
        A tuple of (filter_out, reason)
    """
    lines = response.strip().split("\n") 
    assert len(lines) in [1,2], "Expected 2 lines in the response"
    filter_out = lines[0].split("<filter_out>")[1].split("</filter_out>")[0] == "true"
    if filter_out:
        return True, ""
    else:
        reason = lines[1].split("<reason>")[1].split("</reason>")[0]
        return False, reason