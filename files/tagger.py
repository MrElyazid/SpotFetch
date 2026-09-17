"""MusicBrainz tagging for SpotFetch.

Identifies an audio file via its AcoustID fingerprint (when an API key is
configured) or a tag search, then embeds tags, front cover art
and lyrics. Works for mp3, m4a and flac.

The tag-search matching : lenient Lucene query followed by client-side
scoring of title/artist/duration similarity against the candidates, accepted
via a similarity floor and a best-vs-second margin is adapted from the
MusicBrainz Picard tagger (https://picard.musicbrainz.org), GPL-2.0-or-later.
"""

# Licensed under the GNU General Public License version 2 or later.  See the
# Portions derived from MusicBrainz Picard (GPL-2.0-or-later).

import json
import os
import re
import shutil
import subprocess
import time
import unicodedata

import requests
from .lyrics import fetch as fetch_lyrics
from mutagen.flac import FLAC, Picture
from mutagen.id3 import APIC, ID3, TALB, TDRC, TIT2, TPE1, TPE2, TRCK, TXXX, USLT
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from rich import print

MB = "https://musicbrainz.org/ws/2"
ACOUSTID = "https://api.acoustid.org/v2/lookup"
UA = "SpotFetch/0.1 (https://github.com/MrElyazid/SpotFetch)"
MATCH_SCORE = 0.9                 # minimum acoustid similarity to accept
LENGTH_SCORE_THRESHOLD_MS = 30000  # duration diff beyond this scores 0 (Picard)
QUERY_LIMIT = 10                   # MB recording candidates fetched per search
MATCH_MIN_SCORE = 0.6              # client-side similarity floor (Picard uses 0.25)
MATCH_MIN_MARGIN = 0.1             # required gap over the 2nd-best candidate
TIE_EPS = 0.01                     # scores this close are ties: prefer the established recording
SCORE_TITLE, SCORE_ARTIST, SCORE_LENGTH = 13, 4, 10  # weights (Picard)

# normalization patterns for junky YouTube-rip tags
BRACKET_DECOR = re.compile(r"[【\[({].*?[】\])}]")  # 【Hatsune Miku】 [MV] {HD}
FEAT_TAIL = re.compile(r"(?i)\s+\b(?:feat|ft|featuring)\.?\s+.*$")
JUNK_TOKENS = re.compile(
    r"\b(?:mv|pv|hq|hd|4k|fixed|reupload|full\s+version"
    r"|official\s+(?:video|audio|music\s+video)"
    r"|lyrics?\s+video)\b",
    re.IGNORECASE,
)
YOUTUBE_TAIL = re.compile(r"(?i)\s*-\s*youtube\s*$")


def fpcalc(path):
    """(duration [s], fingerprint) of an audio file, via chromaprint's fpcalc."""
    out = subprocess.run(["fpcalc", "-json", path], capture_output=True, text=True, check=True)
    d = json.loads(out.stdout)
    return int(d["duration"]), d["fingerprint"]


def tags(path):
    """The file's embedded tags as one flat dict; ffprobe is uniform across mp3/m4a/flac."""
    out = subprocess.run(["ffprobe", "-v", "quiet", "-show_format", "-of", "json", path],
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)["format"].get("tags", {})


def duration(path):
    """Audio duration in seconds (float) from ffprobe, 0.0 on failure."""
    try:
        out = subprocess.run(["ffprobe", "-v", "quiet", "-show_format", "-of", "json", path],
                             capture_output=True, text=True, check=True)
        return float(json.loads(out.stdout)["format"].get("duration", 0))
    except (subprocess.SubprocessError, ValueError, KeyError, TypeError):
        return 0.0


def _sim_norm(s):
    """Similarity normalization: lowercase, drop non-alphanumerics."""
    stripped = re.sub(r"\W+", "", s.lower())
    return stripped or s


