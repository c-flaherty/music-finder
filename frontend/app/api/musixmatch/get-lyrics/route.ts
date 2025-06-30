import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { artist_name, track_name } = await request.json();

    if (!artist_name || !track_name) {
      return NextResponse.json({ error: 'Artist name and track name are required' }, { status: 400 });
    }

    // Call the backend MusixMatch scraper API
    const response = await fetch(`${process.env.BACKEND_URL || 'http://localhost:8001'}/musixmatch/get-lyrics`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ artist_name, track_name }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to get lyrics');
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error in get-lyrics API:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to get lyrics' },
      { status: 500 }
    );
  }
} 