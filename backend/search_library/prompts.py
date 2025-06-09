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

Return the songs in the following format:
<song_id>song id 1</song_id>
<song_id>song id 2</song_id>
<song_id>song id 3</song_id>
"""

def decode_assistant_response(response: str) -> list[str]:
    song_ids = []
    for line in response.split("\n"):
        if line.startswith("<song_id>"):
            song_ids.append(line.split("<song_id>")[1].split("</song_id>")[0])
    return song_ids