def _lev_sim(a, b):
    """Levenshtein-based similarity in [0, 1] (1 = identical)."""
    a, b = _sim_norm(a), _sim_norm(b)
    n, m = len(a), len(b)
    if n == 0 or m == 0:
        return 0.0
    if n > m:
        a, b = b, a
        n, m = m, n
    current = list(range(n + 1))
    for i in range(1, m + 1):
        previous, current = current, [i] + [0] * n
        for j in range(1, n + 1):
            current[j] = min(
                previous[j] + 1, current[j - 1] + 1,
                previous[j - 1] + (a[j - 1] != b[i - 1]),
            )
    return 1.0 - current[n] / m


def similarity2(a, b):
    """Word-level fuzzy similarity of two strings (Picard's similarity.py)."""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    alist = [w for w in re.split(r"\W+", a.lower()) if w]
    blist = [w for w in re.split(r"\W+", b.lower()) if w]
    if not alist or not blist:
        return 0.0
    if len(alist) > len(blist):
        alist, blist = blist, alist
    score = 0.0
    for av in alist:
        ms, mp = 0.0, None
        for position, bv in enumerate(blist):
            s = _lev_sim(av, bv)
            if s > ms:
                ms, mp = s, position
        if mp is not None:
            score += ms
            if ms > 0.6:  # consumed: don't reuse this candidate word
                del blist[mp]
    return score / (len(alist) + len(blist) * 0.4)


def length_score(a, b):
    """Duration similarity: 1.0 when equal, linear decay over 30 s (Picard)."""
    if a is None or b is None:
        return 0.0
    return 1.0 - min(abs(a - b), LENGTH_SCORE_THRESHOLD_MS) / LENGTH_SCORE_THRESHOLD_MS


def _mb_score(node):
    """MB search score (0-100) as a 0.0-1.0 factor; 1.0 when absent (Picard)."""
    try:
        return int(node.get("score", 100)) / 100.0
    except (TypeError, ValueError):
        return 1.0


def _release_key(rec):
    """Release-set quality of a recording: (# dated releases, # releases)."""
    rels = rec.get("releases", [])
    return sum(1 for r in rels if r.get("date")), len(rels)


def escape_lucene_query(text):
    """Escape Lucene special characters (Picard's build_lucene_query)."""
    return re.sub(r"([+\-&|!(){}\[\]\^\"~*?:\\/])", r"\\\1", text)


CHANNEL_SUFFIX = re.compile(r"(?i)\s+(?:official|vevo)\s*$")


def clean_terms(artist, title):
    """One clean (artist, title) pair from junky rip tags, e.g.
    ("Queen Official", "Queen – Bohemian Rhapsody (Official Video Remastered)")
    -> ("Queen", "Bohemian Rhapsody")."""
    title = unicodedata.normalize("NFKC", title or "")
    hint, m = "", re.search(r"\(([^)]*)\)", title)  # "(Clean Tears)" -> artist fallback
    if m and not JUNK_TOKENS.search(m.group(1)):
        hint = re.sub(r"(?i)^feat\.?\s*", "", m.group(1)).strip()
    title = re.sub(r"\s+", " ", BRACKET_DECOR.sub(" ", title)).strip(" -")
    title = re.sub(r"\s+", " ", JUNK_TOKENS.sub(" ", title)).strip(" -")
    title = YOUTUBE_TAIL.sub("", title).strip(" -")
    title = title.replace(" – ", " - ").replace(" — ", " - ")  # unicode dashes
    parts = title.split(" - ")  # "Artist – Title" -> artist from prefix
    if len(parts) > 1:
        artist = parts[0] if not artist else artist
        title = " - ".join(parts[1:])
    artist = CHANNEL_SUFFIX.sub("", artist or hint or "").strip()
    artist = FEAT_TAIL.sub("", artist).strip()
    return artist, title


def mb_get(url, **params):
    """MusicBrainz GET with the mandatory UA and 1 req/s pacing;
    503s and timeouts are retried with exponential backoff."""
    for i in range(4):
        try:
            r = requests.get(url, headers={"User-Agent": UA},
                             params={**params, "fmt": "json"}, timeout=30)
            if r.status_code != 503:  # not rate limited: done
                break
        except requests.Timeout:
            pass
        time.sleep(2 ** i)
    else:
        raise RuntimeError(f"musicbrainz unreachable: {url}")
    r.raise_for_status()
    time.sleep(1)
    return r.json()


