"use client";
import { useState } from "react";
import { roobert } from '../fonts';

interface MusixMatchTrack {
  track_id: number;
  track_name: string;
  track_share_url: string;
  track_edit_url: string;
  commontrack_id: number;
  instrumental: number;
  explicit: number;
  has_lyrics: number;
  has_lyrics_crowd: number;
  has_subtitles: number;
  has_richsync: number;
  num_favourite: number;
  lyrics_id: number;
  subtitle_id: number;
  album_id: number;
  album_name: string;
  artist_id: number;
  artist_name: string;
  track_spotify_id: string;
  commontrack_vanity_id: string;
  restricted: number;
  first_release_date: string;
  updated_time: string;
  primary_genres: {
    music_genre_list: Array<{
      music_genre: {
        music_genre_id: number;
        music_genre_parent_id: number;
        music_genre_name: string;
        music_genre_name_extended: string;
        music_genre_vanity: string;
      };
    }>;
  };
  secondary_genres: {
    music_genre_list: Array<{
      music_genre: {
        music_genre_id: number;
        music_genre_parent_id: number;
        music_genre_name: string;
        music_genre_name_extended: string;
        music_genre_vanity: string;
      };
    }>;
  };
}

interface MusixMatchLyrics {
  lyrics_id: number;
  restricted: number;
  instrumental: number;
  lyrics_body: string;
  lyrics_language: string;
  script_tracking_url: string;
  pixel_tracking_url: string;
  html_tracking_url: string;
  lyrics_copyright: string;
  backlink_url: string;
  updated_time: string;
}

interface MusixMatchResponse {
  message: {
    header: {
      status_code: number;
      execute_time: number;
    };
    body: any;
  };
}

interface Track {
  track_id: string;
  track_name: string;
  artist_name: string;
  album_name?: string;
  track_share_url?: string;
}

interface LyricsResponse {
  track_id: string;
  track_name: string;
  artist_name: string;
  album_name?: string;
  lyrics_body: string;
  lyrics_copyright?: string;
  track_share_url?: string;
}

interface TrackByUrlResponse {
  track_id: string;
  track_name: string;
  artist_name: string;
  album_name?: string;
  lyrics_body: string;
  lyrics_copyright?: string;
  track_share_url?: string;
}

