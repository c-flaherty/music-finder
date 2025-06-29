import Image from "next/image";

interface CompressedHeaderProps {
  search: string;
  setSearch: (search: string) => void;
  isSearching: boolean;
  isAuthenticated: boolean;
  onSubmit: (e: React.FormEvent) => void;
  placeholderTexts: string[];
}

export function CompressedHeader({ 
  search, 
  setSearch, 
  isSearching, 
  isAuthenticated, 
  onSubmit,
  placeholderTexts 
}: CompressedHeaderProps) {
  return (
    <header className="sticky top-0 bg-[#FFF5D1] z-50 w-full border-b border-[#DDCDA8] py-4 px-4 mb-6">
      <div className="max-w-4xl mx-auto flex items-center gap-4">
        {/* Cannoli Brand */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <Image 
            src="/logos/cannoli.png" 
            alt="Cannoli logo" 
            width={32} 
            height={32} 
            className="drop-shadow-sm" 
          />
          <span className="text-[#502D07] font-roobert font-[800] text-xl">
            Cannoli
          </span>
        </div>
        
        {/* Compressed Search Bar */}
        <form onSubmit={onSubmit} className="flex-1 max-w-2xl">
          <div className="flex items-center bg-white border border-[#DDCDA8] rounded-full shadow-sm px-4 py-2 focus-within:ring-2 focus-within:ring-[#F6A23B] transition-all">
            <input
              type="text"
              className="flex-1 bg-transparent outline-none text-base text-[#502D07] placeholder-[#838D5A] font-roobert"
              placeholder="Search for songs..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              disabled={isSearching}
            />
            <button
              type="submit"
              className={`ml-2 px-4 py-1 rounded-full font-semibold text-sm transition-colors font-roobert ${
                !search.trim() 
                  ? 'bg-gray-400 text-white cursor-not-allowed' 
                  : 'bg-[#F6A23B] text-white hover:bg-[#D18A32] active:bg-[#D18A32] cursor-pointer'
              }`}
              disabled={!search.trim() || isSearching}
            >
              {isSearching ? 'Searching...' : 'Search'}
            </button>
          </div>
        </form>
      </div>
    </header>
  );
} 