def best_acoustid_hit(results):
    """First candidate that is a confident match AND linked to an MB recording, else None."""
    for x in results:
        if x.get("score", 0) >= MATCH_SCORE and x.get("recordings"):
            return x
    return None


def credit_phrase(credit):
    """artist-credit list -> display string, e.g. "Clean Tears feat. 初音ミク"."""
    out = ""
    for c in credit or []:
        out += c if isinstance(c, str) else c["name"] + c.get("joinphrase", "")
    return out.strip()


def primary_artist(rec):
    """First artist name of the recording, e.g. "Clean Tears" (drops feat. credits)."""
    for c in rec.get("artist-credit") or []:
        if isinstance(c, dict):
            return c.get("name", "")
    return ""


def pick_best_release(rec):
    """Order rec["releases"] so the preferred one comes first: official status,
    a date, an artist-credit matching the recording's primary artist, and the
    earliest date. Returns the preferred release dict (or {} when none)."""
    primary = _sim_norm(primary_artist(rec))
    rels = list(rec.get("releases", []))
    def key(r):
        ac = r.get("artist-credit")
        name = _sim_norm(ac[0]["name"]) if ac and isinstance(ac[0], dict) else ""
        date = r.get("date") or ""
        return (
            r.get("status") != "Official",
            not bool(date),
            (not name) or name != primary,
            date,
        )
    rec["releases"] = sorted(rels, key=key)
    return rec["releases"][0] if rec["releases"] else {}


def identify_by_fingerprint(path, acoustid_key):
    """MB recording found via AcoustID, or None. Needs a key and the fpcalc binary."""
    if not acoustid_key:
        return None
    if shutil.which("fpcalc") is None:
        print("[TAG] acoustid key set but fpcalc is not installed, using tag search instead")
        return None
    try:
        print("[TAG] computing acoustic fingerprint...")
        dur, fp = fpcalc(path)
        r = requests.get(ACOUSTID, timeout=30, params={
            "client": acoustid_key, "duration": dur, "fingerprint": fp,
            "meta": "recordings+releasegroups+compress", "format": "json"}).json()
        if r.get("status") != "ok":
            return None
        hit = best_acoustid_hit(r.get("results", []))
        if hit is None:
            return None
        print("[TAG] fingerprint matched, fetching recording from MusicBrainz...")
        mbid = hit["recordings"][0]["id"]
        rec = mb_get(f"{MB}/recording/{mbid}", inc="artist-credits+releases")
        pick_best_release(rec)
        return rec
    except (requests.RequestException, RuntimeError, subprocess.SubprocessError, OSError, KeyError):
        return None


def _score_candidate(rec, artist, title, dur_ms):
    """Weighted similarity of the file's tags to an MB candidate, x search score."""
    parts = [
        (similarity2(title, rec.get("title", "")), SCORE_TITLE),
        (similarity2(artist, credit_phrase(rec.get("artist-credit"))), SCORE_ARTIST),
    ]
    if dur_ms > 0 and rec.get("length"):
        parts.append((length_score(dur_ms, int(rec["length"])), SCORE_LENGTH))
    weight = sum(w for _, w in parts)
    if weight == 0:
        return 0.0
    return sum(s * w for s, w in parts) / weight * _mb_score(rec)


