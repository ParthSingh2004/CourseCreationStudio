import requests
import traceback
from typing import Optional
from config import Config


def fetch_unsplash_image(query: str, width: int = 800) -> Optional[bytes]:
    """
    Fetch a topic-relevant photo for a slide.

    Strategy (two-tier with automatic fallback):
      1. Unsplash /photos/random API — preferred (high quality, keyword-relevant).
         Requires UNSPLASH_ACCESS_KEY in .env.
         If the key is missing, rate-limited (403), or the request fails for
         any reason we fall through to the next tier automatically.
      2. LoremFlickr — free, no API key needed, keyword-aware CC-licensed photos.
         URL format: https://loremflickr.com/1080/720/{keyword1,keyword2,...}
         Used as a silent fallback whenever Unsplash cannot supply an image.

    Returns raw JPEG/PNG bytes on success, None if both tiers fail.
    Never raises — designed to fail silently so slide_builder can fall back
    to a text-only layout without crashing the pipeline.
    """
    if not query or not query.strip():
        print("[image_fetcher] ⚠ Skipping fetch — query is empty.")
        return None

    # ── Tier 1: Unsplash ──────────────────────────────────────────────────────
    access_key = Config.UNSPLASH_ACCESS_KEY
    if access_key:
        result = _try_unsplash(query.strip(), access_key)
        if result:
            return result
        print("[image_fetcher] ↳ Unsplash unavailable — trying LoremFlickr fallback.")
    else:
        print("[image_fetcher] ⚠ UNSPLASH_ACCESS_KEY not set — going straight to LoremFlickr.")

    # ── Tier 2: LoremFlickr (no key required) ─────────────────────────────────
    return _try_loremflickr(query.strip())


# ── Unsplash helper ───────────────────────────────────────────────────────────

def _try_unsplash(query: str, access_key: str) -> Optional[bytes]:
    """
    Call the Unsplash /photos/random endpoint.
    Returns image bytes on success, None on any error (rate-limit, auth, network).
    """
    search_url = "https://api.unsplash.com/photos/random"
    params = {
        "query":          query,
        "orientation":    "landscape",
        "content_filter": "high",
        "client_id":      access_key,
    }
    # Sending Accept-Version and a descriptive User-Agent is required by the
    # Unsplash API guidelines and avoids some 401 responses.
    headers = {
        "Accept-Version": "v1",
        "User-Agent":     "CourseEngineApp/1.0",
    }

    print(f"[image_fetcher] Requesting Unsplash photo for query: '{query}'")
    try:
        meta_resp = requests.get(search_url, params=params, headers=headers, timeout=10)
        print(f"[image_fetcher] Unsplash metadata response: HTTP {meta_resp.status_code}")

        if meta_resp.status_code == 401:
            print("[image_fetcher] ✗ Invalid Unsplash API key (401). Check UNSPLASH_ACCESS_KEY in .env.")
            return None
        if meta_resp.status_code == 403:
            print("[image_fetcher] ✗ Unsplash rate limit hit (403) — will fall back.")
            return None
        if meta_resp.status_code != 200:
            print(f"[image_fetcher] ✗ Unsplash returned unexpected status {meta_resp.status_code}.")
            return None

        meta      = meta_resp.json()
        image_url = meta.get("urls", {}).get("regular")
        if not image_url:
            print("[image_fetcher] ✗ Unsplash response missing 'urls.regular' field.")
            return None

        print(f"[image_fetcher] Got Unsplash URL: {image_url[:80]}...")

        # Download the actual image bytes
        img_resp     = requests.get(image_url, timeout=15, allow_redirects=True)
        content_type = img_resp.headers.get("Content-Type", "")
        print(
            f"[image_fetcher] Image download: HTTP {img_resp.status_code}, "
            f"Content-Type: {content_type}, Bytes: {len(img_resp.content)}"
        )

        if img_resp.status_code == 200 and img_resp.content and "image" in content_type:
            print(f"[image_fetcher] ✓ Unsplash fetch successful ({len(img_resp.content):,} bytes).")
            return img_resp.content

        print(
            f"[image_fetcher] ✗ Unsplash image download failed — "
            f"status={img_resp.status_code}, content_type='{content_type}'"
        )
        return None

    except requests.exceptions.Timeout:
        print(f"[image_fetcher] ✗ Timeout on Unsplash for query: '{query}'")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"[image_fetcher] ✗ Connection error on Unsplash for '{query}': {e}")
        return None
    except Exception as e:
        print(f"[image_fetcher] ✗ Unexpected Unsplash error for '{query}': {e}")
        traceback.print_exc()
        return None


# ── LoremFlickr fallback ──────────────────────────────────────────────────────

def _try_loremflickr(query: str) -> Optional[bytes]:
    """
    Fallback image source — LoremFlickr.
    - Completely free, no API key required.
    - Keyword-aware: returns CC-licensed Flickr photos matching the query terms.
    - URL: https://loremflickr.com/1080/720/{keyword1,keyword2,...}
    """
    # Replace spaces with commas — LoremFlickr treats them as OR keywords
    keyword = query.replace(" ", ",")
    url     = f"https://loremflickr.com/1080/720/{keyword}"
    print(f"[image_fetcher] Trying LoremFlickr fallback: {url}")
    try:
        resp         = requests.get(url, timeout=15, allow_redirects=True)
        content_type = resp.headers.get("Content-Type", "")
        print(
            f"[image_fetcher] LoremFlickr response: HTTP {resp.status_code}, "
            f"Content-Type: {content_type}, Bytes: {len(resp.content)}"
        )
        if resp.status_code == 200 and resp.content and "image" in content_type:
            print(f"[image_fetcher] ✓ LoremFlickr fetch successful ({len(resp.content):,} bytes).")
            return resp.content

        print(f"[image_fetcher] ✗ LoremFlickr failed — status={resp.status_code}, type={content_type}")
        return None

    except requests.exceptions.Timeout:
        print(f"[image_fetcher] ✗ Timeout on LoremFlickr for query: '{query}'")
        return None
    except Exception as e:
        print(f"[image_fetcher] ✗ LoremFlickr error for '{query}': {e}")
        return None
