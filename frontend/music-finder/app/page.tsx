"use client";
import Image from "next/image";
import { useState, useEffect } from "react";
import { useRouter } from 'next/navigation';
import localFont from 'next/font/local';

const roobert = localFont({
  src: '../public/fonts/Roobert/RoobertUprightsVF.woff2',
  variable: '--font-roobert',
  display: 'swap',
});

// Add font-face declaration
const proximaNovaExtrabold = `
  @font-face {
    font-family: 'Proxima Nova';
    src: url('/fonts/proximanova/proximanova-extrabold-webfont.woff2') format('woff2'),
         url('/fonts/proximanova/proximanova-extrabold-webfont.woff') format('woff'),
         url('/fonts/proximanova/proximanova-extrabold-webfont.ttf') format('truetype');
    font-weight: 800;
    font-style: normal;
  }
`;

const chatMessages = [
  { sender: "user", text: "bro what was that song we were listening to" },
  { sender: "user", text: "the one that's like yeah yeah" },
  { sender: "user", text: "oh and it was like early 2000s or smth" },
  { sender: "friend", text: "dude wtf are you talking about" },
  { sender: "friend", text: "how would i know" },
  { sender: "user", text: "no bc it's the one with the guitar solo" },
  { sender: "friend", text: "r/NameThatSong" },
  { sender: "friend", text: "or cannoli.world" },
];

interface SearchResult {
  id: string;
  name: string;
  artist: string;
  song_link: string;
}

