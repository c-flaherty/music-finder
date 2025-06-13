import { NextResponse } from 'next/server';
import { headers } from 'next/headers';
import Genius from 'genius-lyrics';

// Initialize Genius client with access token
const Client = new Genius.Client(process.env.GENIUS_ACCESS_TOKEN);

// Helper function to fetch lyrics
async function getLyrics(songName: string, artistName: string): Promise<string> {
  try {
    const searches = await Client.songs.search(`${songName} ${artistName}`);
    if (searches.length > 0) {
      const lyrics = await searches[0].lyrics();
      return lyrics;
    }
    return '';
  } catch (error) {
    console.error('Error fetching lyrics:', error);
    return '';
  }
}

export async function POST(request: Request) {
  const headersList = await headers();
  const authHeader = headersList.get('authorization');
  
  if (!authHeader?.startsWith('Bearer ')) {
    return new NextResponse('Unauthorized', { status: 401 });
  }

  const accessToken = authHeader.split(' ')[1];
  
  try {
    // Get the search query from the request body
    const { query } = await request.json();
    
    if (!query) {
      return new NextResponse('Missing query parameter', { status: 400 });
    }

    // First, get all playlists
    const playlistsResponse = await fetch('https://api.spotify.com/v1/me/playlists?limit=50', {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      }
    });

    if (!playlistsResponse.ok) {
      throw new Error('Failed to fetch playlists');
    }

    const playlistsData = await playlistsResponse.json();
    const allSongs: any[] = [];

    // Fetch tracks from each playlist
    for (const playlist of playlistsData.items) {
      const tracksResponse = await fetch(`https://api.spotify.com/v1/playlists/${playlist.id}/tracks`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        }
      });

      if (!tracksResponse.ok) {
        console.error(`Failed to fetch tracks for playlist ${playlist.id}`);
        continue;
      }

      const tracksData = await tracksResponse.json();
      
      // Process tracks in parallel with lyrics fetching
      const songsWithLyrics = await Promise.all(
        tracksData.items.map(async (item: any) => {
          const song = {
            id: item.track.id,
            name: item.track.name,
            artist: item.track.artists.map((a: any) => a.name).join(', '),
            song_link: item.track.external_urls.spotify,
            song_metadata: JSON.stringify({
              album: item.track.album.name,
              duration_ms: item.track.duration_ms,
              popularity: item.track.popularity,
              preview_url: item.track.preview_url
            }),
            lyrics: ''
          };

          // Fetch lyrics for the song
          song.lyrics = await getLyrics(song.name, song.artist);
          return song;
        })
      );

      allSongs.push(...songsWithLyrics);
    }

    // Remove duplicates based on song ID
    const uniqueSongs = Array.from(new Map(allSongs.map(song => [song.id, song])).values());

    // Log the songs being sent to the backend
    console.log('Sending songs to backend:', {
      totalSongs: uniqueSongs.length,
      songs: uniqueSongs.map(song => ({
        id: song.id,
        name: song.name,
        artist: song.artist,
        link: song.song_link,
        hasLyrics: !!song.lyrics,
        lyricsPreview: song.lyrics ? song.lyrics.substring(0, 100) + '...' : 'No lyrics found'
      }))
    });

    // Send the songs to our search backend
    const searchResponse = await fetch('http://localhost:8000/api/search-songs', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        query,
        songs: uniqueSongs
      })
    });

    if (!searchResponse.ok) {
      throw new Error('Failed to search songs');
    }

    const searchResults = await searchResponse.json();
    return NextResponse.json(searchResults);

  } catch (error) {
    console.error('Error in search:', error);
    return new NextResponse('Failed to search songs', { status: 500 });
  }
} 