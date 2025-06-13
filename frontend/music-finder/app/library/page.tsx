'use client';

import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';

// Add font-face declaration
const proximaNovaExtrabold = `
  @font-face {
    font-family: 'Proxima Nova';
    src: url('/fonts/proximanova/proximanova-extrabold-webfont.woff2') format('woff2'),
         url('/fonts/proximanova/proximanova-extrabold-webfont.woff') format('woff'),
         url('/fonts/proximanova/proximanova-extrabold-webfont.ttf') format('truetype');
    font-weight: 800;
    font-style: normal;
  }
`;

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

function LibraryContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = searchParams.get('token');
    if (token) {
      localStorage.setItem('spotify_access_token', token);
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
      <div className="min-h-screen bg-[#FFF5D1] p-8">
        <style jsx global>{proximaNovaExtrabold}</style>
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-['Proxima_Nova'] font-extrabold text-[#502D07] mb-8">Your Library</h1>
          <div className="animate-pulse space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="bg-white p-4 rounded-lg shadow">
                <div className="h-4 bg-[#DDCDA8] rounded w-3/4 mb-2"></div>
                <div className="h-4 bg-[#DDCDA8] rounded w-1/2"></div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#FFF5D1] p-8">
        <style jsx global>{proximaNovaExtrabold}</style>
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-['Proxima_Nova'] font-extrabold text-[#502D07] mb-8">Your Library</h1>
          <div className="bg-[#DD8982] border border-[#E67961] text-[#502D07] px-4 py-3 rounded relative" role="alert">
            <strong className="font-['Proxima_Nova'] font-extrabold">Error: </strong>
            <span className="block sm:inline">{error}</span>
            <button
              onClick={() => window.location.reload()}
              className="mt-2 bg-[#F6A23B] hover:bg-[#E67961] text-white font-['Proxima_Nova'] font-extrabold py-2 px-4 rounded"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FFF5D1] p-8">
      <style jsx global>{proximaNovaExtrabold}</style>
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-['Proxima_Nova'] font-extrabold text-[#502D07] mb-8">Your Library</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {playlists.map((playlist) => (
            <Link 
              key={playlist.id} 
              href={`/playlist/${playlist.id}`}
              className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow duration-200 border border-[#DDCDA8]"
            >
              {playlist.images[0] && (
                <Image
                  src={playlist.images[0].url}
                  alt={playlist.name}
                  width={64}
                  height={64}
                  className="w-full h-48 object-cover"
                />
              )}
              <div className="p-4">
                <h2 className="text-xl font-['Proxima_Nova'] font-extrabold text-[#502D07] mb-2">{playlist.name}</h2>
                <p className="text-[#838D5A] text-sm mb-2">{playlist.description}</p>
                <p className="text-[#838D5A] text-sm">By {playlist.owner.display_name}</p>
                <p className="text-[#838D5A] text-sm mt-2">{playlist.tracks.total} tracks</p>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function Library() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <LibraryContent />
    </Suspense>
  );
} 