def identify_by_tags(path):
    """MB recording found by a lenient tag search, scored client-side.

    Builds one forgiving Lucene query artist/track terms OR'd, duration
    matched via qdur then ranks the candidates by weighted
    title/artist/duration similarity x MB search score. The best candidate is
    accepted when it clears MATCH_MIN_SCORE and stays MATCH_MIN_MARGIN ahead
    of the best *different* track (same title+artist recordings count as one);
    otherwise None (mirrors Picard's matching).
    """
    t = tags(path)
    artist, title = clean_terms(t.get("artist", ""), t.get("title", ""))
    if not artist or not title:
        return None
    dur_ms = int(duration(path) * 1000)
    query = (
        f"artist:({escape_lucene_query(artist).lower()}) "
        f"track:({escape_lucene_query(title).lower()})"
    )
    if dur_ms > 0:
        query += f" qdur:({dur_ms // 1000})"
    print(f"[TAG] searching MusicBrainz for \"{title}\" - {artist}...")
    try:
        results = mb_get(f"{MB}/recording", limit=QUERY_LIMIT, query=query).get("recordings", [])
    except (requests.RequestException, RuntimeError) as e:
        print(f"[TAG] MusicBrainz search failed: {e}")
        return None
    if not results:
        return None
    rated = sorted(
        ((_score_candidate(rec, artist, title, dur_ms), rec) for rec in results),
        key=lambda x: x[0], reverse=True,
    )
    best_score, best_rec = rated[0]
    # near-tied scores are often the same song under duplicated MBIDs (identical
    # length, flighty search order); prefer the more established recording (most
    # dated releases) so a stray single-release duplicate without cover art
    # doesn't win by luck.
    near = [x for x in rated if x[0] >= best_score - TIE_EPS]
    if len(near) > 1:
        near.sort(key=lambda x: _release_key(x[1]), reverse=True)
        rated = near + [x for x in rated if x[0] < best_score - TIE_EPS]
        best_score, best_rec = rated[0]
    if best_score < MATCH_MIN_SCORE:
        return None
    # group candidates by (normalized title, artist): separate recordings of the
    # same song are one cluster, so the margin only guards against a *different*
    # track (cover, other artist, live version) getting too close.
    clusters = {}
    for s, rec in rated:
        key = (_sim_norm(rec.get("title", "")), _sim_norm(credit_phrase(rec.get("artist-credit"))))
        clusters[key] = max(clusters.get(key, 0.0), s)
    top_clusters = sorted(clusters.values(), reverse=True)
    if len(top_clusters) > 1 and best_score - top_clusters[1] < MATCH_MIN_MARGIN:
        return None
    pick_best_release(best_rec)
    return best_rec


def identify(path, acoustid_key=""):
    """The MB recording dict for this file, or None. Fingerprint (if key given) first."""
    rec = identify_by_fingerprint(path, acoustid_key)
    if rec is None:
        rec = identify_by_tags(path)
    return rec


def cover_art(rec):
    """(front art bytes, release id) from the Cover Art Archive, or (None, None)."""
    for rel in rec.get("releases", []):
        try:
            r = requests.get(f"https://coverartarchive.org/release/{rel['id']}/front",
                             headers={"User-Agent": UA}, timeout=30)
        except requests.RequestException:
            continue
        if r.status_code == 404:  # this release has no art, try the next
            continue
        r.raise_for_status()
        return r.content, rel["id"]
    return None, None


def recording_tracknumber(rec):
    """Track number of this recording on its first release, when numeric."""
    try:
        number = str(rec["releases"][0]["media"][0]["track"][0]["number"]).strip()
    except (KeyError, IndexError, TypeError):
        return None
    return number if number.isdigit() else None


