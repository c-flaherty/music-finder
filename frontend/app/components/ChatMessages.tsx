import { chatMessages } from '../constants';
import { SearchResult } from '../types';

interface ChatMessagesProps {
  searchResults: SearchResult[];
  isSearching: boolean;
  showProgress: boolean;
}

export function ChatMessages({ searchResults, isSearching, showProgress }: ChatMessagesProps) {
  // Only show when there are no search results and not searching
  if (searchResults.length > 0 || isSearching || showProgress) {
    return null;
  }

  return (
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
  );
}
