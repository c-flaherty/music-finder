'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { use } from 'react';

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

interface Track {
  track: {
    id: string;
    name: string;
    artists: Array<{ name: string }>;
    album: {
      name: string;
      images: Array<{ url: string }>;
    };
    duration_ms: number;
    external_urls: {
      spotify: string;
    };
  };
}

interface Playlist {
  name: string;
  description: string;
  images: Array<{ url: string }>;
  owner: {
    display_name: string;
  };
  tracks: {
    items: Track[];
  };
}

interface PageParams {
  id: string;
}

export default function PlaylistPage({
  params,
}: {
  params: Promise<PageParams>;
}) {
  const router = useRouter();
  const [playlist, setPlaylist] = useState<Playlist | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const resolvedParams = use(params);

  useEffect(() => {
    async function fetchPlaylist() {
      try {
        setLoading(true);
        setError(null);
        
        const token = localStorage.getItem('spotify_access_token');
        if (!token) {
          console.error('No access token found');
          router.push('/?error=unauthorized');
          return;
        }

        const response = await fetch(`/api/spotify/playlist/${resolvedParams.id}`, {
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
          throw new Error('Failed to fetch playlist');
        }

        const data = await response.json();
        console.log('Playlist data received:', {
          name: data.name,
          trackCount: data.tracks?.items?.length
        });
        setPlaylist(data);
      } catch (err) {
        console.error('Error fetching playlist:', err);
        setError('Failed to load playlist. Please try again.');
      } finally {
        setLoading(false);
      }
    }

    fetchPlaylist();
  }, [resolvedParams.id, router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FFF5D1] p-8">
        <style jsx global>{proximaNovaExtrabold}</style>
        <div className="max-w-4xl mx-auto">
          <div className="animate-pulse">
            <div className="h-8 bg-[#DDCDA8] rounded w-1/3 mb-4"></div>
            <div className="h-4 bg-[#DDCDA8] rounded w-1/4 mb-8"></div>
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-16 bg-[#DDCDA8] rounded"></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#FFF5D1] p-8">
        <style jsx global>{proximaNovaExtrabold}</style>
        <div className="max-w-4xl mx-auto">
          <div className="text-center">
            <h1 className="text-2xl font-['Proxima_Nova'] font-extrabold text-[#502D07] mb-4">Error</h1>
            <p className="text-[#838D5A] mb-4">{error}</p>
            <button
              onClick={() => router.refresh()}
              className="bg-[#01D75E] hover:bg-[#01c055] text-white px-4 py-2 rounded font-['Proxima_Nova'] font-extrabold"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!playlist) {
    return null;
  }

  return (
    <div className="min-h-screen bg-[#FFF5D1] p-8">
      <style jsx global>{proximaNovaExtrabold}</style>
      <div className="max-w-4xl mx-auto">
        <Link 
          href="/library"
          className="inline-block mb-8 text-[#838D5A] hover:text-[#502D07] font-['Proxima_Nova'] font-extrabold"
        >
          ← Back to Library
        </Link>
        
        <div className="flex items-start gap-8 mb-8">
          <img 
            src={playlist.images[0]?.url} 
            alt={playlist.name}
            className="w-48 h-48 object-cover rounded-lg shadow-lg border border-[#DDCDA8]"
          />
          <div>
            <h1 className="text-4xl font-['Proxima_Nova'] font-extrabold text-[#502D07] mb-2">{playlist.name}</h1>
            <p className="text-[#838D5A] mb-4">{playlist.description}</p>
            <p className="text-[#838D5A] font-['Proxima_Nova'] font-extrabold">
              By {playlist.owner.display_name} • {playlist.tracks.items.length} tracks
            </p>
          </div>
        </div>

        <div className="space-y-2">
          {playlist.tracks.items.map((item, index) => (
            <a
              key={item.track.id}
              href={item.track.external_urls.spotify}
              target="_blank"
              rel="noopener noreferrer"
              className="block"
            >
              <div 
                className="flex items-center gap-4 p-4 bg-white rounded-lg hover:bg-[#DDCDA8] transition-colors cursor-pointer group border border-[#DDCDA8]"
              >
                <div className="flex-1">
                  <h3 className="font-['Proxima_Nova'] font-extrabold text-[#502D07] group-hover:text-[#F6A23B] transition-colors">
                    {item.track.name}
                  </h3>
                  <p className="text-sm text-[#838D5A]">
                    {item.track.artists.map(artist => artist.name).join(', ')} • {item.track.album.name}
                  </p>
                </div>
                <div className="text-[#838D5A] font-['Proxima_Nova'] font-extrabold">
                  {Math.floor(item.track.duration_ms / 60000)}:
                  {String(Math.floor((item.track.duration_ms % 60000) / 1000)).padStart(2, '0')}
                </div>
              </div>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
} 