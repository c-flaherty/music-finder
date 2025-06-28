import { useState, useEffect, useRef, useCallback } from "react";
import { SearchResult, TokenUsage } from '../types';
import { useAuth } from './useAuth';

export function useSearch() {
  const { getValidToken, handleUnauthorized, isAuthenticated, shouldAutoSearch, setShouldAutoSearch } = useAuth();
  const [search, setSearchState] = useState("");
  
  // Custom setSearch function that updates both state and URL
  const setSearch = (newSearch: string) => {
    setSearchState(newSearch);
    
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      if (newSearch.trim()) {
        url.searchParams.set('q', newSearch);
      } else {
        url.searchParams.delete('q');
      }
      window.history.replaceState({}, '', url.toString());
    }
  };

  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [tokenUsage, setTokenUsage] = useState<TokenUsage | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [stage, setStage] = useState<"enrichment" | "searching">("enrichment");
  const [animatedProgress, setAnimatedProgress] = useState(0);
  const [showProgress, setShowProgress] = useState(false);
  const animationRef = useRef<number | null>(null);
  const lastFrameTimeRef = useRef<number>(0);
  const [message, setMessage] = useState("");
  const [displayMessage, setDisplayMessage] = useState("");
  const [messageAnimating, setMessageAnimating] = useState(false);
  const readerRef = useRef<ReadableStreamDefaultReader | null>(null);

  // Progress tracking variables for smooth animation
  const [totalEvents, setTotalEvents] = useState(0);
  const [completedEvents, setCompletedEvents] = useState(0);
  const [lastFinishTime, setLastFinishTime] = useState<number | null>(null);
  const [avgDelta, setAvgDelta] = useState(1000); // Start with 1 second guess (in ms)
  const currentAnimatedProgressRef = useRef(0); // Track current animated progress locally
  const [showLargeBatchAlert, setShowLargeBatchAlert] = useState(false);

  // Initialize search from URL params
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const q = params.get('q');
      
      if (q) setSearchState(q);
    }
  }, []);

  // Store a ref to track if auto-search should be triggered
  const autoSearchTriggeredRef = useRef(false);

  // Message animation effect
  useEffect(() => {
    if (!message) {
      setDisplayMessage("");
      return;
    }

    if (displayMessage && message !== displayMessage) {
      // Message changed, fade out old message then fade in new one
      setMessageAnimating(true);
      setTimeout(() => {
        setDisplayMessage(message);
        setMessageAnimating(false);
      }, 200); // Duration matches fade out animation
    } else {
      // First time or same message
      setDisplayMessage(message);
    }
  }, [message, displayMessage]); // Include displayMessage to fix dependency warning

  // Smooth progress animation using predictive smoothing
  useEffect(() => {
    if (!totalEvents || totalEvents === 0) {
      setAnimatedProgress(0);
      return;
    }

    // Clear any existing animation at the start of new search
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }

    const animate = (currentTime: number) => {
      // Limit to ~60fps for smoother animation (16ms = ~60fps)
      if (currentTime - lastFrameTimeRef.current < 16) {
        animationRef.current = requestAnimationFrame(animate);
        return;
      }
      lastFrameTimeRef.current = currentTime;
      
      const now = Date.now();
      
      // If we haven't started receiving updates yet, just show 0
      if (!lastFinishTime) {
        setAnimatedProgress(0);
        animationRef.current = requestAnimationFrame(animate);
        return;
      }
      
      const elapsed = now - lastFinishTime;
      const extra = elapsed / avgDelta; // How many "typical" items based on recent average
      const pseudoDone = Math.min(completedEvents + extra, totalEvents); // Never overshoot
      let newTargetProgress = pseudoDone / totalEvents;
      
      // "Catch up" animation when close to completion
      const completionRatio = completedEvents / totalEvents;
      const isCatchingUp = completionRatio >= 0.8;
      
      if (isCatchingUp) {
        // When 80%+ complete, jump target to 100% for catch-up animation
        newTargetProgress = 1.0;
      }
      
      // Smooth interpolation towards target progress (easing)
      const currentProgress = currentAnimatedProgressRef.current; // Use ref for immediate updates
      const progressDiff = newTargetProgress - currentProgress;
      // Use faster animation speed during catch-up
      const smoothingFactor = 0.1;
      const smoothedProgress = currentProgress + (progressDiff * smoothingFactor);
      
      // Update ref immediately for next animation frame
      currentAnimatedProgressRef.current = smoothedProgress;
      
      setAnimatedProgress(smoothedProgress); // animatedProgress gets the smooth interpolation
      
      // Stop animation if all events are truly completed
      if (completedEvents < totalEvents) {
        animationRef.current = requestAnimationFrame(animate);
      } else {
        // All done - force to 100%
        currentAnimatedProgressRef.current = 1.0;
        setAnimatedProgress(1.0);
        animationRef.current = null;
      }
    };

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
    };
  }, [totalEvents, completedEvents, lastFinishTime, avgDelta]);

  const handleSearch = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!search.trim()) return;

    // Reset auto-search ref when starting any search (manual or auto)
    autoSearchTriggeredRef.current = false;
    setIsSearching(true);
    setShowProgress(false);
    setAnimatedProgress(0);
    
    // Initialize smooth progress tracking
    setTotalEvents(0);
    setCompletedEvents(0);
    setLastFinishTime(null);
    setAvgDelta(1000); // Reset to 1 second guess
    currentAnimatedProgressRef.current = 0; // Reset ref
    setShowLargeBatchAlert(false); // Reset alert
    
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }
    setSearchResults([]);
    setMessage("Fetching Cannoli...");

    try {
      // Get valid token (with refresh if needed)
      const token = await getValidToken(search.trim());
      
      if (!token) {
        return; // getValidToken handles redirects
      }

      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8001';
      const fetchUrl = `${backendUrl}/api/spotify_search?query=${encodeURIComponent(search)}`;

      try {
        const refreshToken = localStorage.getItem('spotify_refresh_token');
        const response = await fetch(fetchUrl, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Refresh-Token': refreshToken || '',
          },
        });

        if (!response.ok) {
          if (response.status === 401) {
            // Token invalid
            handleUnauthorized(search.trim());
            return;
          }
          throw new Error('Search failed');
        }

        // Handle streaming response
        if (!response.body) {
          throw new Error('No response body');
        }

        const reader = response.body.getReader();
        readerRef.current = reader;
        const decoder = new TextDecoder();
        let buffer = '';

        try {
          while (true) {
            const { done, value } = await reader.read();

            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Process complete SSE messages
            const messages = buffer.split('\n\n');
            buffer = messages.pop() || ''; // Keep incomplete message in buffer

            for (const message of messages) {
              if (message.startsWith('data: ')) {
                try {
                  const data = JSON.parse(message.slice(6)); // Remove 'data: ' prefix

                  if (data.type === 'progress') {
                    const now = Date.now();
                    const newCompleted = data.processed;
                    const newTotal = data.total;
                    
                    // Initialize total events on first progress update - use functional update to get current state
                    setTotalEvents(prevTotalEvents => {
                      if (prevTotalEvents === 0 && newTotal > 0) {
                        setLastFinishTime(now);
                        // Initial guess: assume 1 item per second
                        const initialAvgDelta = Math.max(1000, (newTotal * 1000) / 60); // At least 1s, max 1 min per item
                        setAvgDelta(initialAvgDelta);
                        
                        // Show large batch alert if more than 250 songs
                        if (newTotal > 250) {
                          setShowLargeBatchAlert(true);
                        }
                        
                        return newTotal; // Add 10% buffer so progress never exceeds 90%
                      }
                      return prevTotalEvents;
                    });
                    
                    // Update exponentially-smoothed average when events actually complete
                    setCompletedEvents(prevCompletedEvents => {
                      if (newCompleted > prevCompletedEvents) {
                        setLastFinishTime(prevLastFinishTime => {
                          if (prevLastFinishTime && prevCompletedEvents > 0) {
                            const delta = now - prevLastFinishTime;
                            const alpha = 0.2; // Tuning parameter for smoothing
                            setAvgDelta(prevAvgDelta => alpha * delta + (1 - alpha) * prevAvgDelta);
                          }
                          return now;
                        });
                        return newCompleted;
                      }
                      return prevCompletedEvents;
                    });
                    
                    if (data.message) {
                      setMessage(data.message);
                    }
                    setShowProgress(true);
                  } else if (data.type === 'start') {
                    // Explicit reset of all progress state for new search
                    setAnimatedProgress(0);
                    setTotalEvents(0);
                    setCompletedEvents(0);
                    setLastFinishTime(null);
                    setAvgDelta(1000);
                    setShowProgress(false);
                    setSearchResults([]);
                    setTokenUsage(null);
                    setStage("enrichment");
                    
                    if (data.message) {
                      setMessage(data.message);
                    }
                  } else if (data.type === 'results') {
                    setTokenUsage(data.token_usage || null);
                    
                    // Deduplicate results by ID to avoid React key conflicts
                    const results = data.results || [];
                    const uniqueResults = results.filter((song: SearchResult, index: number, self: SearchResult[]) => 
                      index === self.findIndex(s => s.id === song.id)
                    );

                    setSearchResults(uniqueResults);
                    
                    // Mark all events as completed to trigger final animation
                    setCompletedEvents(totalEvents || data.results?.length || 0);
                    setAnimatedProgress(1.0); // Complete the progress bar
                    setShowProgress(false);
                  } else if (data.type === 'completion') {
                    if (data.prev_stage === 'enrichment') {
                      setStage("searching");
                    }
                  } else if (data.type === 'error') {
                    console.error('Error:', data);
                    throw new Error(data.error);
                  }
                  else if (data.type === 'status') {
                    console.log('Status:', data);
                  }
                } catch (parseError) {
                  console.error('Error parsing SSE message:', parseError);
                }
              }
            }
          }
        } finally {
          reader.releaseLock();
          readerRef.current = null;
        }

      } catch (fetchError) {
        console.error('Fetch error caught:', fetchError);
        throw fetchError;
      }

    } catch (error) {
      console.error('Search error:', error);
      setShowProgress(false);
    } finally {
      setIsSearching(false);
      // Clean up animation when search is done
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
    }
  }, [search, getValidToken, handleUnauthorized, totalEvents]);

  // Store the handleSearch function in a ref to avoid dependency issues
  const handleSearchRef = useRef<((e: React.FormEvent) => void) | null>(null);
  
  // Update the ref whenever handleSearch changes
  useEffect(() => {
    handleSearchRef.current = handleSearch;
  }, [handleSearch]);
  
  // Auto-search effect when shouldAutoSearch is true and user is authenticated
  useEffect(() => {    
    const pendingAutoSearch = localStorage.getItem('pending_auto_search') === 'true';
    
    if ((shouldAutoSearch || pendingAutoSearch) && isAuthenticated && search.trim() && !isSearching && !autoSearchTriggeredRef.current) {
      autoSearchTriggeredRef.current = true; // Prevent multiple triggers
      setShouldAutoSearch(false); // Reset the flag
      localStorage.removeItem('pending_auto_search'); // Clear the backup flag
      
      // Create a synthetic form event and call handleSearch directly
      if (handleSearchRef.current) {
        const syntheticEvent = new Event('submit') as unknown as React.FormEvent;
        Object.defineProperty(syntheticEvent, 'preventDefault', {
          value: () => {},
          writable: false
        });
        
        // Call handleSearch directly with the synthetic event
        handleSearchRef.current(syntheticEvent);
      } else {
        // Defer the auto-search by a short delay
        setTimeout(() => {
          if (handleSearchRef.current) {
            const syntheticEvent = new Event('submit') as unknown as React.FormEvent;
            Object.defineProperty(syntheticEvent, 'preventDefault', {
              value: () => {},
              writable: false
            });
            handleSearchRef.current(syntheticEvent);
          }
        }, 100);
      }
    } else {
      console.log('Conditions not met for auto-search');
    }
  }, [shouldAutoSearch, isAuthenticated, search, isSearching, setShouldAutoSearch]);

  // Cleanup function for component unmount
  useEffect(() => {
    return () => {
      if (readerRef.current) {
        readerRef.current.cancel();
        readerRef.current = null;
      }
    };
  }, []);

  return {
    // State
    search,
    setSearch,
    searchResults,
    tokenUsage,
    isSearching,
    stage,
    animatedProgress,
    showProgress,
    displayMessage,
    messageAnimating,
    showLargeBatchAlert,
    
    // Functions
    handleSearch,
  };
}
