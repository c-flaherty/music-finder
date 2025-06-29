"use client";
import { useMemo } from "react";

import { roobert } from './fonts';
import { Header } from './components/Header';
import { CompressedHeader } from './components/CompressedHeader';
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
    stage,
    animatedProgress,
    showProgress,
    displayMessage,
    messageAnimating,
    showLargeBatchAlert,
    handleSearch,
    resetSearch,
  } = useSearch();

  // Use the touch prevention hook
  useTouchPreventHorizontalScroll();

  const placeholderTexts = useMemo(() => placeholderTextsConstants, []);
  const hasSearchResults = searchResults.length > 0;

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
    <div className={`min-h-screen ${hasSearchResults ? 'bg-[#FFFFFF]' : 'bg-[#FFF5D1]'} ${roobert.variable} font-roobert`}>
      {hasSearchResults ? (
        <>
          {/* Compressed Header with Search - shown when results are available */}
          <CompressedHeader 
            search={search}
            setSearch={setSearch}
            isSearching={isSearching}
            isAuthenticated={isAuthenticated}
            onSubmit={handleSearch}
            onReset={resetSearch}
            placeholderTexts={placeholderTexts}
          />
          
          {/* Progress Bar */}
          <ProgressSection 
            isSearching={isSearching}
            stage={stage}
            animatedProgress={animatedProgress}
            displayMessage={displayMessage}
            messageAnimating={messageAnimating}
            showLargeBatchAlert={showLargeBatchAlert}
          />

          {/* Search Results */}
          <SearchResults searchResults={searchResults} tokenUsage={tokenUsage} />
        </>
      ) : (
        <div className="flex flex-col items-center py-8 md:py-12 px-4">
          {/* Header & Hero - shown when no results */}
          <Header />
          
          {/* Search Section */}
          {!isSearching && <SearchForm 
            search={search}
            setSearch={setSearch}
            isSearching={isSearching}
            isAuthenticated={isAuthenticated}
            onSubmit={handleSearch}
            placeholderTexts={placeholderTexts}
          />}

          {/* Progress Bar */}
          <ProgressSection 
            isSearching={isSearching}
            stage={stage}
            animatedProgress={animatedProgress}
            displayMessage={displayMessage}
            messageAnimating={messageAnimating}
            showLargeBatchAlert={showLargeBatchAlert}
          />
        </div>
      )}
    </div>
  );
}
