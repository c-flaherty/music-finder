"use client";
import { useMemo } from "react";

import { roobert } from './fonts';
import { Header } from './components/Header';
import { SearchForm } from './components/SearchForm';
import { SearchResults } from './components/SearchResults';
import { ChatMessages } from './components/ChatMessages';
import { ProgressSection } from './components/ProgressSection';
import { useAuth } from './hooks/useAuth';
import { useSearch } from './hooks/useSearch';
import { useTouchPreventHorizontalScroll } from './hooks/useTouchPreventHorizontalScroll';
import { placeholderTexts as placeholderTextsConstants } from './constants';

export default function Home() {
  const { isAuthenticated, loading } = useAuth();
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

  // Use the touch prevention hook
  useTouchPreventHorizontalScroll();

  const placeholderTexts = useMemo(() => placeholderTextsConstants, []);

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
