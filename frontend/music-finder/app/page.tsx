"use client";
import Image from "next/image";
import { useState, useEffect } from "react";
import { useRouter } from 'next/navigation';

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

export default function Home() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('spotify_access_token');
    setIsAuthenticated(!!token);
    setLoading(false);
  }, []);

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
    <div className="min-h-screen bg-gradient-to-br from-white via-gray-50 to-gray-100 flex flex-col items-center py-12 px-4">
      {/* Header & Hero */}
      <header className="w-full max-w-2xl mx-auto flex flex-col items-center mb-12">
        <div className="flex items-center gap-3 mb-6">
          <Image src="/spotify/logo.png" alt="Spotify logo" width={36} height={36} className="drop-shadow-sm" />
          <span className="text-2xl font-bold tracking-tight text-gray-900">Cannoli</span>
        </div>
        <h1 className="font-cherry text-5xl md:text-6xl font-extrabold text-gray-900 text-center mb-4 tracking-tight leading-tight">
          Ask <span className="bg-gradient-to-r from-green-400 to-blue-500 bg-clip-text text-transparent">Cannoli</span>
        </h1>
        <p className="text-lg md:text-xl text-gray-600 text-center max-w-xl font-normal mb-8">
          Your AI music assistant. Instantly search, discover, and chat about your Spotify library.
        </p>
        {/* Modern Search Bar */}
        <form className="w-full max-w-xl flex items-center bg-white border border-gray-200 rounded-2xl shadow-md px-5 py-3 focus-within:ring-2 focus-within:ring-green-400 transition-all">
          <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 104.5 4.5a7.5 7.5 0 0012.15 12.15z" /></svg>
          <input
            type="text"
            className="flex-1 bg-transparent outline-none px-3 py-2 text-lg text-gray-900 placeholder-gray-400"
            placeholder="that song about a roof in New York?"
            value={search}
            onChange={e => setSearch(e.target.value)}
            disabled
          />
          <button className="ml-2 px-5 py-2 bg-gradient-to-r from-green-400 to-blue-500 text-white rounded-xl font-semibold shadow hover:from-green-500 hover:to-blue-600 transition-colors" disabled>
            Ask
          </button>
        </form>
      </header>

      {/* Chat Preview */}
      <section className="w-full max-w-2xl mx-auto mb-20">
        <div className="bg-white border border-gray-200 rounded-2xl shadow-md p-6 flex flex-col gap-1">
          {chatMessages.map((msg, i) => (
            <div
              key={i}
              className={
                msg.sender === "user"
                  ? "self-end max-w-[75%]"
                  : "self-start max-w-[75%]"
              }
            >
              <div
                className={
                  msg.sender === "user"
                    ? "bg-[#007AFF] text-white px-4 py-2 rounded-full text-base font-medium shadow-sm"
                    : "bg-[#E5E5EA] text-gray-800 px-4 py-2 rounded-full text-base font-medium shadow-sm"
                }
              >
                {msg.text}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="w-full flex flex-col items-center gap-4 pb-2 mt-auto">
        {isAuthenticated ? (
          <button
            onClick={() => router.push('/library')}
            className="flex items-center gap-3 px-7 py-3 bg-black text-white rounded-xl text-base font-semibold shadow hover:scale-105 active:scale-95 transition-transform"
          >
            <Image src="/spotify/logo.png" alt="Spotify logo" width={22} height={22} className="bg-white rounded-full" />
            <span>Go to Library</span>
          </button>
        ) : (
          <a 
            href="/api/auth/spotify"
            className="flex items-center gap-3 px-7 py-3 bg-black text-white rounded-xl text-base font-semibold shadow hover:scale-105 active:scale-95 transition-transform"
          >
            <Image src="/spotify/logo.png" alt="Spotify logo" width={22} height={22} className="bg-white rounded-full" />
            <span>Sign in with Spotify</span>
          </a>
        )}
        <div className="flex gap-4">
          <span className="text-gray-400 text-xs">@cannoliworld</span>
          <a href="#" className="text-gray-400 hover:text-green-500 text-xs">Twitter</a>
          <a href="#" className="text-gray-400 hover:text-blue-500 text-xs">ProductHunt</a>
        </div>
        <span className="text-gray-300 text-xs">Made with ❤️ in SF</span>
      </footer>
    </div>
  );
}
