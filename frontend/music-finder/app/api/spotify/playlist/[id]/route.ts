import { NextResponse } from 'next/server';
import { headers } from 'next/headers';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function GET(request: Request) {
  // Extract playlist ID from the request URL
  const url = new URL(request.url);
  const paths = url.pathname.split('/');
  const id = paths[paths.length - 2] === 'playlist' ? paths[paths.length - 1] : paths.pop() as string;

  if (!id) {
    return new NextResponse('Playlist ID not found', { status: 400 });
  }
  
  console.log('Playlist API called for ID:', id);
  
  const headersList = await headers();
  const authHeader = headersList.get('authorization');
  
  if (!authHeader?.startsWith('Bearer ')) {
    console.error('No valid authorization header found');
    return new NextResponse('Unauthorized', { status: 401 });
  }

  const accessToken = authHeader.split(' ')[1];
  console.log('Token check:', { 
    hasAccessToken: !!accessToken,
    authHeader: authHeader ? 'present' : 'missing'
  });

  try {
    console.log('Fetching playlist from Spotify...');
    const response = await fetch(`https://api.spotify.com/v1/playlists/${id}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      console.error('Spotify API error:', {
        status: response.status,
        statusText: response.statusText,
        error: errorData
      });
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    console.log('Playlist data received:', {
      hasData: !!data,
      trackCount: data?.tracks?.items?.length
    });
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching playlist:', error);
    return new NextResponse('Failed to fetch playlist', { status: 500 });
  }
} 