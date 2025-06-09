from dataclasses import dataclass

@dataclass
class Song:
    id: str
    song_link: str
    song_metadata: str
    lyrics: str
    name: str
    artist: str

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
Artist
------------
{self.artist}
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