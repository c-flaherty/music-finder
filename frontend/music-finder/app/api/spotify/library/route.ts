import { NextResponse } from 'next/server';
import { headers } from 'next/headers';

export async function GET() {
  console.log('Library API called');
  
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
    console.log('Fetching library from Spotify...');
    const response = await fetch('https://api.spotify.com/v1/me/playlists?limit=50', {
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
    console.log('Library data received:', {
      hasData: !!data,
      itemCount: data?.items?.length
    });
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching library:', error);
    return new NextResponse('Failed to fetch library', { status: 500 });
  }
} 