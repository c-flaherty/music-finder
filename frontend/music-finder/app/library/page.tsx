'use client';

import { useState } from 'react';
import Link from 'next/link';

interface PlaylistImage {
  sources: Array<{
    url: string;
    width: number;
    height: number;
  }>;
}

interface PlaylistOwner {
  data: {
    name: string;
    uri: string;
  };
}

interface Playlist {
  name: string;
  description: string;
  uri: string;
  images: {
    items: Array<{
      sources: PlaylistImage['sources'];
    }>;
  };
  ownerV2: PlaylistOwner;
}

interface LibraryItem {
  addedAt: {
    isoString: string;
  };
  item: {
    _uri: string;
    data: Playlist;
  };
}

interface LibraryData {
  data: {
    me: {
      libraryV3: {
        items: LibraryItem[];
        totalCount: number;
      };
    };
  };
}

export default function Library() {
  const [authToken, setAuthToken] = useState('');
  const [curlCommand, setCurlCommand] = useState('');
  const [libraryData, setLibraryData] = useState<LibraryData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const parseCurlCommand = () => {
    try {
      // Extract auth token
      const authMatch = curlCommand.match(/authorization: Bearer ([^'"]+)/);
      if (authMatch) {
        setAuthToken(authMatch[1]);
      }
    } catch (err) {
      setError('Failed to parse cURL command. Please check the format.');
    }
  };

  const fetchLibrary = async () => {
    if (!authToken) {
      setError('Please provide an auth token');
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
            order: null,
            textFilter: "",
            features: ["LIKED_SONGS", "YOUR_EPISODES_V2", "PRERELEASES", "EVENTS"],
            limit: 50,
            offset: 0,
            flatten: false,
            expandedFolders: [],
            folderUri: null,
            includeFoldersWhenFlattening: true
          },
          operationName: "libraryV3",
          extensions: {
            persistedQuery: {
              version: 1,
              sha256Hash: "0082bf82412db50128add72dbdb73e2961d59100b9cbf41fb25c568bd8bc358b"
            }
          }
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setLibraryData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch library');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold">My Library</h1>
          <Link 
            href="/"
            className="px-4 py-2 bg-black text-white rounded-full hover:bg-gray-800 transition-colors"
          >
            Back to Home
          </Link>
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
        <div className="mb-8">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Auth Token
            </label>
            <input
              type="text"
              value={authToken}
              onChange={(e) => setAuthToken(e.target.value)}
              className="w-full p-2 border rounded-lg"
              placeholder="Enter your Spotify auth token"
            />
          </div>
        </div>

        <button
          onClick={fetchLibrary}
          disabled={loading}
          className="w-full px-6 py-3 bg-black text-white rounded-full hover:bg-gray-800 transition-colors disabled:bg-gray-400"
        >
          {loading ? 'Loading...' : 'Fetch Library'}
        </button>

        {error && (
          <div className="mt-4 p-4 bg-red-50 text-red-700 rounded-lg">
            {error}
          </div>
        )}

        {libraryData?.data?.me?.libraryV3 && (
          <div className="mt-8">
            <div className="mb-6">
              <h2 className="text-2xl font-bold mb-2">Your Playlists</h2>
              <p className="text-sm text-gray-500">
                {libraryData.data.me.libraryV3.totalCount} playlists
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {libraryData.data.me.libraryV3.items.map((item, index) => (
                <Link
                  key={index}
                  href={`/playlist?uri=${encodeURIComponent(item.item._uri)}&token=${encodeURIComponent(authToken)}`}
                  className="block p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <div className="aspect-square mb-3">
                    <img
                      src={item.item.data.images.items[0]?.sources[0]?.url}
                      alt={item.item.data.name}
                      className="w-full h-full object-cover rounded"
                    />
                  </div>
                  <h3 className="font-medium truncate">{item.item.data.name}</h3>
                  <p className="text-sm text-gray-600 truncate">
                    {item.item.data.ownerV2.data.name}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Added {new Date(item.addedAt.isoString).toLocaleDateString()}
                  </p>
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
} 