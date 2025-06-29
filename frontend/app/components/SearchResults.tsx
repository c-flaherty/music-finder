"use client";
import { useState, useEffect } from "react";
import { SearchResult, TokenUsage } from '../types';
import { LyricsDisplay } from './LyricsDisplay';
import { TokenUsageDisplay } from './TokenUsageDisplay';
import { SpotifyPreviewImage } from './SpotifyPreviewImage';
import { getSpotifyPreviewImage } from '../utils/spotify';
import { extractDominantColor, getOptimalTextColor, createGradientBackground } from '../utils/colorExtraction';

interface SearchResultsProps {
  searchResults: SearchResult[];
  tokenUsage: TokenUsage | null;
}

interface SongCardData {
  backgroundColor: string;
  textColor: string;
  imageUrl: string | null;
}

export function SearchResults({ searchResults, tokenUsage }: SearchResultsProps) {
  const [showTokenUsage, setShowTokenUsage] = useState(false);
  const [songColors, setSongColors] = useState<{ [songId: string]: SongCardData }>({});
  const [colorsLoading, setColorsLoading] = useState(searchResults.length > 0);

  // Extract colors for each song when component mounts or searchResults change
  useEffect(() => {
    const extractColors = async () => {
      setColorsLoading(true);
      setSongColors({}); // Clear old colors immediately
      
      const colorPromises = searchResults.map(async (song) => {
        try {
          const imageUrl = await getSpotifyPreviewImage(song.song_link);
          if (imageUrl) {
            const dominantColor = await extractDominantColor(imageUrl);
            const textColor = getOptimalTextColor(dominantColor);
            const gradientBg = createGradientBackground(dominantColor);
            
            return {
              songId: song.id,
              colors: {
                backgroundColor: gradientBg,
                textColor: textColor,
                imageUrl: imageUrl
              }
            };
          }
        } catch (error) {
          console.error('Error extracting color for song:', song.id, error);
        }
        
        // Fallback colors
        return {
          songId: song.id,
          colors: {
            backgroundColor: 'linear-gradient(135deg, rgb(255, 255, 255) 0%, rgb(248, 250, 252) 100%)',
            textColor: '#000000',
            imageUrl: null
          }
        };
      });

      const results = await Promise.all(colorPromises);
      const colorMap = results.reduce((acc, result) => {
        acc[result.songId] = result.colors;
        return acc;
      }, {} as { [songId: string]: SongCardData });

      setSongColors(colorMap);
      setColorsLoading(false);
    };

    if (searchResults.length > 0) {
      extractColors();
    } else {
      setColorsLoading(false);
      setSongColors({});
    }
  }, [searchResults]);

  if (searchResults.length === 0) {
    return null;
  }

  return (
    <section className="w-full max-w-2xl mx-auto mb-8 md:mb-12 px-3 md:px-4 animate-fadeIn">
      {/* Header and Analytics */}
      <div className="flex items-center justify-end mb-3 md:mb-4">
        {/* Token Usage Toggle Button */}
        {tokenUsage && (
          <button
            onClick={() => setShowTokenUsage(!showTokenUsage)}
            className="flex items-center gap-2 text-xs md:text-sm text-[#838D5A] hover:text-[#502D07] font-medium transition-colors cursor-pointer"
          >
            🔍 Search Analytics
            <svg 
              className={`w-3 h-3 md:w-4 md:h-4 transition-transform ${showTokenUsage ? 'rotate-180' : ''}`} 
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

      {/* Loading State */}
      {colorsLoading && (
        <div className="flex items-center justify-center py-8">
          <div className="flex items-center gap-3 text-[#838D5A]">
            <div className="w-5 h-5 border-2 border-[#838D5A] border-t-transparent rounded-full animate-spin"></div>
            <span className="text-sm font-medium">Preparing your results...</span>
          </div>
        </div>
      )}

      {/* Song Cards */}
      {!colorsLoading && searchResults.every(song => songColors[song.id]) && (
        <div className="space-y-3 md:space-y-4">
          {searchResults.map((song, index) => {
            const cardData = songColors[song.id] || {
              backgroundColor: 'linear-gradient(135deg, rgb(255, 255, 255) 0%, rgb(248, 250, 252) 100%)',
              textColor: '#000000',
              imageUrl: null
            };

          return (
            <a
              key={song.id}
              href={song.song_link}
              target="_blank"
              rel="noopener noreferrer"
              className="block"
            >
              <div 
                className={`flex flex-col p-3 md:p-6 border border-[#DDCDA8] rounded-2xl shadow-md hover:shadow-lg hover:-translate-y-0.5 cursor-pointer group`}
                style={{ 
                  background: cardData.backgroundColor,
                }}
              >
                {/* Mobile Layout - Album cover top left with text wrapping */}
                <div className="sm:hidden">
                  {/* Reasoning with floating album image */}
                  {song.reasoning && (
                    <div className="rounded-lg p-2">
                      {/* Album Image - Float left */}
                      <div className="float-left mr-3 mb-2">
                        <SpotifyPreviewImage 
                          spotifyUrl={song.song_link} 
                          songName={song.name} 
                          title={song.name} 
                          artist={song.artists.join(', ')} 
                          preloadedImageUrl={cardData.imageUrl}
                        />
                      </div>
                      <p 
                        className="text-sm font-medium leading-relaxed"
                        style={{ 
                          color: cardData.textColor,
                        }}
                      >
                        {song.reasoning}
                      </p>
                      {/* Clear float */}
                      <div className="clear-both"></div>
                    </div>
                  )}
                </div>

                {/* Desktop/Tablet Layout - Side by side */}
                <div className="hidden sm:flex flex-row gap-4">
                  {/* Album Image */}
                  <div className="flex-shrink-0 self-center">
                    <SpotifyPreviewImage 
                      spotifyUrl={song.song_link} 
                      songName={song.name} 
                      title={song.name} 
                      artist={song.artists.join(', ')} 
                      preloadedImageUrl={cardData.imageUrl}
                    />
                  </div>

                  {/* Content */}
                  <div className="flex-1 flex flex-col gap-3 min-w-0">
                    {/* Reasoning */}
                    {song.reasoning && (
                      <div className="rounded-lg p-3">
                        <p 
                          className="text-sm font-medium"
                          style={{ 
                            color: cardData.textColor,
                            fontSize: '1.1em',
                            lineHeight: '1.5'
                          }}
                        >
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
          );
        })}
        </div>
      )}
    </section>
  );
}
