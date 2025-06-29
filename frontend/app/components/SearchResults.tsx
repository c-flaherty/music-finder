"use client";
import { useState } from "react";
import { SearchResult, TokenUsage } from '../types';
import { LyricsDisplay } from './LyricsDisplay';
import { TokenUsageDisplay } from './TokenUsageDisplay';
import { SpotifyPreviewImage } from './SpotifyPreviewImage';

interface SearchResultsProps {
  searchResults: SearchResult[];
  tokenUsage: TokenUsage | null;
}

export function SearchResults({ searchResults, tokenUsage }: SearchResultsProps) {
  const [showTokenUsage, setShowTokenUsage] = useState(false);

  if (searchResults.length === 0) {
    return null;
  }

  return (
    <section className="w-full max-w-2xl mx-auto mb-12 md:mb-20 px-4 animate-fadeIn">
      {/* Header and Analytics */}
      <div className="flex items-center justify-end mb-4">
        {/* Token Usage Toggle Button */}
        {tokenUsage && (
          <button
            onClick={() => setShowTokenUsage(!showTokenUsage)}
            className="flex items-center gap-2 text-sm text-[#838D5A] hover:text-[#502D07] font-medium transition-colors cursor-pointer"
          >
            🔍 Search Analytics
            <svg 
              className={`w-4 h-4 transition-transform ${showTokenUsage ? 'rotate-180' : ''}`} 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        )}
      </div>

      {/* Token Usage Display */}
      {tokenUsage && showTokenUsage && <TokenUsageDisplay tokenUsage={tokenUsage} />}

      {/* Song Cards */}
      <div className="space-y-4">
        {searchResults.map((song, index) => (
          <a
            key={song.id}
            href={song.song_link}
            target="_blank"
            rel="noopener noreferrer"
            className="block"
          >
            <div className={`flex flex-col p-4 md:p-6 bg-white border border-[#DDCDA8] rounded-2xl shadow-md hover:shadow-lg hover:-translate-y-0.5 transition-all duration-100 cursor-pointer group animate-fadeInUp animate-stagger-${Math.min(index + 1, 5)}`}>

              <div className="flex flex-row gap-4">
                {/* Album Image */}
                <div className="flex-shrink-0">
                  <SpotifyPreviewImage spotifyUrl={song.song_link} songName={song.name} title={song.name} artist={song.artists.join(', ')} />
                </div>

                {/* Content */}
                <div className="flex-1 flex flex-col gap-3 min-w-0">
                  {/* Reasoning */}
                  {song.reasoning && (
                    <div className="rounded-lg p-3">
                      <p className="text-sm text-[#502D07] font-medium">
                        {song.reasoning}
                      </p>
                    </div>
                  )}

                  {/* Lyrics */}
                  {/* <LyricsDisplay lyrics={song.lyrics} /> */}
                </div>
              </div>
            </div>
          </a>
        ))}
      </div>
    </section>
  );
}
