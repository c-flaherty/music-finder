'use client';

import { useEffect, useState, useCallback, Suspense } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useSearchParams } from 'next/navigation';

interface Artist {
  profile: {
    name: string;
  };
  uri: string;
}

interface Track {
  name: string;
  uri: string;
  albumOfTrack: {
    name: string;
    coverArt: {
      sources: Array<{
        url: string;
        width: number;
        height: number;
      }>;
    };
  };
  artists: {
    items: Artist[];
  };
  trackDuration: {
    totalMilliseconds: number;
  };
  playcount: string;
}

interface PlaylistItem {
  addedAt: {
    isoString: string;
  };
  itemV2: {
    data: Track;
  };
}

interface PlaylistData {
  data: {
    playlistV2: {
      name: string;
      description: string;
      content: {
        items: PlaylistItem[];
        totalCount: number;
      };
    };
  };
}

function PlaylistContent() {
  const searchParams = useSearchParams();
  const [authToken, setAuthToken] = useState(searchParams.get('token') || '');
  const [playlistUri, setPlaylistUri] = useState(searchParams.get('uri') || '');
  const [curlCommand, setCurlCommand] = useState('');
  const [playlistData, setPlaylistData] = useState<PlaylistData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPlaylist = useCallback(async () => {
    if (!authToken) {
      setError('Please provide an auth token');
      return;
    }

    if (!playlistUri) {
      setError('Please provide a playlist URI');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('https://api-partner.spotify.com/pathfinder/v2/query', {
        method: 'POST',
        headers: {
          'accept': 'application/json',
          'accept-language': 'en',
          'app-platform': 'WebPlayer',
          'authorization': `Bearer ${authToken}`,
          'content-type': 'application/json;charset=UTF-8',
          'origin': 'https://open.spotify.com',
          'referer': 'https://open.spotify.com/',
          'spotify-app-version': '1.2.66.242.g7de5ae85'
        },
        body: JSON.stringify({
          variables: {
            uri: playlistUri,
            offset: 0,
            limit: 25,
            enableWatchFeedEntrypoint: false
          },
          operationName: "fetchPlaylist",
          extensions: {
            persistedQuery: {
              version: 1,
              sha256Hash: "cd2275433b29f7316176e7b5b5e098ae7744724e1a52d63549c76636b3257749"
            }
          }
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setPlaylistData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch playlist');
    } finally {
      setLoading(false);
    }
  }, [authToken, playlistUri]);

  // Auto-fetch playlist if we have both URI and token
  useEffect(() => {
    if (authToken && playlistUri) {
      fetchPlaylist();
    }
  }, [authToken, playlistUri, fetchPlaylist]);

  const parseCurlCommand = () => {
    try {
      // Extract auth token
      const authMatch = curlCommand.match(/authorization: Bearer ([^'"]+)/);
      if (authMatch) {
        setAuthToken(authMatch[1]);
      }

      // Extract playlist URI
      const uriMatch = curlCommand.match(/"uri":"([^"]+)"/);
      if (uriMatch) {
        setPlaylistUri(uriMatch[1]);
      }
    } catch (error) {
      console.error('Error parsing cURL command:', error);
      setError('Failed to parse cURL command. Please check the format.');
    }
  };

  const formatDuration = (ms: number) => {
    const minutes = Math.floor(ms / 60000);
    const seconds = Math.floor((ms % 60000) / 1000);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  return (
    <div className="min-h-screen bg-white p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold">My Playlist</h1>
          <div className="flex gap-4">
            <Link 
              href="/library"
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors"
            >
              Back to Library
            </Link>
            <Link 
              href="/"
              className="px-4 py-2 bg-black text-white rounded-full hover:bg-gray-800 transition-colors"
            >
              Back to Home
            </Link>
          </div>
        </div>

        {/* cURL Command Input */}
        <div className="mb-8">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Paste cURL Command (Optional)
          </label>
          <textarea
            value={curlCommand}
            onChange={(e) => setCurlCommand(e.target.value)}
            className="w-full h-32 p-2 border rounded-lg"
            placeholder="Paste your cURL command here..."
          />
          <button
            onClick={parseCurlCommand}
            className="mt-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
          >
            Parse cURL Command
          </button>
        </div>

        {/* Manual Input Fields */}
        <div className="mb-8 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Auth Token
            </label>
            <input
              type="text"
              value={authToken}
              onChange={(e) => setAuthToken(e.target.value)}
              className="w-full p-2 border rounded-lg"
              placeholder="Enter your auth token..."
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Playlist URI
            </label>
            <input
              type="text"
              value={playlistUri}
              onChange={(e) => setPlaylistUri(e.target.value)}
              className="w-full p-2 border rounded-lg"
              placeholder="Enter your playlist URI..."
            />
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-8 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg">
            {error}
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="mb-8 p-4 bg-gray-100 rounded-lg">
            Loading playlist data...
          </div>
        )}

        {/* Playlist Data */}
        {playlistData && (
          <div className="space-y-4">
            <h2 className="text-2xl font-bold">{playlistData.data.playlistV2.name}</h2>
            <p className="text-gray-600">{playlistData.data.playlistV2.description}</p>
            <div className="space-y-2">
              {playlistData.data.playlistV2.content.items.map((item, index) => (
                <div key={index} className="flex items-center space-x-4 p-2 bg-gray-50 rounded-lg">
                  <div className="flex-shrink-0">
                    {item.itemV2.data.albumOfTrack.coverArt.sources[0] && (
                      <Image
                        src={item.itemV2.data.albumOfTrack.coverArt.sources[0].url}
                        alt={item.itemV2.data.name}
                        width={40}
                        height={40}
                        className="rounded"
                      />
                    )}
                  </div>
                  <div className="flex-grow">
                    <h3 className="font-medium">{item.itemV2.data.name}</h3>
                    <p className="text-sm text-gray-500">
                      {item.itemV2.data.artists.items.map(artist => artist.profile.name).join(', ')}
                    </p>
                  </div>
                  <div className="text-sm text-gray-500">
                    {formatDuration(item.itemV2.data.trackDuration.totalMilliseconds)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function Playlist() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <PlaylistContent />
    </Suspense>
  );
} 