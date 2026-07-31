"""Ek hi jagah se HTTP — retry, delay, timeout."""

import time

import requests

_last_call = {"t": 0.0}


def _fetch(url: str, user_agent: str, accept: str, timeout: int, delay: float, tries: int):
    gap = delay - (time.monotonic() - _last_call["t"])
    if gap > 0:
        time.sleep(gap)

    headers = {"User-Agent": user_agent, "Accept": accept}
    for attempt in range(1, tries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            _last_call["t"] = time.monotonic()
            if resp.status_code == 429:
                if attempt == tries:
                    print(f"  ! {url[:70]} -> rate limited (429), skip")
                    return None
                wait = _retry_after(resp) or 15 * attempt
                print(f"  . rate limit, {wait}s ruk kar dubara...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        except (requests.RequestException, ValueError) as err:
            _last_call["t"] = time.monotonic()
            if attempt == tries:
                print(f"  ! {url[:70]} -> {type(err).__name__}")
                return None
            time.sleep(2 * attempt)
    return None


def _retry_after(resp) -> int:
    try:
        return min(60, int(resp.headers.get("Retry-After", "")))
    except (TypeError, ValueError):
        return 0


def get_json(url: str, user_agent: str, timeout: int = 20, delay: float = 2.0, tries: int = 3):
    """JSON laao. Fail hone pe None, crash nahi."""
    resp = _fetch(url, user_agent, "application/json", timeout, delay, tries)
    if resp is None:
        return None
    try:
        return resp.json()
    except ValueError:
        print(f"  ! {url[:70]} -> JSON nahi hai")
        return None


def get_text(url: str, user_agent: str, timeout: int = 20, delay: float = 2.0, tries: int = 3):
    """Raw text (RSS/XML) laao."""
    resp = _fetch(url, user_agent, "application/atom+xml, application/rss+xml, text/xml", timeout, delay, tries)
    return resp.text if resp is not None else None
