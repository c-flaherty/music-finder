"use client";
import Image from "next/image";
import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { useRouter } from 'next/navigation';

import { SearchResult, TokenUsage } from './types';
import { roobert } from './fonts';
import { LyricsDisplay } from './components/LyricsDisplay';
import { TokenUsageDisplay } from './components/TokenUsageDisplay';
import { SpotifyPreviewImage } from './components/SpotifyPreviewImage';
import { Header } from './components/Header';
import { SearchForm } from './components/SearchForm';
import { SearchResults } from './components/SearchResults';
import { ChatMessages } from './components/ChatMessages';
import { ProgressSection } from './components/ProgressSection';
import { useAuth } from './hooks/useAuth';
import { useSearch } from './hooks/useSearch';

export default function Home() {
  const router = useRouter();
  const { isAuthenticated, loading, shouldAutoSearch, setShouldAutoSearch } = useAuth();
  const {
    search,
    setSearch,
    searchResults,
    tokenUsage,
    isSearching,
    animatedProgress,
    showProgress,
    displayMessage,
    messageAnimating,
    showLargeBatchAlert,
    handleSearch,
  } = useSearch();

  const placeholderTexts = useMemo(() => [
    "that song about a roof in New York?",
    "the one that goes yeah yeah yeah",
    "song with the guitar solo",
    "early 2000s rock song",
    "that catchy chorus from TikTok",
    "the song from that movie",
    "upbeat song with drums"
  ], []);

  useEffect(() => {
    let startX = 0;
    let startY = 0;
    const handleTouchStart = (e: TouchEvent) => {
      if (e.touches && e.touches.length === 1) {
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
      }
    };
    const handleTouchMove = (e: TouchEvent) => {
      if (e.touches && e.touches.length === 1) {
        const dx = Math.abs(e.touches[0].clientX - startX);
        const dy = Math.abs(e.touches[0].clientY - startY);
        if (dx > dy && dx > 0) {
          e.preventDefault();
        }
      }
    };
    document.body.addEventListener('touchstart', handleTouchStart, { passive: false });
    document.body.addEventListener('touchmove', handleTouchMove, { passive: false });
    return () => {
      document.body.removeEventListener('touchstart', handleTouchStart);
      document.body.removeEventListener('touchmove', handleTouchMove);
    };
  }, []);





  // Auto-search effect when shouldAutoSearch is true and user is authenticated
  useEffect(() => {
    if (shouldAutoSearch && isAuthenticated && search.trim() && !isSearching) {
      setShouldAutoSearch(false); // Reset the flag
      // Trigger search programmatically by calling the search logic directly
      const triggerSearch = async () => {
        // We need to call handleSearch but it's not in scope here
        // So we'll dispatch a form submission event instead
        const form = document.querySelector('form[data-search-form]');
        if (form) {
          const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
          form.dispatchEvent(submitEvent);
        }
      };
      
      triggerSearch();
    }
  }, [shouldAutoSearch, isAuthenticated, search, isSearching, setShouldAutoSearch, handleSearch]);



  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <div className="animate-pulse">
          <div className="h-12 w-48 bg-gray-700 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen bg-[#FFF5D1] flex flex-col items-center py-8 md:py-12 px-4 ${roobert.variable} font-roobert`}>
      <style jsx global>{`
        @font-face {
          font-family: 'Proxima Nova';
          src: url('/fonts/proximanova/proximanova-extrabold-webfont.woff2') format('woff2'),
               url('/fonts/proximanova/proximanova-extrabold-webfont.woff') format('woff'),
               url('/fonts/proximanova/proximanova-extrabold-webfont.ttf') format('truetype');
          font-weight: 800;
          font-style: normal;
        }
        
        @keyframes fadeIn {
          from {
            opacity: 0;
          }
          to {
            opacity: 1;
          }
        }
        
        @keyframes slideDown {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        @keyframes shimmer {
          0% {
            background-position: -200% 0;
          }
          100% {
            background-position: 200% 0;
          }
        }
        
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        @keyframes messageStay {
          from { opacity: 1; }
          to { opacity: 0; }
        }
        
        @keyframes jitter {
          0%, 100% { transform: translate(0, 0) rotate(0deg); }
          10% { transform: translate(-5px, -5px) rotate(-1deg); }
          20% { transform: translate(5px, -5px) rotate(1deg); }
          30% { transform: translate(-5px, 5px) rotate(0deg); }
          40% { transform: translate(5px, 5px) rotate(1deg); }
          50% { transform: translate(-5px, -5px) rotate(-1deg); }
          60% { transform: translate(5px, -5px) rotate(0deg); }
          70% { transform: translate(-5px, 5px) rotate(-1deg); }
          80% { transform: translate(5px, 5px) rotate(1deg); }
          90% { transform: translate(-5px, -5px) rotate(0deg); }
        }
        
        .animate-fadeIn {
          animation: fadeIn 0.3s ease-out;
        }
        
        .animate-slideDown {
          animation: slideDown 0.4s ease-out;
        }
        
        .animate-shimmer {
          background: linear-gradient(90deg, #01D75E 25%, #01c055 50%, #01D75E 75%);
          background-size: 200% 100%;
          animation: shimmer 2s infinite;
        }
        
        .animate-fadeInUp {
          animation: fadeInUp 0.5s ease-out;
        }
        
        .animate-messageOut {
          animation: messageStay 0.2s ease-out forwards;
        }
        
        .animate-jitter {
          animation: jitter 1s infinite;
        }
        
        .animate-stagger-1 { animation-delay: 0.1s; }
        .animate-stagger-2 { animation-delay: 0.2s; }
        .animate-stagger-3 { animation-delay: 0.3s; }
        .animate-stagger-4 { animation-delay: 0.4s; }
        .animate-stagger-5 { animation-delay: 0.5s; }
      `}</style>
      {/* Header & Hero */}
      <Header />
      
      {/* Search Section */}
      <SearchForm 
        search={search}
        setSearch={setSearch}
        isSearching={isSearching}
        isAuthenticated={isAuthenticated}
        onSubmit={handleSearch}
        placeholderTexts={placeholderTexts}
      />

      {/* Progress Bar */}
      <ProgressSection 
        isSearching={isSearching}
        animatedProgress={animatedProgress}
        displayMessage={displayMessage}
        messageAnimating={messageAnimating}
        showLargeBatchAlert={showLargeBatchAlert}
      />

      {/* Search Results */}
      <SearchResults searchResults={searchResults} tokenUsage={tokenUsage} />

      {/* Chat Messages */}
      <ChatMessages 
        searchResults={searchResults}
        isSearching={isSearching}
        showProgress={showProgress}
      />
    </div>
  );
}
