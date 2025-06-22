export interface SearchResult {
    id: string;
    name: string;
    artists: string[];
    song_link: string;
    reasoning: string;
    lyrics: string;
    image_url?: string;
  }

export interface RequestBreakdown {
  chunk_size: number;
  input_tokens: number;
  output_tokens: number;
  final_reduction?: boolean;
}
  
export interface TokenUsage {
    total_input_tokens: number;
    total_output_tokens: number;
    total_requests: number;
    requests_breakdown: Array<RequestBreakdown>;
    enrichment_requests?: number;
    search_requests?: number;
    enrichment_input_tokens?: number;
    enrichment_output_tokens?: number;
    search_input_tokens?: number;
    search_output_tokens?: number;
}