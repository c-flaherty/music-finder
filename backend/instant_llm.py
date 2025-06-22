import json
import os
import requests
import urllib.parse
from typing import Optional, Tuple, Dict, Any
from dataclasses import asdict

# Add the search_library directory to Python path
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
search_lib_dir = os.path.join(backend_dir, 'search_library')
sys.path.insert(0, backend_dir)

from search_library.types import Song as SearchSong
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env.local'))
from utils import get_lyrics
from search_library.clients import get_client, TextPrompt

def is_lyric_heavy_query_simple(query: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Use LLM to determine if a query is lyric-heavy and extract the actual lyrics to search for.
    
    Args:
        query: The user's search query
        
    Returns:
        Tuple of (is_lyric_heavy, extracted_lyrics, token_usage)
    """
    llm_client = get_client("openai-direct", model_name="gpt-4o-mini")
    
    prompt = f"""You are analyzing a music search query to determine if it's "lyric-heavy" and extract the actual lyrics to search for.

A "lyric-heavy" query typically contains:
- Direct lyrics or partial lyrics from a song
- Phrases that sound like song lyrics
- Specific memorable lines from songs
- Lyrics with some context words

Examples of lyric-heavy queries:
- "that song that goes 'i insist it wasn't always' with the beats" → lyrics: "i insist it wasn't always"
- "song with lyrics 'hello darkness my old friend'" → lyrics: "hello darkness my old friend"
- "what's that song that says 'we will we will rock you'" → lyrics: "we will we will rock you"
- "the one that goes 'imagine all the people'" → lyrics: "imagine all the people"

Examples of NOT lyric-heavy queries:
- "sad songs about breakups"
- "upbeat dance music"
- "songs like Taylor Swift"
- "rock music from the 80s"

Query: "{query}"

If this is a lyric-heavy query, respond with: "YES|extracted_lyrics"
If this is NOT a lyric-heavy query, respond with: "NO"

For example:
- "YES|hello darkness my old friend"
- "YES|we will we will rock you"
- "NO"

Be conservative - only say YES if you're confident the query contains actual song lyrics."""

    try:
        response_tuple = llm_client.generate(
            [[TextPrompt(text=prompt)]],
            max_tokens=50
        )
        response_blocks = response_tuple[0]
        first_block = response_blocks[0]
        response_text = first_block.text.strip()
        
        # Extract token usage from metadata
        token_usage = response_tuple[1] if len(response_tuple) > 1 else {}
        
        if response_text.startswith("YES|"):
            # Extract the lyrics part
            extracted_lyrics = response_text[4:].strip()
            print(f"[INSTANT] Query '{query}' classified as lyric-heavy. Extracted lyrics: '{extracted_lyrics}'")
            return True, extracted_lyrics, token_usage
        else:
            print(f"[INSTANT] Query '{query}' classified as NOT lyric-heavy")
            return False, "", token_usage
        
    except Exception as e:
        print(f"[INSTANT] Error classifying query: {e}")
        return False, "", {}

def llm_lyrics_match(query: str, lyrics: str) -> bool:
    """
    Use LLM to check if the lyrics are a strong match for the query.
    Returns True if LLM says YES, else False.
    """
    llm_client = get_client("openai-direct", model_name="gpt-4o-mini")
    prompt = f"""You are a music search assistant. The user is searching for a song using the following query:

User Query: "{query}"

Here are the lyrics of a candidate song:
---
{lyrics[:1200]}
---

Does the user's query (which may be a lyric fragment) appear in these lyrics, or is it a very close match? Respond with ONLY "YES" if the lyrics contain or closely match the query, or "NO" if not. Be strict: only say YES if the lyrics clearly match the query."""
    try:
        response_tuple = llm_client.generate(
            [[TextPrompt(text=prompt)]],
            max_tokens=10
        )
        response_blocks = response_tuple[0]
        first_block = response_blocks[0]
        response_text = first_block.text.strip().upper()
        print(f"[INSTANT][LLM] LLM response: {response_text}")
        return response_text == "YES"
    except Exception as e:
        print(f"[INSTANT][LLM] Error in LLM lyrics match: {e}")
        return False

def search_genius_for_lyrics(extracted_lyrics: str) -> Optional[Dict[str, Any]]:
    """
    Search Genius API for songs matching the extracted lyrics.
    
    Args:
        extracted_lyrics: The extracted lyrics to search for
        
    Returns:
        Dictionary with song information if found, None otherwise
    """
    headers = {
        'accept': '*/*',
        'content-type': 'application/json',
        'x-genius-ios-version': '7.7.0',
        'x-genius-logged-out': 'true',
        'accept-language': 'en-US,en;q=0.9',
        'user-agent': 'Genius/1267 CFNetwork/3826.500.131 Darwin/24.5.0'
    }
    
    genius_token = os.getenv('GENIUS_ACCESS_TOKEN')
    if genius_token:
        headers['Authorization'] = f"Bearer {genius_token}"

    # Handle proxy settings (same as in utils.py)
    proxies = None
    verify_ssl = True
    use_proxy = False
    isp_username = os.getenv('BD_ISP_USERNAME')
    isp_password = os.getenv('BD_ISP_PASSWORD')
    
    if isp_username and isp_password:
        proxy_url = f'http://{isp_username}:{isp_password}@brd.superproxy.io:33335'
        proxies = {'http': proxy_url, 'https': proxy_url}
        verify_ssl = False
        use_proxy = True

    # Try multiple search strategies to get better results
    search_attempts = []
    
    # Strategy 1: Use the exact extracted lyrics
    search_attempts.append(extracted_lyrics)
    
    # Strategy 2: Add "song" to make it more specific
    search_attempts.append(f"{extracted_lyrics} song")
    
    # Strategy 3: Add "original" to try to find original versions
    search_attempts.append(f"{extracted_lyrics} original")
    
    # Try each search strategy
    best_result = None
    best_score = 0
    
    for attempt in search_attempts:
        # URL encode the query
        encoded_query = urllib.parse.quote(attempt)
        search_url = f"https://api.genius.com/search?q={encoded_query}"
        
        print(f"[INSTANT] Searching Genius for: '{attempt}'")
        
        try:
            search_response = requests.get(search_url, headers=headers, proxies=proxies, verify=verify_ssl, timeout=10)
            print(f"[INSTANT] Genius search response status: {search_response.status_code}")
        except Exception as proxy_error:
            print(f"[INSTANT] Proxy request failed: {proxy_error}")
            if use_proxy:
                search_response = requests.get(search_url, headers=headers, timeout=10)
            else:
                continue
                
        if not search_response.ok:
            print(f"[INSTANT] Genius search request failed. Status: {search_response.status_code}")
            continue
            
        try:
            search_data = search_response.json()
        except json.JSONDecodeError:
            print(f"[INSTANT] Genius search returned non-JSON")
            continue
            
        hits = search_data.get('response', {}).get('hits', [])
        if not hits:
            print(f"[INSTANT] No search results found for query: {attempt}")
            continue
            
        # Try up to 3 candidates for each search attempt
        for hit in hits[:3]:
            top_result = hit.get('result', {})
            if not top_result:
                continue
            
            result = {
                'id': str(top_result.get('id', '')),
                'name': top_result.get('title', ''),
                'artists': [artist.get('name', '') for artist in top_result.get('primary_artist', {}).get('artists', [top_result.get('primary_artist', {})])],
                'album': top_result.get('album', {}).get('name', '') if top_result.get('album') else '',
                'song_link': top_result.get('url', ''),
                'genius_url': top_result.get('url', ''),
                'lyrics_state': top_result.get('lyrics_state', ''),
                'full_title': top_result.get('full_title', ''),
                'search_score': hit.get('highlights', []),
                'result_type': top_result.get('result_type', ''),
                'search_query_used': attempt
            }
            
            # Fetch lyrics for this candidate
            lyrics = get_lyrics(result['name'], result['artists'])
            if not lyrics:
                print(f"[INSTANT] No lyrics found for {result['name']} by {', '.join(result['artists'])}")
                continue
            
            # Use LLM to check if lyrics match the query
            if llm_lyrics_match(extracted_lyrics, lyrics):
                print(f"[INSTANT] LLM says lyrics match for {result['name']} by {', '.join(result['artists'])}")
                print(f"[INSTANT] Lyrics preview: {lyrics[:200]}...")
                result['lyrics'] = lyrics
                return result
            else:
                print(f"[INSTANT] LLM says lyrics do NOT match for {result['name']} by {', '.join(result['artists'])}")
                print(f"[INSTANT] Lyrics preview: {lyrics[:200]}...")
    
    print(f"[INSTANT] No excellent results found after trying all search strategies and checking lyrics with LLM")
    return None

def convert_genius_result_to_search_song(genius_result: Dict[str, Any]) -> SearchSong:
    """
    Convert a Genius API result to a SearchSong object.
    
    Args:
        genius_result: The result from Genius search
        
    Returns:
        SearchSong object
    """
    # Create a unique ID for the song
    song_id = f"genius-{genius_result.get('id', 'unknown')}"
    
    # Get the primary artist name
    artists = genius_result.get('artists', [])
    if not artists and genius_result.get('full_title'):
        # Try to extract artist from full_title (format is usually "Artist - Song")
        full_title = genius_result.get('full_title', '')
        if ' – ' in full_title:
            artist_part = full_title.split(' – ')[0]
            artists = [artist_part]
    
    return SearchSong(
        id=song_id,
        name=genius_result.get('name', ''),
        artists=artists,
        album=genius_result.get('album', ''),
        song_link=genius_result.get('genius_url', ''),  # Use Genius URL as song link
        lyrics=genius_result.get('lyrics', ''),  # Now include lyrics if available
        song_metadata=f"Found via instant Genius search. Original query matched this song.",
        reasoning=f"Instant match found via Genius search for query containing lyrics."
    )

def instant_search(query: str) -> Tuple[Optional[SearchSong], Dict[str, Any]]:
    """
    Perform instant search for lyric-heavy queries using LLM classification and lyrics verification.
    
    Args:
        query: The user's search query
        
    Returns:
        Tuple of (SearchSong if found, token_usage)
    """
    print(f"[INSTANT] Starting simple instant search for query: {query}")
    
    # Initialize token usage tracking
    combined_token_usage = {
        'total_input_tokens': 0,
        'total_output_tokens': 0,
        'total_requests': 0
    }
    
    # Step 1: Determine if query is lyric-heavy using LLM
    is_lyric_heavy, extracted_lyrics, classification_tokens = is_lyric_heavy_query_simple(query)
    combined_token_usage['total_input_tokens'] += classification_tokens.get('input_tokens', 0)
    combined_token_usage['total_output_tokens'] += classification_tokens.get('output_tokens', 0)
    combined_token_usage['total_requests'] += 1
    
    print(f"[INSTANT] Query '{query}' classified as lyric-heavy: {is_lyric_heavy}")
    
    if not is_lyric_heavy:
        print(f"[INSTANT] Query not classified as lyric-heavy, skipping instant search")
        return None, combined_token_usage
    
    # Step 2: Search Genius with extracted lyrics
    genius_result = search_genius_for_lyrics(extracted_lyrics)
    if not genius_result:
        print(f"[INSTANT] No Genius results found")
        return None, combined_token_usage
    
    # Step 3: Convert to SearchSong and return (no need for additional heuristic check since LLM already verified lyrics)
    search_song = convert_genius_result_to_search_song(genius_result)
    print(f"[INSTANT] Found excellent match: {search_song.name} by {', '.join(search_song.artists)}")
    
    return search_song, combined_token_usage 