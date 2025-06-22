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
