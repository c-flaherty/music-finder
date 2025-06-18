from dataclasses import dataclass, field

@dataclass
class RawSong:
    id: str
    song_link: str
    album: str
    name: str
    artists: list[str]

    def __str__(self):
        return f"""
------------
ID
------------
{self.id}
------------
Name
------------
{self.name}
------------
Artists
------------
{', '.join(self.artists)}
------------
Song Link
------------
{self.song_link}
------------
Song Metadata
------------
{self.song_metadata}
------------
Lyrics
------------
{self.lyrics}
------------
"""
    
@dataclass
class Song(RawSong):
    lyrics: str
    song_metadata: str
    reasoning: str = ""