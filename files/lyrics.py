"""Lyrics fetching from LRCLIB (https://lrclib.net)"""

import requests

LRCLIB = "https://lrclib.net/api"
UA = "SpotFetch/1.0 (https://github.com/MrElyazid/SpotFetch)"
DURATION_TOLERANCE_S = 5


def _pick(result):
    """Best lyrics text of a lrclib result: synced (LRC) first, plain as fallback."""
    if result.get("instrumental"):
        return None
    return result.get("syncedLyrics") or result.get("plainLyrics") or None


def fetch(artist, track, album=None, duration_s=None):
    """Lyrics for a track: exact-match fetch first, then a filtered search.
    Returns the lyrics text, or None when not found."""
    params = {"artist_name": artist, "track_name": track}
    if album:
        params["album_name"] = album
    if duration_s:
        params["duration"] = int(duration_s)
    try:
        r = requests.get(f"{LRCLIB}/get", params=params,
                         headers={"User-Agent": UA}, timeout=30)
        if r.status_code == 200:
            text = _pick(r.json())
            if text:
                return text

        r = requests.get(f"{LRCLIB}/search",
                         params={"artist_name": artist, "track_name": track},
                         headers={"User-Agent": UA}, timeout=30)
        r.raise_for_status()
        results = r.json()
        if not isinstance(results, list):
            return None
        for result in results:
            text = _pick(result)
            if not text:
                continue
            if duration_s and abs(result.get("duration", 0) - duration_s) > DURATION_TOLERANCE_S:
                continue  # a different version (live, radio edit...), skip
            return text
    except requests.RequestException:
        return None
    return None
