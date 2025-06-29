from __future__ import annotations

import os
import random
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Optional

import requests
import trafilatura
from dotenv import load_dotenv
from googleapiclient.discovery import build
from trafilatura.meta import reset_caches

# --------------------------------------------------------------------------- #
#  One‑time setup
# --------------------------------------------------------------------------- #
load_dotenv(
    dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env.local")
)

_GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
_GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
if not _GOOGLE_API_KEY or not _GOOGLE_CSE_ID:
    raise ValueError("GOOGLE_API_KEY and GOOGLE_CSE_ID env vars must be set")

_SERVICE = build("customsearch", "v1", developerKey=_GOOGLE_API_KEY, cache_discovery=False)

_DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Encoding": "gzip",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Single pooled HTTPS session (one per *process*)
_TLS = requests.Session()
_TLS.headers.update(_DEFAULT_HEADERS)
_TLS.mount(
    "https://",
    requests.adapters.HTTPAdapter(pool_maxsize=10, pool_block=False),
)


# --------------------------------------------------------------------------- #
#  Public helpers – same API
# --------------------------------------------------------------------------- #

def get_google_links(query: str, n: int = 3) -> List[str]:
    t0 = time.time()
    resp = (
        _SERVICE.cse()
        .list(q=query, cx=_GOOGLE_CSE_ID, num=n, fields="items(link)")
        .execute()
    )
    print(f"[PROFILE] get_google_links: {time.time() - t0:.3f}s")
    return [it["link"] for it in resp.get("items", [])]


# --------------------------------------------------------------------------- #
#  Core fetch + extract logic (runs inside worker processes)
# --------------------------------------------------------------------------- #

def _fetch_clean_text(url: str, timeout: int = 10, max_retries: int = 2) -> Optional[str]:
    """Download *url* and return the main text (or None on failure)."""
    for attempt in range(max_retries):
        try:
            r = _TLS.get(url, timeout=timeout, allow_redirects=True)
            r.raise_for_status()

            if not r.text or len(r.text) < 10:
                raise ValueError("empty response")

            txt = trafilatura.extract(
                r.text, include_comments=False, no_fallback=True, url=url
            )
            return txt

        except Exception as e:
            if attempt == max_retries - 1:
                print(f"[warn] fetch failed {url[:60]}…: {e}")
                return None
            sleep_for = 1.5 * (attempt + 1) + random.random()
            print(
                f"[PROFILE] retry {attempt + 1}/{max_retries - 1}: {type(e).__name__} for {url[:60]} – sleeping {sleep_for:.1f}s"
            )
            time.sleep(sleep_for)


# --------------------------------------------------------------------------- #
#  Parallel wrapper – *process* pool
# --------------------------------------------------------------------------- #

def _parallel_fetch(urls: List[str], timeout: int = 10, max_retries: int = 2) -> List[Optional[str]]:
    t0 = time.time()
    out: List[Optional[str]] = [None] * len(urls)

    # Spawn a pool only if there is real work to do
    if len(urls) == 1:
        out[0] = _fetch_clean_text(urls[0], timeout, max_retries)
    else:
        max_workers = min(4, os.cpu_count() or 1)
        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            future_to_idx = {
                pool.submit(_fetch_clean_text, url, timeout, max_retries): i
                for i, url in enumerate(urls)
            }
            for fut in as_completed(future_to_idx):
                idx = future_to_idx[fut]
                try:
                    out[idx] = fut.result()
                except Exception as e:  # pragma: no‑cover – defensive guard
                    print(f"[warn] worker crash on {urls[idx][:60]}: {e}")

    print(f"[PROFILE] _parallel_fetch: {time.time() - t0:.3f}s for {len(urls)} URLs")
    return out


# --------------------------------------------------------------------------- #
#  High‑level helpers
# --------------------------------------------------------------------------- #

def search_internet(query: str, top_n: int = 5, timeout: int = 15, max_retries: int = 2) -> List[str]:
    t0 = time.time()
    links = get_google_links(query, n=top_n)
    texts = _parallel_fetch(links, timeout=timeout, max_retries=max_retries)
    reset_caches()  # keep libxml2 heap clean
    result = [t for t in texts if t]
    print(
        f"[PROFILE] search_internet: {time.time() - t0:.3f}s total (query: '{query}', found {len(result)} docs)"
    )
    return result


def search_internet_with_urls(
    query: str,
    top_n: int = 5,
    timeout: int = 15,
    max_retries: int = 2,
) -> Dict[str, Optional[str]]:
    t0 = time.time()
    links = get_google_links(query, n=top_n)
    texts = _parallel_fetch(links, timeout=timeout, max_retries=max_retries)
    reset_caches()
    result = {u: (t[:4000] if t else None) for u, t in zip(links, texts)}
    ok = sum(1 for v in result.values() if v is not None)
    print(
        f"[PROFILE] search_internet_with_urls: {time.time() - t0:.3f}s total (query: '{query}', {ok}/{len(result)} successful)"
    )
    return result


# --------------------------------------------------------------------------- #
#  Quick smoke‑test
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
        "custom ASIC acceleration pytorch",
    ]

    t_total = time.time()
    for idx, q in enumerate(test_queries, 1):
        t0 = time.time()
        docs = search_internet(q, top_n=5)
        print(f"\n[{idx}/10] \"{q}\" → {len(docs)} docs in {time.time() - t0:.2f}s")

    print(f"\nCompleted {len(test_queries)} searches in {time.time() - t_total:.2f}s")
