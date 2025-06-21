import Image from "next/image";

export function Header() {
  return (
    <header className="w-full max-w-2xl mx-auto flex flex-col items-center mb-8 md:mb-12">
      <h1 className="font-roobert text-4xl md:text-5xl lg:text-6xl font-[800] text-[#F6A23B] text-center mb-3 md:mb-4 tracking-tight leading-tight">
        Remember that song
        <span className="flex items-center justify-center w-full mt-1 gap-2" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          with <span className="text-[#502D07] ml-2">Cannoli</span>
          <Image src="/logos/cannoli.png" alt="Cannoli logo" width={64} height={64} className="drop-shadow-sm ml-2 align-middle" />
        </span>
      </h1>
    </header>
  );
} 