import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { lyrics_url } = await request.json();

    if (!lyrics_url) {
      return NextResponse.json({ error: 'Lyrics URL is required' }, { status: 400 });
    }

    // Call the backend MusixMatch scraper API
    const response = await fetch(`${process.env.BACKEND_URL || 'http://localhost:8001'}/musixmatch/get-track-by-url`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ lyrics_url }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to get track by URL');
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error in get-track-by-url API:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to get track by URL' },
      { status: 500 }
    );
  }
} 