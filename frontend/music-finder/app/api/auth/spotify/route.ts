import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

const SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize';

const scopes = [
  'user-read-email',
  'user-read-private',
  'user-library-read',
  'playlist-read-private',
  'playlist-read-collaborative',
].join(' ');

export async function GET(request: Request) {
  const clientId = process.env.SPOTIFY_CLIENT_ID;
  const redirectUri = process.env.SPOTIFY_REDIRECT_URI;

  if (!clientId || !redirectUri) {
    return new NextResponse('Missing environment variables', { status: 500 });
  }

  // Get q param from the request
  const url = new URL(request.url);
  const q = url.searchParams.get('q');
  
  // Encode q in state parameter
  const state = q ? JSON.stringify({ q: encodeURIComponent(q) }) : undefined;

  const params = new URLSearchParams({
    response_type: 'code',
    client_id: clientId,
    scope: scopes,
    redirect_uri: redirectUri,
    show_dialog: 'true',
    ...(state && { state }),
  });

  const authUrl = `${SPOTIFY_AUTH_URL}?${params.toString()}`;
  return NextResponse.redirect(authUrl);
} 