
from __future__ import annotations

import os
import random
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

import requests
import trafilatura
from dotenv import load_dotenv
from trafilatura.meta import reset_caches

# --------------------------------------------------------------------------- #
#  One‑time setup
# --------------------------------------------------------------------------- #
load_dotenv(
    dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env.local")
)

_BRAVE_API_KEY: str | None = os.getenv("BRAVE_API_KEY")
if not _BRAVE_API_KEY:
    raise ValueError("BRAVE_API_KEY env var must be set (see .env.local)")

_BRAVE_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"

_DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Encoding": "gzip",
    "Accept": "application/json",
}

# Single pooled HTTPS session (shared by all threads)
_TLS = requests.Session()
_TLS.headers.update(_DEFAULT_HEADERS)
_TLS.headers["X-Subscription-Token"] = _BRAVE_API_KEY
_TLS.mount(
    "https://",
    requests.adapters.HTTPAdapter(pool_maxsize=20, pool_block=False),
)

# --------------------------------------------------------------------------- #
#  Public helpers – same *interface*
# --------------------------------------------------------------------------- #

def get_google_links(query: str, n: int = 3) -> List[str]:
    """Return *n* result URLs for *query* via Brave Search.

    Retains the original name for backwards compatibility.
    """
    t0 = time.time()

    params = {
        "q": query,
        "count": n,
        # Reasonable, explicit defaults – feel free to expose as kwargs
        "country": "US",
        "search_lang": "en",
        "result_filter": "web",  # only canonical web results
    }

    r = _TLS.get(_BRAVE_ENDPOINT, params=params, timeout=10)
    r.raise_for_status()
    data: dict = r.json()

    links: List[str] = [
        item.get("url")
        for item in data.get("web", {}).get("results", [])
        if item.get("url")
    ]

    print(f"[PROFILE] get_google_links (Brave): {time.time() - t0:.3f}s")
    return links[:n]


# --------------------------------------------------------------------------- #
#  Core fetch + extract logic
# --------------------------------------------------------------------------- #

def _fetch_clean_text(url: str, timeout: int = 10, max_retries: int = 2) -> Optional[str]:
    """Download *url* and return the main article text (or None on failure)."""
    for attempt in range(max_retries):
        try:
            resp = _TLS.get(url, timeout=timeout, allow_redirects=True)
            resp.raise_for_status()

            if not resp.text or len(resp.text) < 10:
                raise ValueError("empty response")

            txt = trafilatura.extract(
                resp.text, include_comments=False, no_fallback=True, url=url
            )
            return txt

        except Exception as exc:
            if attempt == max_retries - 1:
                print(f"[warn] fetch failed {url[:60]}…: {exc}")
                return None
            backoff = 1.5 * (attempt + 1) + random.random()
            print(
                f"[PROFILE] retry {attempt + 1}/{max_retries - 1}: {type(exc).__name__} for {url[:60]} – sleeping {backoff:.1f}s"
            )
            time.sleep(backoff)


# --------------------------------------------------------------------------- #
#  Parallel wrapper – thread pool (I/O bound)
# --------------------------------------------------------------------------- #

def _parallel_fetch(
    urls: List[str], timeout: int = 10, max_retries: int = 2
) -> List[Optional[str]]:
    t0 = time.time()
    results: List[Optional[str]] = [None] * len(urls)

    if not urls:
        return results

    if len(urls) == 1:
        results[0] = _fetch_clean_text(urls[0], timeout, max_retries)
    else:
        max_workers = min(16, len(urls))  # generous for I/O but avoids oversubscription
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            fut_to_idx = {
                pool.submit(_fetch_clean_text, url, timeout, max_retries): i
                for i, url in enumerate(urls)
            }
            for fut in as_completed(fut_to_idx):
                idx = fut_to_idx[fut]
                try:
                    results[idx] = fut.result()
                except Exception as exc:  # pragma: no‑cover – defensive guard
                    print(f"[warn] worker crash on {urls[idx][:60]}: {exc}")

    print(f"[PROFILE] _parallel_fetch: {time.time() - t0:.3f}s for {len(urls)} URLs")
    return results


# --------------------------------------------------------------------------- #
#  High‑level helpers
# --------------------------------------------------------------------------- #

def search_internet(
    query: str, top_n: int = 5, timeout: int = 15, max_retries: int = 2
) -> List[str]:
    """Return list of plain‑text articles for *query* (best‑effort)."""
    t0 = time.time()
    links = get_google_links(query, n=top_n)
    texts = _parallel_fetch(links, timeout=timeout, max_retries=max_retries)
    reset_caches()  # keep libxml2 heap clean
    docs = [t for t in texts if t]
    print(
        f"[PROFILE] search_internet: {time.time() - t0:.3f}s total (query: '{query}', found {len(docs)} docs)"
    )
    return docs


def search_internet_with_urls(
    query: str,
    top_n: int = 5,
    timeout: int = 15,
    max_retries: int = 2,
) -> Dict[str, Optional[str]]:
    """Return mapping url -> article_text (first 4k chars)."""
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
