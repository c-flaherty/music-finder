import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <div className="space-y-4">
        <Link 
          href="/library"
          className="block px-6 py-3 bg-black text-white rounded-full hover:bg-gray-800 transition-colors text-center"
        >
          View My Library
        </Link>
        <Link 
          href="/playlist"
          className="block px-6 py-3 bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors text-center"
        >
          Go to Playlist
        </Link>
      </div>
    </div>
  );
}