export default function MusixMatchTestPage() {
  const [artistName, setArtistName] = useState("");
  const [trackName, setTrackName] = useState("");
  const [lyricsResult, setLyricsResult] = useState<LyricsResponse | null>(null);
  const [lyricsLoading, setLyricsLoading] = useState(false);
  const [lyricsError, setLyricsError] = useState("");

  const [lyricsUrl, setLyricsUrl] = useState("");
  const [urlResult, setUrlResult] = useState<TrackByUrlResponse | null>(null);
  const [urlLoading, setUrlLoading] = useState(false);
  const [urlError, setUrlError] = useState("");

  const handleGetLyrics = async () => {
    if (!artistName.trim() || !trackName.trim()) return;

    setLyricsLoading(true);
    setLyricsError("");
    setLyricsResult(null);

    try {
      const response = await fetch("/api/musixmatch/get-lyrics", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ artist_name: artistName, track_name: trackName }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to get lyrics");
      }

      setLyricsResult(data);
    } catch (error) {
      setLyricsError(error instanceof Error ? error.message : "Failed to get lyrics");
    } finally {
      setLyricsLoading(false);
    }
  };

  const handleGetTrackByUrl = async () => {
    if (!lyricsUrl.trim()) return;

    setUrlLoading(true);
    setUrlError("");
    setUrlResult(null);

    try {
      const response = await fetch("/api/musixmatch/get-track-by-url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lyrics_url: lyricsUrl }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to get track by URL");
      }

      setUrlResult(data);
    } catch (error) {
      setUrlError(error instanceof Error ? error.message : "Failed to get track by URL");
    } finally {
      setUrlLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold text-white mb-8 text-center">
          MusixMatch Scraper Test
        </h1>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Get Lyrics */}
          <div className="bg-white/10 backdrop-blur-lg rounded-lg p-6">
            <h2 className="text-2xl font-semibold text-white mb-4">Get Lyrics</h2>
            <div className="space-y-4">
              <input
                type="text"
                placeholder="Artist name"
                value={artistName}
                onChange={(e) => setArtistName(e.target.value)}
                className="w-full px-4 py-2 bg-white/20 border border-white/30 rounded-lg text-white placeholder-white/70 focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
              <input
                type="text"
                placeholder="Track name"
                value={trackName}
                onChange={(e) => setTrackName(e.target.value)}
                className="w-full px-4 py-2 bg-white/20 border border-white/30 rounded-lg text-white placeholder-white/70 focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
              <button
                onClick={handleGetLyrics}
                disabled={lyricsLoading}
                className="w-full px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-green-800 text-white rounded-lg transition-colors"
              >
                {lyricsLoading ? "Getting Lyrics..." : "Get Lyrics"}
              </button>
              
              {lyricsError && (
                <div className="text-red-400 text-sm bg-red-900/20 p-3 rounded-lg">
                  {lyricsError}
                </div>
              )}

              {lyricsResult && (
                <div className="bg-white/10 p-4 rounded-lg">
                  <h3 className="text-white font-semibold mb-2">{lyricsResult.track_name}</h3>
                  <div className="text-white/70 text-sm mb-3">{lyricsResult.artist_name}</div>
                  {lyricsResult.album_name && (
                    <div className="text-white/50 text-xs mb-3">{lyricsResult.album_name}</div>
                  )}
                  <div className="text-white text-sm whitespace-pre-wrap max-h-60 overflow-y-auto bg-white/5 p-3 rounded">
                    {lyricsResult.lyrics_body}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Get Track by URL */}
          <div className="bg-white/10 backdrop-blur-lg rounded-lg p-6">
            <h2 className="text-2xl font-semibold text-white mb-4">Get Track by URL</h2>
            <div className="space-y-4">
              <input
                type="text"
                placeholder="MusixMatch lyrics URL"
                value={lyricsUrl}
                onChange={(e) => setLyricsUrl(e.target.value)}
                className="w-full px-4 py-2 bg-white/20 border border-white/30 rounded-lg text-white placeholder-white/70 focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
              <button
                onClick={handleGetTrackByUrl}
                disabled={urlLoading}
                className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-800 text-white rounded-lg transition-colors"
              >
                {urlLoading ? "Getting Track..." : "Get Track"}
              </button>
              
              {urlError && (
                <div className="text-red-400 text-sm bg-red-900/20 p-3 rounded-lg">
                  {urlError}
                </div>
              )}

              {urlResult && (
                <div className="bg-white/10 p-4 rounded-lg">
                  <h3 className="text-white font-semibold mb-2">{urlResult.track_name}</h3>
                  <div className="text-white/70 text-sm mb-3">{urlResult.artist_name}</div>
                  {urlResult.album_name && (
                    <div className="text-white/50 text-xs mb-3">{urlResult.album_name}</div>
                  )}
                  <div className="text-white text-sm whitespace-pre-wrap max-h-60 overflow-y-auto bg-white/5 p-3 rounded">
                    {urlResult.lyrics_body}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="mt-8 bg-white/10 backdrop-blur-lg rounded-lg p-6">
          <h2 className="text-2xl font-semibold text-white mb-4">How to Use</h2>
          <div className="text-white/80 space-y-2">
            <p><strong>Get Lyrics:</strong> Get lyrics by providing artist name and track name</p>
            <p><strong>Get Track by URL:</strong> Get track info and lyrics from a direct MusixMatch lyrics URL</p>
            <p className="text-yellow-400 mt-4">
              <strong>Note:</strong> The scraper works best with specific artist/track names or direct MusixMatch lyrics URLs.
            </p>
            <p className="text-blue-400 mt-2">
              <strong>Example URLs:</strong>
            </p>
            <ul className="text-sm text-blue-300 ml-4 space-y-1">
              <li>• https://www.musixmatch.com/lyrics/Pinegrove/Flora</li>
              <li>• https://www.musixmatch.com/lyrics/The-Beatles/Hey-Jude</li>
              <li>• https://www.musixmatch.com/lyrics/Queen/Bohemian-Rhapsody</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
} 