def embed(path, title, artist, album=None, albumartist=None, date=None, cover=None,
          tracknumber=None, lyrics=None, release_id=None):
    """Embed tags + cover art + lyrics; handles mp3 (ID3), m4a (MP4) and flac (Vorbis).
    Junk frames left behind by yt-dlp/ffmpeg (video descriptions, comments,
    URLs, bogus genre/track) are stripped first. release_id is stored as a
    custom tag (TXXX / iTunes atom / Vorbis comment) for cover verification."""
    ext = path.rsplit(".", 1)[-1].lower()
    if ext == "mp3":
        audio = MP3(path, ID3=ID3)
        if audio.tags is None:
            audio.add_tags()
        t = audio.tags
        for frame in ("COMM", "TXXX", "TCON", "TRCK", "TDRC"):
            t.delall(frame)
        t.add(TIT2(encoding=3, text=title))
        t.add(TPE1(encoding=3, text=artist))
        if album:
            t.add(TALB(encoding=3, text=album))
        if albumartist:
            t.add(TPE2(encoding=3, text=albumartist))
        if date:
            t.add(TDRC(encoding=3, text=date))
        if tracknumber and str(tracknumber).isdigit():
            t.add(TRCK(encoding=3, text=str(tracknumber)))
        if lyrics:
            t.delall("USLT")
            t.add(USLT(encoding=3, lang="eng", desc="", text=lyrics))
        if cover:
            t.delall("APIC")  # drop the yt-dlp thumbnail
            t.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=cover))
        if release_id:
            t.add(TXXX(encoding=3, desc="MusicBrainz Release Id", text=[release_id]))
        audio.save()
    elif ext == "m4a":
        audio = MP4(path)
        if audio.tags is None:
            audio.add_tags()
        for key in ("\xa9cmt", "desc", "ldes", "\xa9gen", "trkn", "\xa9day"):
            audio.tags.pop(key, None)
        audio.tags["\xa9nam"] = [title]
        audio.tags["\xa9ART"] = [artist]
        if album:
            audio.tags["\xa9alb"] = [album]
        if albumartist:
            audio.tags["aART"] = [albumartist]
        if date:
            audio.tags["\xa9day"] = [date]
        if tracknumber and str(tracknumber).isdigit():
            audio.tags["trkn"] = [(int(tracknumber), 0)]
        if lyrics:
            audio.tags["\xa9lyr"] = [lyrics]
        if cover:
            audio.tags["covr"] = [MP4Cover(cover, imageformat=MP4Cover.FORMAT_JPEG)]
        if release_id:
            audio.tags["----:com.apple.iTunes:MusicBrainz Release Id"] = [release_id.encode()]
        audio.save()
    elif ext == "flac":
        audio = FLAC(path)
        junk = ("COMMENT", "DESCRIPTION", "SYNOPSIS", "PURL", "GENRE",
                "TRACKNUMBER", "DATE")
        for key in [k for k in audio.tags.keys() if k.upper() in junk]:  # case-insensitive
            del audio.tags[key]
        audio["TITLE"] = title
        audio["ARTIST"] = artist
        if album:
            audio["ALBUM"] = album
        if albumartist:
            audio["ALBUMARTIST"] = albumartist
        if date:
            audio["DATE"] = date
        if tracknumber and str(tracknumber).isdigit():
            audio["TRACKNUMBER"] = str(tracknumber)
        if lyrics:
            audio["LYRICS"] = lyrics
        if cover:
            audio.clear_pictures()  # drop the yt-dlp thumbnail
            picture = Picture()
            picture.type = 3
            picture.mime = "image/jpeg"
            picture.data = cover
            audio.add_picture(picture)
        if release_id:
            audio["MUSICBRAINZ_RELEASEID"] = release_id
        audio.save()


def tag_file(path, acoustid_key="", lyrics=False):
    """Identify a file and embed MB tags + cover (+ lyrics from lrclib);
    returns "title - artist", or None when unidentified (in which case the
    existing tags are left untouched)."""
    print(f"[TAG] identifying {os.path.basename(path)}...")
    rec = identify(path, acoustid_key)
    if rec is None:
        return None
    rel = rec.get("releases", [{}])[0]
    artist = credit_phrase(rec.get("artist-credit"))
    print("[TAG] downloading cover art...")
    cover, release_id = cover_art(rec)
    if release_id:
        print(f"[TAG] cover art from release {release_id}")
    if lyrics:
        print("[TAG] fetching lyrics...")
    lyrics_text = fetch_lyrics(
        artist=primary_artist(rec), track=rec["title"], album=rel.get("title"),
        duration_s=(rec.get("length") or 0) / 1000) if lyrics else None
    print("[TAG] embedding tags...")
    embed(path, title=rec["title"], artist=artist, album=rel.get("title"),
          albumartist=credit_phrase(rel.get("artist-credit")), date=rel.get("date"),
          cover=cover, tracknumber=recording_tracknumber(rec), lyrics=lyrics_text,
          release_id=release_id)
    return f"{rec['title']} - {artist}"