export default function Home() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('spotify_access_token');
    const refreshToken = localStorage.getItem('spotify_refresh_token');
    const expiresAt = localStorage.getItem('spotify_token_expires_at');
    
    console.log('Auth state:', {
      hasAccessToken: !!token,
      hasRefreshToken: !!refreshToken,
      expiresAt: expiresAt ? new Date(parseInt(expiresAt)).toISOString() : 'not set',
      isExpired: expiresAt ? Date.now() > parseInt(expiresAt) : true
    });
    
    setIsAuthenticated(!!token);
    setLoading(false);
  }, []);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!search.trim()) return;

    setIsSearching(true);
    try {
      // Check if token is expired
      const expiresAt = localStorage.getItem('spotify_token_expires_at');
      const refreshToken = localStorage.getItem('spotify_refresh_token');
      let token = localStorage.getItem('spotify_access_token');
      
      console.log('Token state before search:', {
        hasAccessToken: !!token,
        hasRefreshToken: !!refreshToken,
        expiresAt: expiresAt ? new Date(parseInt(expiresAt)).toISOString() : 'not set',
        isExpired: expiresAt ? Date.now() > parseInt(expiresAt) : true
      });
      
      if (expiresAt && Date.now() > parseInt(expiresAt) && !refreshToken) {
        console.warn('No refresh token, redirecting to Spotify auth');
        router.push('/api/auth/spotify');
        return;
      }

      if (expiresAt && refreshToken && Date.now() > parseInt(expiresAt)) {
        // Token is expired, try to refresh
        try {
          console.log('Attempting to refresh token...');
          const response = await fetch('/api/spotify/refresh', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refresh_token: refreshToken }),
          });
          
          if (!response.ok) {
            throw new Error('Failed to refresh token');
          }
          
          const data = await response.json();
          token = data.access_token;
          if (token) {
            localStorage.setItem('spotify_access_token', token);
            if (data.refresh_token) {
              localStorage.setItem('spotify_refresh_token', data.refresh_token);
            }
            localStorage.setItem('spotify_token_expires_at', (Date.now() + (data.expires_in * 1000)).toString());
            console.log('Token refreshed successfully');
          } else {
            throw new Error('No access token received from refresh');
          }
        } catch (refreshError) {
          console.error('Error refreshing token:', refreshError);
          router.push('/?error=unauthorized');
          return;
        }
      }

      if (!token) {
        router.push('/?error=unauthorized');
        return;
      }

      const response = await fetch('/api/spotify/search', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Refresh-Token': refreshToken || '',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query: search })
      });

      if (!response.ok) {
        throw new Error('Search failed');
      }

      const data = await response.json();
      setSearchResults(data.results || []);
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setIsSearching(false);
    }
  };

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
      <header className="w-full max-w-2xl mx-auto flex flex-col items-center mb-8 md:mb-12">
        <div className="flex items-center gap-3 mb-4 md:mb-6">
          <Image src="/logos/cannoli.png" alt="Cannoli logo" width={32} height={32} className="drop-shadow-sm md:w-9 md:h-9" />
          <span className="text-xl md:text-2xl font-roobert font-bold tracking-tight text-[#502D07]">Cannoli</span>
        </div>
        <style jsx global>{proximaNovaExtrabold}</style>
        <h1 className="font-roobert text-4xl md:text-5xl lg:text-6xl font-[800] text-[#F6A23B] text-center mb-3 md:mb-4 tracking-tight leading-tight">
          Ask <span className="text-[#502D07]">Cannoli</span>
        </h1>
        <p className="text-base md:text-lg lg:text-xl text-[#502D07] text-center max-w-xl font-normal mb-6 md:mb-8 px-4">
          Your AI music assistant. Instantly search, discover, and chat about your Spotify library.
        </p>
        {/* Modern Search Bar */}
        <form onSubmit={handleSearch} className="w-full max-w-xl flex items-center bg-white border border-[#DDCDA8] rounded-2xl shadow-md px-4 md:px-5 py-3 focus-within:ring-2 focus-within:ring-[#F6A23B] transition-all mx-4">
          <svg className="w-5 h-5 md:w-6 md:h-6 text-[#838D5A]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 104.5 4.5a7.5 7.5 0 0012.15 12.15z" /></svg>
          <input
            type="text"
            className="flex-1 bg-transparent outline-none px-3 py-2 text-base md:text-lg text-[#502D07] placeholder-[#838D5A] font-roobert"
            placeholder="that song about a roof in New York?"
            value={search}
            onChange={e => setSearch(e.target.value)}
            disabled={!isAuthenticated}
          />
          <button 
            type="submit"
            disabled={!isAuthenticated || isSearching}
            className="ml-2 px-4 md:px-5 py-2 bg-[#01D75E] text-white rounded-xl font-semibold shadow hover:bg-[#01c055] active:bg-[#00b04d] transition-colors font-roobert disabled:bg-gray-400"
          >
            {isSearching ? 'Searching...' : 'Ask'}
          </button>
        </form>
      </header>

      {/* Search Results */}
      {searchResults.length > 0 && (
        <section className="w-full max-w-2xl mx-auto mb-12 md:mb-20 px-4">
          <div className="bg-white border border-[#DDCDA8] rounded-2xl shadow-md p-4 md:p-6">
            <h2 className="text-xl font-['Proxima_Nova'] font-extrabold text-[#502D07] mb-4">Search Results</h2>
            <div className="space-y-4">
              {searchResults.map((song) => (
                <a
                  key={song.id}
                  href={song.song_link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block"
                >
                  <div className="flex items-center gap-4 p-4 bg-[#FFF5D1] rounded-lg hover:bg-[#DDCDA8] transition-colors cursor-pointer group">
                    <div className="flex-1">
                      <h3 className="font-['Proxima_Nova'] font-extrabold text-[#502D07] group-hover:text-[#F6A23B] transition-colors">
                        {song.name}
                      </h3>
                      <p className="text-sm text-[#838D5A]">
                        {song.artist}
                      </p>
                    </div>
                  </div>
                </a>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Chat Messages - Only show when there are no search results */}
      {searchResults.length === 0 && (
        <section className="w-full max-w-md mx-auto mb-8 md:mb-12 px-4">
          <div className="bg-white border border-[#DDCDA8] rounded-2xl shadow-md overflow-hidden h-[600px] flex flex-col">
            {/* iMessage Header */}
            <div className="bg-[#F7F7F7] px-4 py-6 flex items-center justify-between border-b border-[#DDCDA8]">
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-[#007AFF]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </div>
              <div className="flex flex-col items-center">
                <div className="w-10 h-10 rounded-full bg-[#E5E5EA] flex items-center justify-center mb-1.5">
                  <span className="text-base font-medium text-[#8E8E93]">J</span>
                </div>
                <span className="text-sm text-[#000000]">Jonny</span>
              </div>
              <div className="w-5"></div> {/* Spacer for balance */}
            </div>
            
            <div className="p-4 flex-1 overflow-y-auto">
              <div className="space-y-1">
                <div className="flex justify-center mb-2">
                  <span className="text-xs font-medium">
                    <span className="text-[#6C6C70]">Today</span>
                    <span className="text-[#8E8E93]"> {new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })}</span>
                  </span>
                </div>
                {chatMessages.map((message, index) => (
                  <div
                    key={index}
                    className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"} ${
                      index > 0 && message.sender !== chatMessages[index - 1].sender ? 'mt-5' : ''
                    }`}
                  >
                    <div
                      className={`max-w-[80%] px-3 py-1.5 rounded-[20px] ${
                        message.sender === "user"
                          ? "bg-[#1F8AFF] text-white"
                          : "bg-[#E5E5EA] text-black"
                      }`}
                    >
                      <p className="text-sm md:text-base">{message.text}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Auth Button */}
      <div className="w-full flex justify-center mb-6 md:mb-8 px-4">
        {isAuthenticated ? (
          <button
            onClick={() => router.push('/library')}
            className="flex items-center gap-3 px-6 md:px-7 py-2.5 md:py-3 bg-[#502D07] text-white rounded-xl text-sm md:text-base font-semibold shadow hover:scale-105 active:scale-95 transition-transform w-full md:w-auto justify-center font-roobert"
          >
            <Image src="/logos/cannoli.png" alt="Cannoli logo" width={20} height={20} className="bg-white rounded-full md:w-[22px] md:h-[22px]" />
            <span>Go to Library</span>
          </button>
        ) : (
          <a 
            href="/api/auth/spotify"
            className="flex items-center gap-3 px-6 md:px-7 py-2.5 md:py-3 bg-[#01D75E] text-white rounded-xl text-sm md:text-base font-semibold shadow hover:scale-105 active:scale-95 transition-transform w-full md:w-auto justify-center font-roobert"
          >
            <Image src="/spotify/logo.png" alt="Spotify logo" width={20} height={20} className="bg-white rounded-full md:w-[22px] md:h-[22px]" />
            <span>Sign in with Spotify</span>
          </a>
        )}
      </div>

      {/* Footer */}
      <footer className="w-full flex flex-col items-center gap-3 md:gap-4 pb-2 mt-auto px-4">
        <div className="flex gap-3 md:gap-4 flex-wrap justify-center">
          <span className="text-[#502D07] text-xs font-roobert">@cannoliworld</span>
          <a href="#" className="text-[#502D07] hover:text-[#F6A23B] text-xs font-roobert">Twitter</a>
          <a href="#" className="text-[#502D07] hover:text-[#4D41E6] text-xs font-roobert">ProductHunt</a>
        </div>
        <span className="text-[#838D5A] text-xs font-roobert">Made with ❤️ in SF</span>
      </footer>
    </div>
  );
}
