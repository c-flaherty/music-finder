import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef } from 'react';
import { useTypingAnimation } from '../hooks/useTypingAnimation';

interface CompressedHeaderProps {
  search: string;
  setSearch: (search: string) => void;
  isSearching: boolean;
  isAuthenticated: boolean;
  onSubmit: (e: React.FormEvent) => void;
  onReset: () => void;
  placeholderTexts: string[];
}

export function CompressedHeader({ 
  search, 
  setSearch, 
  isSearching, 
  isAuthenticated, 
  onSubmit,
  onReset,
  placeholderTexts 
}: CompressedHeaderProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  // Use the typing animation hook
  const { animatedPlaceholder } = useTypingAnimation(placeholderTexts, search);

  // Auto-focus the input when component mounts
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  return (
    <header className="sticky top-0 bg-[#FFF5D1] z-50 w-full border-b border-[#DDCDA8] py-3 px-3 md:py-4 md:px-4 mb-6">
      {/* Mobile Layout - Stack vertically */}
      <div className="flex flex-col gap-3 sm:hidden">
        {/* Brand */}
        <Link 
          href="/" 
          className="flex items-center justify-center gap-2 cursor-pointer hover:opacity-80 transition-opacity"
          onClick={onReset}
        >
          <Image 
            src="/logos/cannoli.png" 
            alt="Cannoli logo" 
            width={24} 
            height={24} 
            className="drop-shadow-sm" 
          />
          <span className="text-[#502D07] font-roobert font-[800] text-xl">
            Cannoli
          </span>
        </Link>
        
        {/* Search Bar */}
        <form onSubmit={onSubmit} className="w-full">
          <div className="flex items-center bg-white border border-[#DDCDA8] rounded-2xl shadow-sm px-3 py-2 focus-within:ring-2 focus-within:ring-[#F6A23B] transition-all">
            <input
              ref={inputRef}
              type="text"
              className="flex-1 bg-transparent outline-none text-sm text-[#502D07] placeholder-[#838D5A] font-roobert"
              placeholder={animatedPlaceholder}
              value={search}
              onChange={e => setSearch(e.target.value)}
              disabled={isSearching}
            />
            <button
              type="submit"
              className={`px-3 py-1.5 rounded-xl text-sm font-semibold shadow transition-colors font-roobert cursor-pointer flex-shrink-0 ${!search.trim() ? 'bg-gray-400 text-white' : 'bg-[#F6A23B] text-white hover:bg-[#D18A32] active:bg-[#D18A32]'}`}
              disabled={!search.trim() || isSearching}
            >
              {isSearching ? 'Searching...' : 'Find Song'}
            </button>
          </div>
        </form>
      </div>

      {/* Desktop/Tablet Layout - Side by side */}
      <div className="hidden sm:flex items-center w-full relative">
        {/* Brand - Fixed Left */}
        <Link 
          href="/" 
          className="flex items-center gap-2 flex-shrink-0 cursor-pointer hover:opacity-80 transition-opacity absolute left-0 z-10"
          onClick={onReset}
        >
          <Image 
            src="/logos/cannoli.png" 
            alt="Cannoli logo" 
            width={32} 
            height={32} 
            className="drop-shadow-sm" 
          />
          <span className="text-[#502D07] font-roobert font-[800] text-2xl">
            Cannoli
          </span>
          
        </Link>
        
        {/* Search Bar - Centered */}
        <form onSubmit={onSubmit} className="flex-1 flex justify-center">
          <div className="w-full max-w-2xl">
            <div className="flex items-center bg-white border border-[#DDCDA8] rounded-2xl shadow-sm px-4 py-2 focus-within:ring-2 focus-within:ring-[#F6A23B] transition-all">
              <input
                type="text"
                className="flex-1 bg-transparent outline-none text-base text-[#502D07] placeholder-[#838D5A] font-roobert"
                placeholder={animatedPlaceholder}
                value={search}
                onChange={e => setSearch(e.target.value)}
                disabled={isSearching}
              />
              <button
                type="submit"
                className={`px-3 md:px-4 py-1.5 rounded-xl font-semibold shadow transition-colors font-roobert cursor-pointer ${!search.trim() ? 'bg-gray-400 text-white' : 'bg-[#F6A23B] text-white hover:bg-[#D18A32] active:bg-[#D18A32]'}`}
                disabled={!search.trim() || isSearching}
              >
                {isSearching ? 'Searching...' : 'Find Song'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </header>
  );
} 