import { NextResponse } from 'next/server';

const SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize';
const SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token';

const scopes = [
  'user-read-email',
  'user-read-private',
  'user-library-read',
  'playlist-read-private',
  'playlist-read-collaborative',
].join(' ');

export async function GET() {
  const clientId = process.env.SPOTIFY_CLIENT_ID;
  const redirectUri = process.env.SPOTIFY_REDIRECT_URI;

  if (!clientId || !redirectUri) {
    return new NextResponse('Missing environment variables', { status: 500 });
  }

  const params = new URLSearchParams({
    response_type: 'code',
    client_id: clientId,
    scope: scopes,
    redirect_uri: redirectUri,
    show_dialog: 'true',
  });

  const authUrl = `${SPOTIFY_AUTH_URL}?${params.toString()}`;
  return NextResponse.redirect(authUrl);
} 