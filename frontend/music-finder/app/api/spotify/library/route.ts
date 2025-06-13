import { NextResponse } from 'next/server';
import { headers } from 'next/headers';

async function refreshAccessToken(refreshToken: string): Promise<string> {
  const response = await fetch('https://accounts.spotify.com/api/token', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      grant_type: 'refresh_token',
      refresh_token: refreshToken,
      client_id: process.env.SPOTIFY_CLIENT_ID as string,
      client_secret: process.env.SPOTIFY_CLIENT_SECRET as string,
    }),
  });

  if (!response.ok) {
    throw new Error('Failed to refresh access token');
  }

  const data = await response.json();
  return data.access_token;
}

export async function GET(request: Request) {
  console.log('GET request received', request);
  const headersList = await headers();
  const authHeader = headersList.get('authorization');
  
  if (!authHeader?.startsWith('Bearer ')) {
    return new NextResponse('Unauthorized', { status: 401 });
  }

  let accessToken = authHeader.split(' ')[1];
  const refreshToken = headersList.get('refresh-token');
  console.log('Refresh token:', refreshToken);

  try {
    const response = await fetch('https://api.spotify.com/v1/me/playlists?limit=50', {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      }
    });

    if (response.status === 401 && refreshToken) {
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
        const data = await retryResponse.json();
        return NextResponse.json(data);
      } catch (refreshError) {
        console.error('Error refreshing token:', refreshError);
        return new NextResponse('Failed to refresh access token', { status: 401 });
      }
    }

    if (!response.ok) {
      // Return a JSON response with a redirect URL
      return NextResponse.json({ redirect: '/api/auth/spotify' }, { status: 401 });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching library:', error);
    return new NextResponse('Failed to fetch library', { status: 500 });
  }
} 