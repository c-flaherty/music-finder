import Image from "next/image";

interface ProgressSectionProps {
  isSearching: boolean;
  stage: "enrichment" | "searching";
  animatedProgress: number;
  displayMessage: string;
  messageAnimating: boolean;
  showLargeBatchAlert: boolean;
}

export function ProgressSection({
  isSearching,
  stage,
  animatedProgress,
  displayMessage,
  messageAnimating,
  showLargeBatchAlert
}: ProgressSectionProps) {
  if (!isSearching) return null;

  const enrichmentComponent = (
    <>
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
            stroke="#F6A23B"
            strokeWidth="8"
            fill="none"
            strokeLinecap="round"
            strokeDasharray={`${2 * Math.PI * 70}`}
            strokeDashoffset={`${2 * Math.PI * 70 * (1 - animatedProgress)}`}
            style={{
              transition: 'stroke-dashoffset 0.1s ease-out'
            }}
          />
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
        <h3 className={`text-lg font-['Proxima_Nova'] font-extrabold text-[#502D07] mb-2 transition-opacity duration-200 ${messageAnimating ? 'animate-messageOut' : 'opacity-100'}`}>
          {displayMessage}
        </h3>
        
        {/* Large batch alert */}
        {showLargeBatchAlert && (
          <div className="mt-4 p-4 bg-[#FFF5D1] border-2 border-[#F6A23B] rounded-xl animate-fadeIn">
            <p className="text-sm text-[#502D07] font-medium text-center leading-relaxed">
              <span className="text-base">🍃</span> You have a lot of songs Cannoli hasn&apos;t listened to yet. This may take a few minutes! Go watch some reels and come back soon pls.
            </p>
          </div>
        )}
      </div>
    </>
  );

  const searchingComponent = (
    <>
      {/* Invisible Circular Progress with Cannoli for consistent positioning */}
      <div className="relative mb-6">
        <svg
          className="w-48 h-48 md:w-56 md:h-56 transform -rotate-90 opacity-0"
          viewBox="0 0 160 160"
        >
          {/* Invisible background circle */}
          <circle
            cx="80"
            cy="80"
            r="70"
            stroke="#F7F7F7"
            strokeWidth="8"
            fill="none"
          />
        </svg>
        
        {/* Cannoli image with gentle bounce animation */}
        <div className="absolute inset-0 flex items-center justify-center">
          <Image 
            src="/logos/cannoli.png" 
            alt="Cannoli logo" 
            width={144} 
            height={144}
            className="animate-gentle-bounce"
            style={{
              animationDuration: '2s'
            }}
          />
        </div>
      </div>
      
      {/* Searching text */}
      <div className="text-center">
        <h3 className="text-lg font-['Proxima_Nova'] font-extrabold text-[#502D07] mb-2">
          Searching!
        </h3>
      </div>
    </>
  );

  return (
    <section className="w-full max-w-2xl mx-auto mb-6 px-4 animate-fadeIn flex flex-col items-center">
      {stage === "enrichment" ? enrichmentComponent : searchingComponent}
    </section>
  );
}
