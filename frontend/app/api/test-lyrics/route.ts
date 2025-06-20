import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const songId = searchParams.get('songId');

  if (!songId) {
    return new NextResponse('Missing songId parameter', { status: 400 });
  }

  // Escape the songId to prevent command injection
  const safeSongId = songId.replace(/[^0-9]/g, '');

  const command = `curl -s -H 'accept: */*' -H 'content-type: application/json' -H 'x-genius-ios-version: 7.7.0' -H 'x-genius-logged-out: true' -H 'accept-language: en-US,en;q=0.9' -H 'user-agent: Genius/1267 CFNetwork/3826.500.131 Darwin/24.5.0' --compressed 'https://api.genius.com/songs/${safeSongId}?text_format=plain,dom'`;

  try {
    const { stdout, stderr } = await execAsync(command);

    if (stderr) {
      console.error(`curl stderr for songId ${safeSongId}:`, stderr);
      // stderr is not always a fatal error, so we proceed but log it
    }

    const data = JSON.parse(stdout);
    const lyrics = data.response?.song?.lyrics?.plain;

    if (!lyrics) {
        console.error(`No lyrics found in curl response for songId: ${safeSongId}`);
        console.error('Full Genius API response from curl:', JSON.stringify(data, null, 2));
        return NextResponse.json({ success: false, message: 'No lyrics found in curl response', data });
    }

    return NextResponse.json({ success: true, lyrics });

  } catch (error) {
    console.error(`Error executing curl for songId ${safeSongId}:`, error);
    // Check if the error is due to parsing JSON, which could mean the curl command itself failed.
    if (error instanceof Error && 'stdout' in error) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        return new NextResponse(`Failed to parse JSON from curl output. Output: ${(error as any).stdout}`, { status: 500 });
    }
    return new NextResponse('Failed to execute curl command', { status: 500 });
  }
} 