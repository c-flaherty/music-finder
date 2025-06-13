import { NextResponse } from 'next/server';
import { headers } from 'next/headers';
import { Client as GeniusClient } from 'genius-lyrics';

interface SpotifyArtist {
  name: string;
}

interface SpotifyTrack {
  id: string;
  name: string;
  artists: SpotifyArtist[];
  external_urls: {
    spotify: string;
  };
  album: {
    name: string;
  };
  duration_ms: number;
  popularity: number;
  preview_url: string | null;
}

interface SpotifyTrackItem {
  track: SpotifyTrack;
}

interface Song {
  id: string;
  name: string;
  artist: string;
  song_link: string;
  song_metadata: string;
  lyrics: string;
}

// Initialize Genius client with access token
const genius = new GeniusClient(process.env.GENIUS_ACCESS_TOKEN);

// Helper function to fetch lyrics
async function getLyrics(songName: string, artistName: string): Promise<string> {
  try {
    const searches = await genius.songs.search(`${songName} ${artistName}`);
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
  const refreshToken = headersList.get('refresh-token');
  
  if (!authHeader?.startsWith('Bearer ')) {
    return new NextResponse('Unauthorized', { status: 401 });
  }

  let accessToken = authHeader.split(' ')[1];
  
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

    if (playlistsResponse.status === 401 && refreshToken) {
      // Token expired, attempt to refresh
      try {
        accessToken = await refreshAccessToken(refreshToken);
        // Retry the request with the new token
        const retryResponse = await fetch('https://api.spotify.com/v1/me/playlists?limit=50', {
          headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json'
          }
        });
        if (!retryResponse.ok) {
          throw new Error(`HTTP error! status: ${retryResponse.status}`);
        }
        const playlistsData = await retryResponse.json();
        return await processPlaylists(playlistsData, accessToken, query);
      } catch (refreshError) {
        console.error('Error refreshing token:', refreshError);
        return new NextResponse('Failed to refresh access token', { status: 401 });
      }
    }

    if (!playlistsResponse.ok) {
      throw new Error('Failed to fetch playlists');
    }

    const playlistsData = await playlistsResponse.json();
    return await processPlaylists(playlistsData, accessToken, query);

  } catch (error) {
    console.error('Error in search:', error);
    return new NextResponse('Failed to search songs', { status: 500 });
  }
}

async function refreshAccessToken(refreshToken: string): Promise<string> {
  const response = await fetch('https://accounts.spotify.com/api/token', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'Authorization': `Basic ${Buffer.from(`${process.env.SPOTIFY_CLIENT_ID}:${process.env.SPOTIFY_CLIENT_SECRET}`).toString('base64')}`
    },
    body: new URLSearchParams({
      grant_type: 'refresh_token',
      refresh_token: refreshToken
    })
  });

  if (!response.ok) {
    throw new Error('Failed to refresh access token');
  }

  const data = await response.json();
  return data.access_token;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function processPlaylists(playlistsData: any, accessToken: string, query: string) {
  const allSongs: Song[] = [];

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
      tracksData.items.map(async (item: SpotifyTrackItem) => {
        const song: Song = {
          id: item.track.id,
          name: item.track.name,
          artist: item.track.artists.map(a => a.name).join(', '),
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

  return NextResponse.json(await searchResponse.json());
} 