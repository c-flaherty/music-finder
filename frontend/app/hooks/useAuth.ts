import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

export const useAuth = () => {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [shouldAutoSearch, setShouldAutoSearch] = useState(false);

  // Initial auth check on component mount
  useEffect(() => {
    const token = localStorage.getItem('spotify_access_token');
    const refreshToken = localStorage.getItem('spotify_refresh_token');
    const expiresAt = localStorage.getItem('spotify_token_expires_at');

    console.log('Auth state:', {
      hasAccessToken: !!token,
      hasRefreshToken: !!refreshToken,
      expiresAt: expiresAt ? new Date(parseInt(expiresAt)).toISOString() : 'not set',
      isExpired: expiresAt ? Date.now() > parseInt(expiresAt) : true
    });

    setIsAuthenticated(!!token);
    setLoading(false);
  }, []);

  // Handle tokens from URL after Spotify login
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const accessToken = params.get('access_token');
      const refreshToken = params.get('refresh_token');
      const expiresIn = params.get('expires_in');
      const startSearch = params.get('start_search') === 'true';
      const q = params.get('q');

      if (accessToken) {
        // Store tokens first
        localStorage.setItem('spotify_access_token', accessToken);
        if (refreshToken) {
          localStorage.setItem('spotify_refresh_token', refreshToken);
        }
        if (expiresIn) {
          const expiresAt = Date.now() + (parseInt(expiresIn) * 1000);
          localStorage.setItem('spotify_token_expires_at', expiresAt.toString());
        }

        // Call backend to create/update user in database
        const createOrUpdateUser = async () => {
          try {
            const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8001';
            const headers: Record<string, string> = {
              'Authorization': `Bearer ${accessToken}`,
              'Content-Type': 'application/json',
            };
            
            if (refreshToken) {
              headers['refresh-token'] = refreshToken;
            }

            const response = await fetch(`${backendUrl}/api/login-or-create-user`, {
              method: 'POST',
              headers,
            });

            if (!response.ok) {
              console.error('[AUTH] Failed to create/update user:', response.status, response.statusText);
              // Don't block authentication if user creation fails
              // The user can still use the app, just without database tracking
            } else {
              const userData = await response.json();
              console.log('[AUTH] User created/updated successfully:', userData);
            }
          } catch (error) {
            console.error('[AUTH] Error creating/updating user:', error);
            // Don't block authentication if user creation fails
          }
        };

        // Call the user creation function
        createOrUpdateUser();

        // Set authenticated state
        setIsAuthenticated(true);

        // Clean up URL to remove tokens and start_search (but keep q)
        const newUrl = new URL(window.location.href);
        newUrl.searchParams.delete('access_token');
        newUrl.searchParams.delete('refresh_token');
        newUrl.searchParams.delete('expires_in');
        newUrl.searchParams.delete('start_search');
        window.history.replaceState({}, '', newUrl.toString());

        // If start_search is true and we have a search query, trigger search automatically
        if (startSearch && q && q.trim()) {
          console.log('[AUTH] Setting shouldAutoSearch=true for query:', q);
          console.trace('[AUTH] Stack trace for setShouldAutoSearch(true):');
          // Also store in localStorage as a backup
          localStorage.setItem('pending_auto_search', 'true');
          setShouldAutoSearch(true);
        } else {
          console.log('[AUTH] Not setting auto-search. startSearch:', startSearch, 'q:', q);
          localStorage.removeItem('pending_auto_search');
        }
      }
    }
  }, []);

  // Function to get valid token (with refresh if needed)
  const getValidToken = async (searchQuery?: string): Promise<string | null> => {
    const expiresAt = localStorage.getItem('spotify_token_expires_at');
    const refreshToken = localStorage.getItem('spotify_refresh_token');
    let token = localStorage.getItem('spotify_access_token');

    // If no token or expired without refresh token, redirect to login
    if (expiresAt && Date.now() > parseInt(expiresAt) && !refreshToken) {
      router.push('/api/auth/spotify');
      return null;
    }

    // If token is expired but we have refresh token, try to refresh
    if (expiresAt && refreshToken && Date.now() > parseInt(expiresAt)) {
      try {
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8001';
        const response = await fetch(`${backendUrl}/api/spotify_refresh`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (!response.ok) {
          // Clear local auth and redirect to login
          clearAuth();
          router.push(`/api/auth/spotify${searchQuery ? `?q=${encodeURIComponent(searchQuery)}` : ''}`);
          return null;
        }

        const data = await response.json();
        token = data.access_token;
        if (token) {
          localStorage.setItem('spotify_access_token', token);
          if (data.refresh_token) {
            localStorage.setItem('spotify_refresh_token', data.refresh_token);
          }
          localStorage.setItem('spotify_token_expires_at', (Date.now() + (data.expires_in * 1000)).toString());
        } else {
          throw new Error('No access token received from refresh');
        }
      } catch (refreshError) {
        console.error('Error refreshing token:', refreshError);
        router.push('/?error=unauthorized');
        return null;
      }
    }

    // If still no token, redirect to login
    if (!token) {
      clearAuth();
      router.push(`/api/auth/spotify${searchQuery ? `?q=${encodeURIComponent(searchQuery)}` : ''}`);
      return null;
    }

    return token;
  };

  // Function to clear authentication data
  const clearAuth = () => {
    localStorage.removeItem('spotify_access_token');
    localStorage.removeItem('spotify_refresh_token');
    localStorage.removeItem('spotify_token_expires_at');
    setIsAuthenticated(false);
  };

  // Function to handle 401 errors by clearing auth and redirecting
  const handleUnauthorized = (searchQuery?: string) => {
    clearAuth();
    router.push(`/api/auth/spotify${searchQuery ? `?q=${encodeURIComponent(searchQuery)}` : ''}`);
  };

  return {
    isAuthenticated,
    loading,
    shouldAutoSearch,
    setShouldAutoSearch,
    getValidToken,
    clearAuth,
    handleUnauthorized
  };
};
