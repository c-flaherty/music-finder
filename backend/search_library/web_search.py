# fast_search.py  – revision: compatible with any trafilatura ≥1.4
import os, time, requests, trafilatura
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from googleapiclient.discovery import build
from dotenv import load_dotenv
import random

# --------------------------------------------------------------------------- #
#  One-time setup
# --------------------------------------------------------------------------- #
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     '.env.local'))

_GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
_GOOGLE_CSE_ID  = os.getenv("GOOGLE_CSE_ID")
if not _GOOGLE_API_KEY or not _GOOGLE_CSE_ID:
    raise ValueError("GOOGLE_API_KEY and GOOGLE_CSE_ID env vars must be set")

_SERVICE = build("customsearch", "v1",
                 developerKey=_GOOGLE_API_KEY,
                 cache_discovery=False)

# Don't reuse sessions to avoid SSL memory corruption issues
# Each request will get a fresh session
_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Encoding": "gzip",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "close",  # Don't keep connections alive to avoid issues
}

# --------------------------------------------------------------------------- #
#  Public helpers – *unchanged* API
# --------------------------------------------------------------------------- #
def get_google_links(query: str, n: int = 3) -> List[str]:
    t0 = time.time()
    resp = (_SERVICE.cse()
                    .list(q=query,
                          cx=_GOOGLE_CSE_ID,
                          num=n,
                          fields="items(link)")
                    .execute())
    elapsed = time.time() - t0
    print(f"[PROFILE] get_google_links: {elapsed:.3f}s")
    return [it["link"] for it in resp.get("items", [])]

def fetch_clean_text(url: str, timeout: int = 15, max_retries: int = 2) -> Optional[str]:
    """
    Download *url* and extract main text using trafilatura.
    Returns None on network/parse failure.
    Simplified for safety to avoid memory corruption.
    """
    t0 = time.time()
    
    for attempt in range(max_retries):
        try:
            # Use simple requests without complex SSL handling to avoid memory corruption
            headers = _DEFAULT_HEADERS.copy()
            
            # Simple retry strategy: just try again on failure
            r = requests.get(url, timeout=timeout, allow_redirects=True, headers=headers)
            if not r.ok or not r.text:
                if attempt < max_retries - 1:
                    print(f"[PROFILE] fetch_clean_text (retry {attempt + 1}): HTTP {r.status_code} for {url[:60]}...")
                    time.sleep(random.uniform(1, 2))  # Shorter delays
                    continue
                else:
                    elapsed = time.time() - t0
                    print(f"[PROFILE] fetch_clean_text (failed): {elapsed:.3f}s for {url[:60]}...")
                    return None
            
            # Extract text using trafilatura
            result = trafilatura.extract(r.text, include_comments=False, no_fallback=True, url=url)
            elapsed = time.time() - t0
            print(f"[PROFILE] fetch_clean_text (success): {elapsed:.3f}s for {url[:60]}...")
            return result
            
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"[PROFILE] fetch_clean_text (retry {attempt + 1}): {type(e).__name__} for {url[:60]}...")
                time.sleep(random.uniform(1, 2))  # Shorter delays
                continue
            else:
                elapsed = time.time() - t0
                print(f"[PROFILE] fetch_clean_text (error): {elapsed:.3f}s for {url[:60]}...")
                print(f"[warn] fetch failed {url[:60]}…: {e}")
                return None
    
    return None

# --------------------------------------------------------------------------- #
#  Parallel wrappers – safer with reduced concurrency
# --------------------------------------------------------------------------- #
def _parallel_fetch(urls: List[str], timeout: int = 15, max_retries: int = 2) -> List[Optional[str]]:
    t0 = time.time()
    out: List[Optional[str]] = [None] * len(urls)
    
    # Reduce concurrency to avoid memory corruption issues
    max_workers = min(3, len(urls))  # Much lower concurrency for safety
    
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(fetch_clean_text, u, timeout, max_retries): i
                   for i, u in enumerate(urls)}
        for fut in as_completed(futures):
            out[futures[fut]] = fut.result()
    elapsed = time.time() - t0
    print(f"[PROFILE] _parallel_fetch: {elapsed:.3f}s for {len(urls)} URLs (max_workers: {max_workers})")
    return out

def search_internet(query: str, top_n: int = 5, timeout: int = 15, max_retries: int = 2) -> List[str]:
    t0 = time.time()
    links = get_google_links(query, n=top_n)
    texts = _parallel_fetch(links, timeout=timeout, max_retries=max_retries)
    result = [t for t in texts if t]
    elapsed = time.time() - t0
    print(f"[PROFILE] search_internet: {elapsed:.3f}s total (query: '{query}', found {len(result)} docs)")
    return result

def search_internet_with_urls(query: str,
                              top_n: int = 5, 
                              timeout: int = 15, 
                              max_retries: int = 2) -> Dict[str, Optional[str]]:
    t0 = time.time()
    links = get_google_links(query, n=top_n)
    texts = _parallel_fetch(links, timeout=timeout, max_retries=max_retries)
    result = {u: (t[:4000] if t else None) for u, t in zip(links, texts)}
    elapsed = time.time() - t0
    successful_fetches = sum(1 for v in result.values() if v is not None)
    print(f"[PROFILE] search_internet_with_urls: {elapsed:.3f}s total (query: '{query}', {successful_fetches}/{len(result)} successful)")
    return result

# --------------------------------------------------------------------------- #
#  Quick smoke-test
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    test_queries = [
        "quantum gravity overview",
        "deep learning tutorial",
        "pf400 robot calibration",
        "isaac sim reinforcement learning",
        "vision language action models",
        "self-supervised learning biology",
        "plate handling robot safety",
        "large language model benchmarks 2025",
        "generative ai startup trends",
        "custom ASIC acceleration pytorch"
    ]

    t_total = time.time()
    for idx, q in enumerate(test_queries, 1):
        t0 = time.time()
        docs = search_internet(q, top_n=5)
        elapsed = time.time() - t0
        print(f"\n[{idx}/10] \"{q}\" → {len(docs)} docs in {elapsed:.2f}s")
    print(f"\nCompleted {len(test_queries)} searches in {time.time() - t_total:.2f}s")
