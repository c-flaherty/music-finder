"use client";
import { useState, useEffect } from "react";
import Image from "next/image";
import { getSpotifyPreviewImage } from "../utils/spotify";

interface SpotifyPreviewImageProps {
  spotifyUrl: string;
  songName: string;
  title: string;
  artist: string;
}

// Component for Spotify Preview Image
export const SpotifyPreviewImage = ({ 
  spotifyUrl, 
  songName, 
  title, 
  artist 
}: SpotifyPreviewImageProps) => {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getSpotifyPreviewImage(spotifyUrl).then((url) => {
      setImageUrl(url);
      setLoading(false);
    });
  }, [spotifyUrl]);

  // Truncate text to fit overlay
  const truncateText = (text: string, maxLength: number) => {
    return text.length > maxLength ? text.slice(0, maxLength) + '...' : text;
  };

  const truncatedTitle = truncateText(title, 20);
  const truncatedArtist = truncateText(artist, 18);

  return (
    <div className="flex-shrink-0 relative w-36 h-36 rounded-lg overflow-hidden shadow-sm">
      {loading ? (
        <div className="w-full h-full bg-gray-200 animate-pulse flex items-center justify-center">
          <Image src="/logos/cannoli.png" alt="Cannoli logo" width={32} height={32} className="opacity-60" />
        </div>
      ) : imageUrl ? (
        <Image
          src={imageUrl}
          alt={`${songName} album cover`}
          width={144}
          height={144}
          className="w-full h-full object-cover"
          onError={(e) => {
            e.currentTarget.style.display = 'none';
          }}
        />
      ) : (
        <div className="w-full h-full bg-gray-300 flex items-center justify-center">
          <svg className="w-8 h-8 text-gray-500" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
          </svg>
        </div>
      )}
      
      {/* Overlay gradient for better text readability */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent" />
      
      {/* Text overlay - always shown */}
      <div className="absolute bottom-0 left-0 right-0 p-3">
        <h4 className="text-white font-semibold text-sm leading-tight mb-1 drop-shadow-sm">
          {truncatedTitle}
        </h4>
        <p className="text-white/90 text-xs leading-tight drop-shadow-sm">
          {truncatedArtist}
        </p>
      </div>
    </div>
  );
};