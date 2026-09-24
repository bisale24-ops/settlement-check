"""The Panta catalogue, read-only.

Every call here is a GET. This tool never quotes, builds, signs or submits a transaction, so it
never needs a wallet and never spends anything. The key is read from a file outside the repository
and is never logged.
"""
import json
import os
import pathlib
import time
import urllib.error
import urllib.request

BASE = os.environ.get("PANTA_API", "https://live-api.panta.market/api/v1")
KEY_FILE = pathlib.Path(os.environ.get("PANTA_KEY_FILE", pathlib.Path.home() / ".config/panta.key"))


class PantaError(RuntimeError):
    pass


def api_key():
    key = os.environ.get("PANTA_API_KEY", "")
    if not key and KEY_FILE.exists():
        key = KEY_FILE.read_text().strip()
    if not key:
        raise PantaError(f"no API key: set PANTA_API_KEY or write one to {KEY_FILE}")
    return key


def get(path, params=None, timeout=30, retries=3):
    """One GET against the catalogue, with a short retry on transport errors."""
    query = "&".join(f"{k}={v}" for k, v in (params or {}).items() if v not in (None, ""))
    url = f"{BASE}/{path.lstrip('/')}" + (f"?{query}" if query else "")
    request = urllib.request.Request(url, headers={
        "X-Api-Key": api_key(),
        "Accept": "application/json",
        # The gateway rejects urllib's default agent on some paths; say who we are.
        "User-Agent": "settlement-check/0.1",
    })
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", "replace")[:300]
            if error.code in (429, 502, 503, 504) and attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise PantaError(f"HTTP {error.code} on {path}: {body}") from None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            if attempt + 1 < retries:
                time.sleep(1.0 * (attempt + 1))
                continue
            raise PantaError(f"{type(error).__name__} on {path}") from None
    raise PantaError(f"gave up on {path}")


MAX_PAGES = 200  # a catalogue this size is someone else's server; never walk it unbounded

# The documented cursor pagination does not advance: passing a page's own `nextCursor` back returns
# the identical page and the identical cursor (reproduced with curl on 2026-09-24, limit=5 and
# limit=50). So the catalogue cannot be walked. What does work is asking for one phase at a time,
# which returns a different 50 rows per phase — the slices below are the whole coverage there is.
# `status=resolved` and `status=cancelled` return nothing at all, though unfiltered pages contain
# rows in both phases.
SLICES = ("", "primary", "secondary")


def page(limit=50, status="", cursor=None):
    params = {"limit": min(limit, 50), "cursor": cursor}
    if status:
        params["status"] = status
    payload = get("markets/", params)
    return payload.get("items", []), payload.get("nextCursor")


def markets(limit=50, pages=None, sleep=0.15, max_markets=None, slices=SLICES):
    """Every row the catalogue will actually hand over, de-duplicated by `marketId`.

    Each slice is one request, because a second request with the returned cursor brings the same
    rows back. If the cursor is ever fixed upstream, `page()` already accepts one.
    """
    found = {}
    for status in slices:
        rows, _cursor = page(limit=limit, status=status)
        for row in rows:
            found.setdefault(row["marketId"], row)
        if max_markets is not None and len(found) >= max_markets:
            break
        time.sleep(sleep)
    out = list(found.values())
    return out[:max_markets] if max_markets else out


def market(market_id):
    """The full card: `description`, `oracle`, phase, prices, creator."""
    return get(f"markets/{market_id}/")


def account():
    return get("account/")
