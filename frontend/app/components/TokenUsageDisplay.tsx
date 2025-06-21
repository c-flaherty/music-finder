"use client";
import { useState } from "react";
import { TokenUsage } from "../types";

interface TokenUsageDisplayProps {
  tokenUsage: TokenUsage;
}

// Token Usage Display Component
export const TokenUsageDisplay = ({ tokenUsage }: { tokenUsage: TokenUsage }) => {
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
              {tokenUsage.requests_breakdown.map((request: any, index: number) => (
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