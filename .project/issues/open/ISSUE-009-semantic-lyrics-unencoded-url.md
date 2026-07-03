# ISSUE-009: semantic_lyrics builds the lyrics URL without encoding reserved characters

**Severity**: LOW
**Type**: Bug
**Discovered By**: code-review-engineer
**Discovered During**: ad-hoc review
**Affected Files**: semantic_lyrics.py
**Assigned To**: unassigned
**Status**: Open

---

## Description

`semantic_lyrics.fetch_lyrics_web()` interpolates the artist and title straight into the
request path:

```python
# semantic_lyrics.py:15-16
url = f"https://api.lyrics.ovh/v1/{artist}/{title}"
resp = requests.get(url, timeout=10)
```

`requests` applies `requote_uri`, which percent-encodes spaces but leaves URL-reserved
characters (`/`, `?`, `#`, `&`) untouched. Those characters are common in real metadata and
silently corrupt the request path. The sibling module `story_reader.py:33` does this
correctly with `requests.utils.quote(...)`; `semantic_lyrics` was not updated to match.

## Reproduction / Evidence

```
artist="AC/DC", title="Hells Bells"
  -> https://api.lyrics.ovh/v1/AC/DC/Hells Bells   (the "/" becomes an extra path segment)

title="Hello? Is It Me"
  -> the "?" starts a query string; the path sent is ".../Hello"
```

Both yield a 404 / wrong lookup rather than the intended request. Because artist/title can
originate from a filename (`parse_artist_title`), a name containing `../` is also passed
through unencoded toward the third-party API (low impact — the host is fixed, so no SSRF).

## Impact

Lyric lookups fail for any artist or title containing a reserved character. Only the
standalone `semantic_lyrics.py` is affected today (the wired path goes through
`story_reader`, which encodes correctly), but the bug will surface the moment this module
is invoked directly or wired in.

## Suggested Fix

Encode each path segment, disallowing `/`:

```python
from urllib.parse import quote
url = f"https://api.lyrics.ovh/v1/{quote(artist, safe='')}/{quote(title, safe='')}"
```

(Note `quote`'s default `safe='/'` still leaves `/` unencoded — pass `safe=''` for path
segments.)

## Resolution

[Filled in when resolved.]

---

*Filed: 2026-06-30*
*Resolved: *
