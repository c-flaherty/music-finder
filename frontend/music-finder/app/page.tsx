"use client";
import Image from "next/image";
import { useState, useEffect, useRef } from "react";
import { useRouter } from 'next/navigation';
import localFont from 'next/font/local';

const roobert = localFont({
  src: '../public/fonts/Roobert/RoobertUprightsVF.woff2',
  variable: '--font-roobert',
  display: 'swap',
});

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
  artists: string[];
  song_link: string;
  reasoning: string;
  lyrics: string;
  image_url?: string;
}

interface TokenUsage {
  total_input_tokens: number;
  total_output_tokens: number;
  total_requests: number;
  requests_breakdown: Array<{
    chunk_size: number;
    input_tokens: number;
    output_tokens: number;
    final_reduction?: boolean;
  }>;
  enrichment_requests?: number;
  search_requests?: number;
  enrichment_input_tokens?: number;
  enrichment_output_tokens?: number;
  search_input_tokens?: number;
  search_output_tokens?: number;
}

// Lyrics Display Component
const LyricsDisplay = ({ lyrics }: { lyrics: string }) => {
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

// Token Usage Display Component
const TokenUsageDisplay = ({ tokenUsage }: { tokenUsage: TokenUsage }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  console.log('TokenUsageDisplay rendered with:', tokenUsage);

  if (!tokenUsage) {
    console.log('TokenUsageDisplay: Not showing - no token usage data');
    return null;
  }

  // Show even if total_requests is 0 for debugging
  if (tokenUsage.total_requests === 0) {
    console.log('TokenUsageDisplay: Showing with zero requests for debugging');
  }

  const totalTokens = tokenUsage.total_input_tokens + tokenUsage.total_output_tokens;

  return (
<div className="bg-white/50 rounded-lg p-3  mb-4">
  

      <div className="text-sm text-[#502D07] space-y-1">
        <div className="flex justify-between">
          <span>Total tokens used:</span>
          <span className="font-medium">{totalTokens.toLocaleString()}</span>
        </div>
        <div className="flex justify-between">
          <span>Input tokens:</span>
          <span>{tokenUsage.total_input_tokens.toLocaleString()}</span>
        </div>
        <div className="flex justify-between">
          <span>Output tokens:</span>
          <span>{tokenUsage.total_output_tokens.toLocaleString()}</span>
        </div>
        <div className="flex justify-between">
          <span>LLM requests:</span>
          <span>{tokenUsage.total_requests}</span>
        </div>
        {tokenUsage.enrichment_requests !== undefined && tokenUsage.search_requests !== undefined && (
          <>
            <div className="flex justify-between">
              <span>• Enrichment requests:</span>
              <span>{tokenUsage.enrichment_requests}</span>
            </div>
            <div className="flex justify-between">
              <span>• Search requests:</span>
              <span>{tokenUsage.search_requests}</span>
            </div>
          </>
        )}
        {tokenUsage.enrichment_input_tokens !== undefined && tokenUsage.search_input_tokens !== undefined && (
          <>
            <div className="mt-2 pt-2 border-t border-[#DDCDA8]">
              <div className="text-xs text-[#502D07] font-medium mb-1">Token Breakdown:</div>
              <div className="text-xs text-[#502D07] space-y-1">
                <div className="flex justify-between">
                  <span>Enrichment tokens:</span>
                  <span>{((tokenUsage.enrichment_input_tokens || 0) + (tokenUsage.enrichment_output_tokens || 0)).toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span>Search tokens:</span>
                  <span>{((tokenUsage.search_input_tokens || 0) + (tokenUsage.search_output_tokens || 0)).toLocaleString()}</span>
                </div>
              </div>
            </div>
          </>
        )}
        {tokenUsage.total_requests === 0 && (
          <div className="text-xs text-[#838D5A] italic mt-2">
            No LLM requests were made (songs may have been cached)
          </div>
        )}
      </div>

      {isExpanded && tokenUsage.requests_breakdown.length > 0 && (
        <div className="mt-3 pt-3 border-t border-[#DDCDA8]">
          <p className="text-xs text-[#502D07] font-medium mb-2">Request Breakdown:</p>
          <div className="space-y-1">
            {tokenUsage.requests_breakdown.map((request, index) => (
              <div key={index} className="text-xs text-[#502D07] flex justify-between">
                <span>
                  {request.final_reduction ? 'Final reduction' : `Chunk ${index + 1}`}
                  ({request.chunk_size} songs)
                </span>
                <span>{request.input_tokens + request.output_tokens} tokens</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="text-xs text-[#838D5A] hover:text-[#502D07] font-medium transition-colors mt-3 w-full text-center cursor-pointer"
      >
        {isExpanded ?   'Hide chunk breakdown' : 'Show chunk breakdown'}
      </button>
    </div>
  );
};

// Function to get OpenGraph image from Spotify link
const getSpotifyPreviewImage = async (spotifyUrl: string): Promise<string | null> => {
  try {
    // Using microlink.io service to extract OG data (free, no API key needed)
    const response = await fetch(`https://api.microlink.io?url=${encodeURIComponent(spotifyUrl)}&screenshot=false&video=false`);
    const data = await response.json();

    if (data.status === 'success' && data.data && data.data.image) {
      return data.data.image.url;
    }
    return null;
  } catch (error) {
    console.error('Error fetching preview image:', error);
    return null;
  }
};

// Component for Spotify Preview Image
const SpotifyPreviewImage = ({ 
  spotifyUrl, 
  songName, 
  title, 
  artist 
}: { 
  spotifyUrl: string; 
  songName: string;
  title: string;
  artist: string;
}) => {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getSpotifyPreviewImage(spotifyUrl).then((url) => {
      setImageUrl(url);
      setLoading(false);
    });
  }, [spotifyUrl]);

  // Truncate text to fit overlay
  const truncateText = (text: string, maxLength: number) => {
    return text.length > maxLength ? text.slice(0, maxLength) + '...' : text;
  };

  const truncatedTitle = truncateText(title, 20);
  const truncatedArtist = truncateText(artist, 18);

  return (
    <div className="flex-shrink-0 relative w-36 h-36 rounded-lg overflow-hidden shadow-sm">
      {loading ? (
        <div className="w-full h-full bg-gray-200 animate-pulse flex items-center justify-center">
          <Image src="/logos/cannoli.png" alt="Cannoli logo" width={32} height={32} className="opacity-60" />
        </div>
      ) : imageUrl ? (
        <img
          src={imageUrl}
          alt={`${songName} album cover`}
          className="w-full h-full object-cover"
          onError={(e) => {
            e.currentTarget.style.display = 'none';
          }}
        />
      ) : (
        <div className="w-full h-full bg-gray-300 flex items-center justify-center">
          <svg className="w-8 h-8 text-gray-500" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
          </svg>
        </div>
      )}
      
      {/* Overlay gradient for better text readability */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent" />
      
      {/* Text overlay - always shown */}
      <div className="absolute bottom-0 left-0 right-0 p-3">
        <h4 className="text-white font-semibold text-sm leading-tight mb-1 drop-shadow-sm">
          {truncatedTitle}
        </h4>
        <p className="text-white/90 text-xs leading-tight drop-shadow-sm">
          {truncatedArtist}
        </p>
      </div>
    </div>
  );
};

export default function Home() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [tokenUsage, setTokenUsage] = useState<TokenUsage | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [showAuthDropdown, setShowAuthDropdown] = useState(false);
  const [progress, setProgress] = useState(0);
  const [total, setTotal] = useState(0);
  const [showProgress, setShowProgress] = useState(false);
  const [showTokenUsage, setShowTokenUsage] = useState(false);
  const [currentPlaceholderIndex, setCurrentPlaceholderIndex] = useState(0);
  const [typedText, setTypedText] = useState("");
  const [isTyping, setIsTyping] = useState(true);
  const [isDeleting, setIsDeleting] = useState(false);
  const dropdownRef = useRef<HTMLDivElement | null>(null);
  const askButtonRef = useRef<HTMLButtonElement | null>(null);
  const readerRef = useRef<ReadableStreamDefaultReader | null>(null);

  const placeholderTexts = [
    "that song about a roof in New York?",
    "the one that goes yeah yeah yeah",
    "song with the guitar solo",
    "early 2000s rock song",
    "that catchy chorus from TikTok",
    "the song from that movie",
    "upbeat song with drums"
  ];

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

  // Typing animation effect
  useEffect(() => {
    if (search.trim()) {
      setTypedText("");
      return; // Don't animate when user is typing
    }

    const currentText = placeholderTexts[currentPlaceholderIndex];
    let timeout: NodeJS.Timeout;

    if (isTyping && !isDeleting) {
      // Typing characters
      if (typedText.length < currentText.length) {
        timeout = setTimeout(() => {
          setTypedText(currentText.slice(0, typedText.length + 1));
        }, 50 + Math.random() * 100); // Variable typing speed (50-150ms)
      } else {
        // Finished typing, wait then start deleting
        timeout = setTimeout(() => {
          setIsDeleting(true);
        }, 2000); // Pause for 2 seconds when done typing
      }
    } else if (isDeleting) {
      // Deleting characters
      if (typedText.length > 0) {
        timeout = setTimeout(() => {
          setTypedText(typedText.slice(0, -1));
        }, 30 + Math.random() * 50); // Faster deleting (30-80ms)
      } else {
        // Finished deleting, move to next placeholder
        setIsDeleting(false);
        setCurrentPlaceholderIndex((prev) => (prev + 1) % placeholderTexts.length);
        setTimeout(() => {
          setIsTyping(true);
        }, 300); // Short pause before starting next text
      }
    }

    return () => clearTimeout(timeout);
  }, [search, typedText, isTyping, isDeleting, currentPlaceholderIndex, placeholderTexts]);

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

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const q = params.get('q');
      if (q) setSearch(q);

      // Handle tokens from URL after Spotify login
      const accessToken = params.get('access_token');
      const refreshToken = params.get('refresh_token');
      const expiresIn = params.get('expires_in');

      if (accessToken) {
        localStorage.setItem('spotify_access_token', accessToken);
        if (refreshToken) {
          localStorage.setItem('spotify_refresh_token', refreshToken);
        }
        if (expiresIn) {
          const expiresAt = Date.now() + (parseInt(expiresIn) * 1000);
          localStorage.setItem('spotify_token_expires_at', expiresAt.toString());
        }
        setIsAuthenticated(true);

        // Clean up URL to remove tokens
        const newUrl = new URL(window.location.href);
        newUrl.searchParams.delete('access_token');
        newUrl.searchParams.delete('refresh_token');
        newUrl.searchParams.delete('expires_in');
        window.history.replaceState({}, '', newUrl.toString());
      }
    }
  }, []);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!search.trim()) return;

    setIsSearching(true);
    setShowProgress(false);
    setProgress(0);
    setTotal(0);
    setSearchResults([]);

    console.log('hi3');

    try {
      // Check if token is expired
      const expiresAt = localStorage.getItem('spotify_token_expires_at');
      const refreshToken = localStorage.getItem('spotify_refresh_token');
      let token = localStorage.getItem('spotify_access_token');

      if (expiresAt && Date.now() > parseInt(expiresAt) && !refreshToken) {
        router.push('/api/auth/spotify');
        return;
      }

      if (expiresAt && refreshToken && Date.now() > parseInt(expiresAt)) {
        // Token is expired, try to refresh
        try {
          const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8001';
          const response = await fetch(`${backendUrl}/api/spotify_refresh`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refresh_token: refreshToken }),
          });

          if (!response.ok) {
            // Clear local auth and redirect to login
            localStorage.removeItem('spotify_access_token');
            localStorage.removeItem('spotify_refresh_token');
            localStorage.removeItem('spotify_token_expires_at');
            router.push(`/api/auth/spotify${search.trim() ? `?q=${encodeURIComponent(search.trim())}` : ''}`);
            return;
          }

          const data = await response.json();
          token = data.access_token;
          if (token) {
            localStorage.setItem('spotify_access_token', token);
            if (data.refresh_token) {
              localStorage.setItem('spotify_refresh_token', data.refresh_token);
            }
            localStorage.setItem('spotify_token_expires_at', (Date.now() + (data.expires_in * 1000)).toString());
          } else {
            throw new Error('No access token received from refresh');
          }
        } catch (refreshError) {
          console.error('Error refreshing token:', refreshError);
          router.push('/?error=unauthorized');
          return;
        }
      }

      console.log('hi2');

      if (!token) {
        localStorage.removeItem('spotify_access_token');
        localStorage.removeItem('spotify_refresh_token');
        localStorage.removeItem('spotify_token_expires_at');
        router.push(`/api/auth/spotify${search.trim() ? `?q=${encodeURIComponent(search.trim())}` : ''}`);
        console.log('hi5');
        return;
      }

      console.log('hi4');

      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8001';
      const fetchUrl = `${backendUrl}/api/spotify_search?query=${encodeURIComponent(search)}`;

      console.log('About to fetch:', {
        url: fetchUrl,
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Refresh-Token': refreshToken || '',
        }
      });

      try {
        const response = await fetch(fetchUrl, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Refresh-Token': refreshToken || '',
          },
        });

        console.log('hi - fetch completed with status:', response.status);

        if (!response.ok) {
          if (response.status === 401) {
            // Token invalid
            localStorage.removeItem('spotify_access_token');
            localStorage.removeItem('spotify_refresh_token');
            localStorage.removeItem('spotify_token_expires_at');
            router.push(`/api/auth/spotify${search.trim() ? `?q=${encodeURIComponent(search.trim())}` : ''}`);
            return;
          }
          throw new Error('Search failed');
        }

        // Handle streaming response
        if (!response.body) {
          throw new Error('No response body');
        }

        const reader = response.body.getReader();
        readerRef.current = reader;
        const decoder = new TextDecoder();
        let buffer = '';

        console.log('Streaming response...');

        try {
          while (true) {
            const { done, value } = await reader.read();

            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Process complete SSE messages
            const messages = buffer.split('\n\n');
            buffer = messages.pop() || ''; // Keep incomplete message in buffer

            for (const message of messages) {
              if (message.startsWith('data: ')) {
                try {
                  const data = JSON.parse(message.slice(6)); // Remove 'data: ' prefix

                  if (data.type === 'progress') {
                    setProgress(data.processed);
                    setTotal(data.total);
                    setShowProgress(true);
                  } else if (data.type === 'results') {
                    console.log('Search response data:', data);
                    console.log('Token usage data:', data.token_usage);
                    setTokenUsage(data.token_usage || null);
                    setSearchResults(data.results || []);
                    setShowProgress(false);
                  } else if (data.type === 'error') {
                    console.error('Error:', data);
                    throw new Error(data.error);
                  }
                } catch (parseError) {
                  console.error('Error parsing SSE message:', parseError);
                }
              }
            }
          }
        } finally {
          reader.releaseLock();
          readerRef.current = null;
        }

      } catch (fetchError) {
        console.error('Fetch error caught:', fetchError);
        throw fetchError;
      }

    } catch (error) {
      console.error('Search error:', error);
      setShowProgress(false);
    } finally {
      setIsSearching(false);
    }
  };

  // Cleanup function for component unmount
  useEffect(() => {
    return () => {
      if (readerRef.current) {
        readerRef.current.cancel();
        readerRef.current = null;
      }
    };
  }, []);

  const handleAskClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (!isAuthenticated) {
      e.preventDefault();
      setShowAuthDropdown(true);
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
      <header className="w-full max-w-2xl mx-auto flex flex-col items-center mb-8 md:mb-12">
        <h1 className="font-roobert text-4xl md:text-5xl lg:text-6xl font-[800] text-[#F6A23B] text-center mb-3 md:mb-4 tracking-tight leading-tight">
          Remember that song
          <span className="flex items-center justify-center w-full mt-1 gap-2" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            with <span className="text-[#502D07] ml-2">Cannoli</span>
            <Image src="/logos/cannoli.png" alt="Cannoli logo" width={64} height={64} className="drop-shadow-sm ml-2 align-middle" />
          </span>
        </h1>
        {/* <p className="text-base md:text-lg lg:text-xl text-[#502D07] text-center max-w-xl font-normal mb-6 md:mb-8 px-4">
          What&apos;s that sound? What&apos;s that song about?
        </p> */}
        {/* Modern Search Bar */}
        <form onSubmit={handleSearch} className="w-full max-w-xl flex flex-nowrap items-center bg-white border border-[#DDCDA8] rounded-2xl shadow-md px-4 md:px-5 py-3 focus-within:ring-2 focus-within:ring-[#F6A23B] transition-all mx-4 relative">
          <svg className="w-5 h-5 md:w-6 md:h-6 text-[#838D5A]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 104.5 4.5a7.5 7.5 0 0012.15 12.15z" /></svg>
          <input
            type="text"
            className="flex-1 min-w-0 bg-transparent outline-none px-3 py-2 text-base md:text-lg text-[#502D07] placeholder-[#838D5A] font-roobert"
            placeholder={typedText + (isTyping && !isDeleting ? "|" : "")}
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          <button
            type="submit"
            onClick={handleAskClick}
            className={`ml-2 px-4 md:px-5 py-2 rounded-xl font-semibold shadow transition-colors font-roobert relative flex-shrink-0 ${!search.trim() ? 'bg-gray-400 text-white' : 'bg-[#01D75E] text-white hover:bg-[#01c055] active:bg-[#00b04d]'}`}
            disabled={!search.trim()}
            ref={askButtonRef}
          >
            {isSearching ? 'Searching...' : 'Find song'}
          </button>
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
      </header>

      {/* Progress Bar */}
      {isSearching && (
        <section className="w-full max-w-2xl mx-auto mb-6 px-4 animate-fadeIn flex flex-col items-center">
          {/* Circular Progress with Cannoli */}
          <div className="relative mb-6">
            <svg
              className="w-48 h-48 md:w-56 md:h-56 transform -rotate-90"
              viewBox="0 0 160 160"
            >
              {/* Background circle */}
              <circle
                cx="80"
                cy="80"
                r="70"
                stroke="#F7F7F7"
                strokeWidth="8"
                fill="none"
              />
              {/* Progress circle */}
              <circle
                cx="80"
                cy="80"
                r="70"
                stroke="url(#progressGradient)"
                strokeWidth="8"
                fill="none"
                strokeLinecap="round"
                strokeDasharray={`${2 * Math.PI * 70}`}
                strokeDashoffset={`${2 * Math.PI * 70 * (1 - (total > 0 ? progress / total : 0))}`}
                className="transition-all duration-500 ease-out"
              />
              <defs>
                <linearGradient id="progressGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#01D75E" />
                  <stop offset="100%" stopColor="#01c055" />
                </linearGradient>
              </defs>
            </svg>
            
            {/* Cannoli image with jitter animation */}
            <div className="absolute inset-0 flex items-center justify-center">
              <Image 
                src="/logos/cannoli.png" 
                alt="Cannoli logo" 
                width={144} 
                height={144} 
                className="animate-jitter"
              />
            </div>
          </div>
          
          {/* Progress text */}
          <div className="text-center">
            <h3 className="text-lg font-['Proxima_Nova'] font-extrabold text-[#502D07] mb-2">
              {showProgress ? 'Searching your library...' : 'Analyzing your new songs...'}
            </h3>
            <p className="text-base text-[#838D5A] font-roobert">
              {showProgress ? `${progress} out of ${total} songs processed` : 'Getting ready...'}
            </p>
          </div>
        </section>
      )}

      {/* Search Results */}
      {searchResults.length > 0 && (
        <section className="w-full max-w-2xl mx-auto mb-12 md:mb-20 px-4 animate-fadeIn">
          {/* Header and Analytics */}
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-['Proxima_Nova'] font-extrabold text-[#502D07]">SEARCH RESULTS</h2>
            
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

          {/* Divider */}
          <div className="w-full h-px bg-[#DDCDA8] mb-6"></div>

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
                      <LyricsDisplay lyrics={song.lyrics} />
                    </div>
                  </div>
                </div>
              </a>
            ))}
          </div>
        </section>
      )}

      {/* Chat Messages - Only show when there are no search results and not searching */}
      {searchResults.length === 0 && !isSearching && !showProgress && (
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
                    className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"} ${index > 0 && message.sender !== chatMessages[index - 1].sender ? 'mt-5' : ''
                      }`}
                  >
                    <div
                      className={`max-w-[80%] px-3 py-1.5 rounded-[20px] ${message.sender === "user"
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
      {/* <div className="w-full flex justify-center mb-6 md:mb-8 px-4">
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
      </div> */}

      {/* Footer */}
      <footer className="w-full flex flex-col items-center gap-3 md:gap-4 pb-2 mt-auto px-4">
        <span className="text-[#838D5A] text-xs font-roobert">Made with ❤️</span>
      </footer>
    </div>
  );
}
