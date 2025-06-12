'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';

interface PlaylistImage {
  url: string;
  width: number;
  height: number;
}

interface PlaylistOwner {
  display_name: string;
  id: string;
}

interface Playlist {
  id: string;
  name: string;
  description: string;
  images: PlaylistImage[];
  owner: PlaylistOwner;
  type: string;
  uri: string;
  tracks: {
    total: number;
  };
}

export default function Library() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = searchParams.get('token');
    if (token) {
      // Store token in localStorage
      localStorage.setItem('spotify_access_token', token);
      // Remove token from URL
      router.replace('/library');
    }
  }, [searchParams, router]);

  useEffect(() => {
    async function fetchLibrary() {
      try {
        setLoading(true);
        setError(null);

        const token = localStorage.getItem('spotify_access_token');
        if (!token) {
          console.error('No access token found in localStorage');
          router.push('/?error=unauthorized');
          return;
        }

        const response = await fetch('/api/spotify/library', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (!response.ok) {
          if (response.status === 401) {
            console.error('Unauthorized access');
            router.push('/?error=unauthorized');
            return;
          }
          throw new Error('Failed to fetch library');
        }

        const data = await response.json();
        console.log('Library data received:', {
          hasData: !!data,
          itemCount: data?.items?.length
        });

        if (data?.items) {
          setPlaylists(data.items);
        }
      } catch (err) {
        console.error('Error fetching library:', err);
        setError('Failed to load your library. Please try again.');
      } finally {
        setLoading(false);
      }
    }

    fetchLibrary();
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 p-8">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold mb-8">Your Library</h1>
          <div className="animate-pulse space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="bg-white p-4 rounded-lg shadow">
                <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                <div className="h-4 bg-gray-200 rounded w-1/2"></div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-100 p-8">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold mb-8">Your Library</h1>
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative" role="alert">
            <strong className="font-bold">Error: </strong>
            <span className="block sm:inline">{error}</span>
            <button
              onClick={() => window.location.reload()}
              className="mt-2 bg-red-100 hover:bg-red-200 text-red-800 font-semibold py-2 px-4 rounded"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Your Library</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {playlists.map((playlist) => (
            <Link 
              key={playlist.id} 
              href={`/playlist/${playlist.id}`}
              className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow duration-200"
            >
              {playlist.images[0] && (
                <img
                  src={playlist.images[0].url}
                  alt={playlist.name}
                  className="w-full h-48 object-cover"
                />
              )}
              <div className="p-4">
                <h2 className="text-xl font-semibold mb-2">{playlist.name}</h2>
                <p className="text-gray-600 text-sm mb-2">{playlist.description}</p>
                <p className="text-gray-500 text-sm">By {playlist.owner.display_name}</p>
                <p className="text-gray-500 text-sm mt-2">{playlist.tracks.total} tracks</p>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
} 