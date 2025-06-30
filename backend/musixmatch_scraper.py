import requests
import json
import re
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import quote, urljoin

class MusixMatchScraper:
    def __init__(self):
        self.base_url = "https://www.musixmatch.com"
        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.9',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def search_tracks(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for tracks by query string
        Returns a list of track information
        """
        try:
            # Search URL format
            search_url = f"{self.base_url}/search/{quote(query)}"
            
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find the script tag with the search results
            script_tag = soup.find("script", {"id": "__NEXT_DATA__"})
            
            if not script_tag:
                return []
            
            json_data = json.loads(script_tag.string)
            
            # Navigate through the JSON to find search results
            try:
                page_props = json_data.get('props', {}).get('pageProps', {})
                search_results = page_props.get('data', {}).get('searchGet', {}).get('data', {}).get('tracks', [])
                
                tracks = []
                for track in search_results[:limit]:
                    track_info = {
                        'track_id': track.get('id'),
                        'track_name': track.get('name'),
                        'artist_name': track.get('artistName'),
                        'album_name': track.get('albumName'),
                        'spotify_id': track.get('spotifyId'),
                        'release_date': track.get('releaseDate'),
                        'lyrics_url': f"{self.base_url}/lyrics/{track.get('artistName', '').replace(' ', '-')}/{track.get('name', '').replace(' ', '-')}" if track.get('artistName') and track.get('name') else None
                    }
                    tracks.append(track_info)
                
                return tracks
                
            except KeyError as e:
                print(f"Could not find search results in JSON: {e}")
                return []
                
        except Exception as e:
            print(f"Error searching tracks: {e}")
            return []

    def get_track_lyrics(self, artist_name: str, track_name: str) -> Optional[Dict[str, Any]]:
        """
        Get lyrics for a specific track by artist and track name
        """
        # Try multiple URL variations
        url_variations = self._generate_url_variations(artist_name, track_name)
        
        print(f"Trying {len(url_variations)} URL variations for '{track_name}' by '{artist_name}'")
        
        for i, lyrics_url in enumerate(url_variations, 1):
            try:
                print(f"  [{i}/{len(url_variations)}] Trying: {lyrics_url}")
                result = self._get_track_from_url(lyrics_url)
                if result:
                    print(f"  ✓ Success! Found lyrics at: {lyrics_url}")
                    return result
            except Exception as e:
                print(f"  ✗ Failed: {e}")
                continue
        
        print(f"  ✗ All {len(url_variations)} variations failed")
        return None

    def _generate_url_variations(self, artist_name: str, track_name: str) -> List[str]:
        """
        Generate multiple URL variations to try when the standard format doesn't work
        """
        variations = []
        
        # Clean and normalize names
        artist_clean = self._normalize_name(artist_name)
        track_clean = self._normalize_name(track_name)
        
        # Standard format
        variations.append(f"{self.base_url}/lyrics/{artist_clean}/{track_clean}")
        
        # Try with numbers appended to artist (common pattern)
        for i in range(1, 10):
            variations.append(f"{self.base_url}/lyrics/{artist_clean}-{i}/{track_clean}")
        
        # Try different casing variations
        variations.append(f"{self.base_url}/lyrics/{artist_clean.lower()}/{track_clean.lower()}")
        variations.append(f"{self.base_url}/lyrics/{artist_clean.title()}/{track_clean.title()}")
        
        # Try with different apostrophe handling
        if "'" in track_name or "'" in artist_name:
            # Original with apostrophes
            artist_apostrophe = artist_name.replace("'", "'").replace("'", "'")
            track_apostrophe = track_name.replace("'", "'").replace("'", "'")
            artist_apostrophe_clean = self._normalize_name(artist_apostrophe)
            track_apostrophe_clean = self._normalize_name(track_apostrophe)
            variations.append(f"{self.base_url}/lyrics/{artist_apostrophe_clean}/{track_apostrophe_clean}")
            
            # With numbers for apostrophe versions too
            for i in range(1, 5):
                variations.append(f"{self.base_url}/lyrics/{artist_apostrophe_clean}-{i}/{track_apostrophe_clean}")
        
        # Try removing common words that might be omitted
        track_words = track_clean.split('-')
        if len(track_words) > 1:
            # Try without first word
            variations.append(f"{self.base_url}/lyrics/{artist_clean}/{'-'.join(track_words[1:])}")
            # Try without last word
            variations.append(f"{self.base_url}/lyrics/{artist_clean}/{'-'.join(track_words[:-1])}")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for url in variations:
            if url not in seen:
                seen.add(url)
                unique_variations.append(url)
        
        return unique_variations

    def _normalize_name(self, name: str) -> str:
        """
        Normalize a name for URL generation
        """
        # Replace apostrophes and quotes with hyphens
        normalized = name.replace("'", "-").replace("'", "-").replace('"', "-").replace('"', "-")
        
        # Replace other special characters
        normalized = normalized.replace("&", "and")
        normalized = normalized.replace("+", "and")
        
        # Replace spaces and other separators with hyphens
        normalized = re.sub(r'[^\w\s-]', '', normalized)
        normalized = re.sub(r'[-\s]+', '-', normalized)
        
        # Remove leading/trailing hyphens
        normalized = normalized.strip('-')
        
        return normalized

    def _get_track_from_url(self, lyrics_url: str) -> Optional[Dict[str, Any]]:
        """
        Get track information from a specific URL
        """
        try:
            response = self.session.get(lyrics_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find the script tag with the track data
            script_tag = soup.find("script", {"id": "__NEXT_DATA__"})
            
            if not script_tag:
                return None
            
            json_data = json.loads(script_tag.string)
            
            # Navigate through the JSON to extract data
            try:
                page_props = json_data['props']['pageProps']
                
                # Extract Track Info
                track_info = page_props['data']['trackInfo']['data']['track']
                track_title = track_info.get('name', 'N/A')
                artist_name = track_info.get('artistName', 'N/A')
                track_release_date = track_info.get('releaseDate', 'N/A')
                spotify_id = track_info.get('spotifyId', 'N/A')
                
                # Extract Album Info
                album_info = page_props['data']['albumGet']['data']
                album_title = album_info.get('name', 'N/A')
                album_track_count = album_info.get('trackCount', 'N/A')
                album_release_timestamp = album_info.get('releaseDate', 0) / 1000
                album_release_date = datetime.fromtimestamp(album_release_timestamp).strftime('%Y-%m-%d') if album_release_timestamp > 0 else 'N/A'
                
                # Extract Credits/Writers
                credits_info = page_props['data']['creditsTrackCollaboratorsGet']['data']
                writers = []
                for credit in credits_info:
                    writer_name = credit.get('name')
                    roles = ', '.join([role['name'] for role in credit.get('roles', [])])
                    writers.append(f"{writer_name} ({roles})")
                
                # Extract Lyrics
                lyrics_body = page_props['data']['trackInfo']['data']['lyrics']['body']
                
                return {
                    'track': {
                        'title': track_title,
                        'artist': artist_name,
                        'release_date': track_release_date.split('T')[0] if 'T' in track_release_date else 'N/A',
                        'spotify_id': spotify_id
                    },
                    'album': {
                        'title': album_title,
                        'release_date': album_release_date,
                        'track_count': album_track_count
                    },
                    'credits': {
                        'writers': writers
                    },
                    'lyrics': lyrics_body
                }
                
            except KeyError as e:
                print(f"Could not find key {e} in the JSON data. The website's data structure may have changed.")
                return None
                
        except Exception as e:
            print(f"Error getting track from URL {lyrics_url}: {e}")
            return None

    def get_track_by_url(self, lyrics_url: str) -> Optional[Dict[str, Any]]:
        """
        Get track information from a direct lyrics URL
        """
        return self._get_track_from_url(lyrics_url)


if __name__ == "__main__":
    # Test the scraper
    scraper = MusixMatchScraper()
    
    # Test search
    print("=== Testing Search ===")
    search_results = scraper.search_tracks("hey jude", limit=5)
    print(f"Found {len(search_results)} tracks")
    for track in search_results:
        print(f"- {track['track_name']} by {track['artist_name']}")
    
    # Test getting lyrics
    print("\n=== Testing Lyrics ===")
    if search_results:
        first_track = search_results[0]
        lyrics_data = scraper.get_track_lyrics(first_track['artist_name'], first_track['track_name'])
        if lyrics_data:
            print(f"Title: {lyrics_data['track']['title']}")
            print(f"Artist: {lyrics_data['track']['artist']}")
            print(f"Lyrics preview: {lyrics_data['lyrics'][:200]}...")
        else:
            print("Could not get lyrics")
    
    # Test direct URL
    print("\n=== Testing Direct URL ===")
    direct_result = scraper.get_track_by_url("https://www.musixmatch.com/lyrics/Pinegrove/Flora")
    if direct_result:
        print(f"Title: {direct_result['track']['title']}")
        print(f"Artist: {direct_result['track']['artist']}")
        print(f"Lyrics preview: {direct_result['lyrics'][:200]}...")
    else:
        print("Could not get track from direct URL") 