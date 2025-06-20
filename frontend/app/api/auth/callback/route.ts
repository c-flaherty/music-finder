import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function GET(request: Request) {
  console.log('Callback received:', {
    code: request.url.includes('code=') ? 'present' : 'missing',
    error: request.url.includes('error=') ? new URL(request.url).searchParams.get('error') : null
  });

  const url = new URL(request.url);
  const code = url.searchParams.get('code');
  const error = url.searchParams.get('error');
  const state = url.searchParams.get('state');
  
  // Parse state to get q param and start_search flag
  let q: string | undefined;
  let startSearch: boolean = false;
  if (state) {
    try {
      const parsed = JSON.parse(state);
      q = parsed.q ? decodeURIComponent(parsed.q) : undefined;
      startSearch = parsed.start_search === true;
    } catch (e) {
      console.error('Failed to parse state:', e);
    }
  }

  if (error) {
    console.error('Spotify auth error:', error);
    return NextResponse.redirect(new URL('/?error=auth_failed', request.url));
  }

  if (!code) {
    console.error('No code received from Spotify');
    return NextResponse.redirect(new URL('/?error=no_code', request.url));
  }

  try {
    console.log('Exchanging code for tokens...');
    const tokenResponse = await fetch('https://accounts.spotify.com/api/token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': `Basic ${Buffer.from(`${process.env.SPOTIFY_CLIENT_ID}:${process.env.SPOTIFY_CLIENT_SECRET}`).toString('base64')}`
      },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        code,
        redirect_uri: process.env.SPOTIFY_REDIRECT_URI!
      })
    });

    const tokens = await tokenResponse.json();
    
    console.log('Tokens received:', {
      hasAccessToken: !!tokens.access_token,
      hasRefreshToken: !!tokens.refresh_token,
      expiresIn: tokens.expires_in,
      refreshToken: tokens.refresh_token ? 'present' : 'missing'
    });

    if (!tokens.access_token) {
      console.error('No access token in response:', tokens);
      return NextResponse.redirect(new URL('/?error=no_token', request.url));
    }

    // Create a URL with both tokens as query parameters
    const redirectUrl = new URL('/', request.url);
    redirectUrl.searchParams.set('access_token', tokens.access_token);
    if (tokens.refresh_token) {
      redirectUrl.searchParams.set('refresh_token', tokens.refresh_token);
    }
    redirectUrl.searchParams.set('expires_in', tokens.expires_in.toString());
    
    // If q was in state, forward it
    if (q) {
      redirectUrl.searchParams.set('q', q);
    }
    
    // If start_search was in state, forward it
    if (startSearch) {
      redirectUrl.searchParams.set('start_search', 'true');
    }
    
    console.log('Redirecting to library page with tokens:', {
      hasAccessToken: true,
      hasRefreshToken: !!tokens.refresh_token,
      expiresIn: tokens.expires_in
    });
    return NextResponse.redirect(redirectUrl);

  } catch (error) {
    console.error('Error exchanging code for tokens:', error);
    return NextResponse.redirect(new URL('/?error=token_exchange_failed', request.url));
  }
} 