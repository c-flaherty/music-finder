'use client';

import { useState } from 'react';

export default function TestLyricsPage() {
  const [songId, setSongId] = useState('5924383'); // Default to "half return"
  const [lyrics, setLyrics] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [fullResponse, setFullResponse] = useState('');

  const handleFetchLyrics = async () => {
    setIsLoading(true);
    setError('');
    setLyrics('');
    setFullResponse('');

    try {
      const response = await fetch(`/api/test-lyrics?songId=${songId}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status} ${await response.text()}`);
      }
      const data = await response.json();

      if (data.success) {
        setLyrics(data.lyrics);
      } else {
        setError(data.message || 'Failed to fetch lyrics.');
        setFullResponse(JSON.stringify(data.data, null, 2));
      }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (e: any) {
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif', maxWidth: '800px', margin: 'auto' }}>
      <h1>Test Genius Lyrics with Node.js `curl`</h1>
      <p>This page tests fetching lyrics by executing the exact curl command via a Node.js child process on the server.</p>
      <div style={{ margin: '20px 0' }}>
        <label htmlFor="songId" style={{ marginRight: '10px' }}>Song ID:</label>
        <input
          id="songId"
          type="text"
          value={songId}
          onChange={(e) => setSongId(e.target.value)}
          style={{ padding: '8px', width: '250px', fontSize: '16px' }}
        />
      </div>
      <button onClick={handleFetchLyrics} disabled={isLoading} style={{ padding: '10px 20px', cursor: 'pointer', fontSize: '16px' }}>
        {isLoading ? 'Loading...' : 'Fetch Lyrics via Server Curl'}
      </button>

      {error && (
        <div style={{ marginTop: '20px', color: 'red' }}>
          <h2>Error</h2>
          <pre style={{ backgroundColor: '#ffeeee', padding: '10px', whiteSpace: 'pre-wrap', wordBreak: 'break-all', border: '1px solid red' }}>
            {error}
          </pre>
          {fullResponse && (
            <>
              <h3>Full API Response:</h3>
              <pre style={{ backgroundColor: '#f0f0f0', padding: '10px', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                {fullResponse}
              </pre>
            </>
          )}
        </div>
      )}

      {lyrics && (
        <div style={{ marginTop: '20px' }}>
          <h2>Lyrics Fetched Successfully!</h2>
          <pre style={{ backgroundColor: '#e6ffed', padding: '10px', whiteSpace: 'pre-wrap', border: '1px solid green' }}>
            {lyrics}
          </pre>
        </div>
      )}
    </div>
  );
} 