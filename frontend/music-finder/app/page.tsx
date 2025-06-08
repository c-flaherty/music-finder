import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <Link 
        href="/playlist"
        className="px-6 py-3 bg-black text-white rounded-full hover:bg-gray-800 transition-colors"
      >
        Go to Playlist
      </Link>
    </div>
  );
}
