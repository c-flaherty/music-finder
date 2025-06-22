"use client";
import { useState } from "react";

interface LyricsDisplayProps {
  lyrics: string;
}

// Lyrics Display Component
export const LyricsDisplay = ({ lyrics }: LyricsDisplayProps) => {
    const [isExpanded, setIsExpanded] = useState(false);
  
    if (!lyrics || lyrics.trim() === '') {
      return null;
    }
  
    const snippetLength = 150;
    const shouldShowExpand = lyrics.length > snippetLength;
    const displayText = isExpanded ? lyrics : lyrics.slice(0, snippetLength) + (shouldShowExpand ? '...' : '');
  
    return (
      <div className="bg-white/50 rounded-lg p-3 border-l-4 border-[#01D75E]">
        <p className="text-sm text-[#502D07] font-medium mb-2">
          🎵 Lyrics
        </p>
        <p className="text-sm text-[#502D07] leading-relaxed whitespace-pre-line">
          {displayText}
        </p>
        {shouldShowExpand && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-xs text-[#01D75E] hover:text-[#01c055] font-medium mt-2 transition-colors"
          >
            {isExpanded ? 'Show less' : 'Show more'}
          </button>
        )}
      </div>
    );
  };