"use client";
import Image from "next/image";
import { useState, useEffect, useRef } from "react";
import { useTypingAnimation } from '../hooks/useTypingAnimation';

interface SearchFormProps {
  search: string;
  setSearch: (search: string) => void;
  isSearching: boolean;
  isAuthenticated: boolean;
  onSubmit: (e: React.FormEvent) => void;
  placeholderTexts: string[];
}

export function SearchForm({ 
  search, 
  setSearch, 
  isSearching, 
  isAuthenticated, 
  onSubmit,
  placeholderTexts 
}: SearchFormProps) {
  const [showAuthDropdown, setShowAuthDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement | null>(null);
  const askButtonRef = useRef<HTMLButtonElement | null>(null);

  // Use the typing animation hook
  const { animatedPlaceholder } = useTypingAnimation(placeholderTexts, search);

  useEffect(() => {
    if (!showAuthDropdown) return;
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowAuthDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showAuthDropdown]);

  const handleAskClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (!isAuthenticated) {
      e.preventDefault();
      setShowAuthDropdown(true);
    }
  };

  return (
    <section className="w-full max-w-2xl mx-auto mb-8 md:mb-12 px-4">
      {/* Modern Search Bar */}
      <form onSubmit={onSubmit} data-search-form className="w-full max-w-xl mx-auto flex flex-col bg-white border border-[#DDCDA8] rounded-2xl shadow-md p-3 focus-within:ring-2 focus-within:ring-[#F6A23B] transition-all relative">
        <div className="flex items-start gap-3 mb-3">
          <textarea
            className="flex-1 bg-transparent outline-none py-2 text-base md:text-lg text-[#502D07] placeholder-[#838D5A] font-roobert resize-none overflow-hidden min-h-[3rem] max-h-32"
            placeholder={animatedPlaceholder}
            value={search}
            onChange={e => setSearch(e.target.value)}
            rows={2}
            disabled={isSearching}
            style={{
              lineHeight: '1.5rem',
              height: 'auto'
            }}
            onInput={(e) => {
              const textarea = e.target as HTMLTextAreaElement;
              textarea.style.height = 'auto';
              textarea.style.height = Math.min(textarea.scrollHeight, 128) + 'px';
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                if (e.shiftKey) {
                  // Shift+Enter: allow newline (default behavior)
                  return;
                } else {
                  e.preventDefault();
                  
                  if (!isAuthenticated && search.trim()) {
                    // If not authenticated and has search text
                    if (!showAuthDropdown) {
                      // First Enter: show auth dropdown
                      setShowAuthDropdown(true);
                    } else {
                      // Second Enter: navigate to Spotify auth
                      const authUrl = `/api/auth/spotify${search.trim() ? `?q=${encodeURIComponent(search.trim())}` : ''}`;
                      window.location.href = authUrl;
                    }
                  } else if (isAuthenticated && search.trim() && !isSearching) {
                    // If authenticated: trigger search
                    const form = e.currentTarget.closest('form');
                    if (form) {
                      form.requestSubmit();
                    }
                  }
                }
              }
            }}
          />
        </div>
        <div className="flex justify-end">
          <button
            type="submit"
            onClick={handleAskClick}
            className={`px-4 md:px-5 py-2 rounded-xl font-semibold shadow transition-colors font-roobert cursor-pointer ${!search.trim() ? 'bg-gray-400 text-white' : 'bg-[#F6A23B] text-white hover:bg-[#D18A32] active:bg-[#D18A32]'}`}
            disabled={!search.trim()}
            ref={askButtonRef}
          >
            {isSearching ? 'Searching...' : 'Find song'}
          </button>
        </div>
        {showAuthDropdown && !isAuthenticated && (
          <div
            ref={dropdownRef}
            className="absolute flex flex-col items-center"
            style={{
              right: 0,
              top: 'calc(100% + 8px)',
              zIndex: 20,
              minWidth: 0,
              position: 'absolute',
            }}
          >
            {/* Green carrot, top right of dropdown */}
            <div
              style={{
                position: 'absolute',
                right: 16, // matches dropdown horizontal padding
                top: -12,
                width: 0,
                height: 0,
                borderLeft: '12px solid transparent',
                borderRight: '12px solid transparent',
                borderBottom: '12px solid #01D75E',
                zIndex: 21,
              }}
            />
            <a
              href={`/api/auth/spotify${search.trim() ? `?q=${encodeURIComponent(search.trim())}` : ''}`}
              className="flex items-center gap-2 px-5 py-2 bg-[#01D75E] text-white rounded-lg text-base font-semibold shadow-lg hover:bg-[#01c055] active:bg-[#00b04d] transition-colors font-roobert justify-center whitespace-nowrap relative"
              style={{ zIndex: 22 }}
            >
              <Image src="/spotify/logo.png" alt="Spotify logo" width={20} height={20} className="bg-white rounded-full" />
              <span>Sign in with Spotify</span>
            </a>
          </div>
        )}
      </form>
    </section>
  );
} 