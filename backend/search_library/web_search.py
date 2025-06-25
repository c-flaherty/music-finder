import os
import time
from typing import List, Dict, Optional
import requests
import time
import trafilatura
from googleapiclient.discovery import build
from dotenv import load_dotenv
# Correctly load .env.local from the backend directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env.local'))

def get_google_links(query: str, n: int = 3) -> List[str]:
    """
    Get the first n organic links from Google Custom Search API.
    
    Args:
        query: Search query string
        n: Number of results to return (default: 5)
    
    Returns:
        List of URLs from search results
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")
    
    if not api_key or not cse_id:
        raise ValueError("GOOGLE_API_KEY and GOOGLE_CSE_ID environment variables must be set")
    start_time = time.time()
    try:
        service = build("customsearch", "v1", developerKey=api_key)
        resp = (service.cse()
                      .list(q=query, cx=cse_id, num=n, fields="kind,items(title,link)")
                      .execute())
        end_time = time.time()
        print(f"Time taken to get google links: {end_time - start_time} seconds")
        return [item["link"] for item in resp.get("items", [])]
    except Exception as e:
        print(f"Error fetching Google search results: {e}")
        return []


def fetch_clean_text(url: str, timeout: int = 15) -> Optional[str]:
    """
    Download and clean page content using trafilatura.
    
    Args:
        url: URL to fetch content from
        timeout: Request timeout in seconds (default: 15) - Note: Not used by trafilatura.fetch_url
    
    Returns:
        Cleaned text content or None if extraction failed
    """
    try:
        start_time = time.time()
        html = trafilatura.fetch_url(url)
        if not html:
            return None  # network issue or blocked request
        
        text = trafilatura.extract(html, include_comments=False)
        end_time = time.time()
        print(f"Time taken to extract text: {end_time - start_time} seconds")
        return text
    except Exception as e:
        print(f"Error fetching content from {url}: {e}")
        return None


def search_internet(query: str, top_n: int = 5) -> List[str]:
    """
    Search the internet for a query and return cleaned text from top results.
    
    Args:
        query: Search query string
        top_n: Number of top results to process (default: 5)
    
    Returns:
        List of cleaned text content from search results
    """
    results = []
    
    # Get search result URLs
    links = get_google_links(query, n=top_n)
    
    if not links:
        print("No search results found")
        return results
    
    # Fetch and clean content from each URL
    for link in links:
        text = fetch_clean_text(link)
        if text:
            results.append(text)
        
        # Polite crawl delay
        time.sleep(1)
    return results


def search_internet_with_urls(query: str, top_n: int = 5) -> Dict[str, Optional[str]]:
    """
    Search the internet for a query and return a mapping of URLs to cleaned text.
    
    Args:
        query: Search query string
        top_n: Number of top results to process (default: 5)
    
    Returns:
        Dictionary mapping URLs to their cleaned text content
    """
    corpus = {}
    
    # Get search result URLs
    links = get_google_links(query, n=top_n)
    
    if not links:
        print("No search results found")
        return corpus
    
    # Fetch and clean content from each URL
    for link in links:
        text = fetch_clean_text(link)
        corpus[link] = text[:4000]
        
        # Polite crawl delay
        time.sleep(1)
    
    return corpus


if __name__ == "__main__":
    # Example usage
    query = "quantum gravity overview"
    
    # Get just the text results
    texts = search_internet(query)
    print(f"Found {len(texts)} results:")
    for i, text in enumerate(texts, 1):
        print(f"\n--- Result {i} ---")
        print(text[:400] if text else "No content extracted")
        print("-" * 80)
    
    # Get results with URLs
    docs = search_internet_with_urls(query)
    print(f"\nFound {len(docs)} results with URLs:")
    for url, text in docs.items():
        print(f"\nURL: {url}")
        print(f"Content: {text[:400] if text else 'No content extracted'}")
        print("-" * 80) 