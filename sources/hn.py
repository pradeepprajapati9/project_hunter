"""Hacker News ka monthly 'Freelancer? Seeking freelancer?' thread.

Us thread me 'SEEKING FREELANCER' wale comments = client (kaam dene wala).
'SEEKING WORK' wale = freelancer, unhe chhod dete hain.
"""

import re
from datetime import datetime, timezone

from lib import extract
from lib.net import get_json
from lib.store import lead_key, title_fingerprint

NAME = "hn"
SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date?tags=story&hitsPerPage=30&query="
ITEM_URL = "https://hn.algolia.com/api/v1/items/"

_CLIENT_MARK = re.compile(r"seeking\s+freelancer", re.I)
_WORKER_MARK = re.compile(r"seeking\s+work", re.I)


def fetch(cfg: dict) -> list:
    ua = cfg["user_agent"]
    hcfg = cfg["hn"]

    search = get_json(
        SEARCH_URL + requests_quote(hcfg["thread_query"]),
        ua, cfg["request_timeout"], cfg["request_delay_sec"],
    )
    if not search:
        return []

    threads = [
        h for h in search.get("hits", [])
        if _CLIENT_MARK.search(h.get("title") or "")
    ][: hcfg["threads_to_scan"]]

    if not threads:
        print("  hn: monthly thread nahi mila")
        return []

    leads = []
    for thread in threads:
        item = get_json(
            ITEM_URL + str(thread["objectID"]), ua,
            cfg["request_timeout"], cfg["request_delay_sec"],
        )
        if not item:
            continue

        hits = 0
        for comment in item.get("children") or []:
            lead = _to_lead(comment, thread, cfg)
            if lead:
                leads.append(lead)
                hits += 1
        print(f"  hn: {hits} clients / {len(item.get('children') or [])} comments "
              f"({(thread.get('title') or '')[:45]})")

    return leads


def _to_lead(comment: dict, thread: dict, cfg: dict):
    raw = comment.get("text") or ""
    if not raw or comment.get("author") is None:
        return None

    head = raw[:400]
    if not _CLIENT_MARK.search(head):
        return None
    if _WORKER_MARK.search(head) and not _CLIENT_MARK.search(head[:120]):
        return None

    body = extract.clean_text(raw)
    title = _make_title(body)
    if not title:
        return None
    cls = extract.classify(title, body, cfg["categories"])

    return {
        "id": lead_key(NAME, comment.get("id", title)),
        "fingerprint": title_fingerprint(title),
        "source": "Hacker News",
        "source_detail": (thread.get("title") or "HN freelancer thread")[:60],
        "title": title,
        "url": f"https://news.ycombinator.com/item?id={comment.get('id')}",
        "posted_at": _stamp(comment.get("created_at_i")),
        "author": comment.get("author") or "",
        "body": body,
        "budget": extract.find_budget(body),
        "contact": extract.find_contact(body),
        "category": cls["category"],
        "category_auto": cls["auto"],
        "topic": cls["topic"],
        "flags": extract.find_flags(body),
    }


def _make_title(body: str) -> str:
    """'SEEKING FREELANCER | Acme | Remote | need a scraper' -> pehli kaam ki line."""
    text = _CLIENT_MARK.sub("", body, count=1).lstrip(" |:-–—\n")
    line = next((l.strip(" |:-–—") for l in text.splitlines() if len(l.strip()) > 8), "")
    if not line:
        return ""
    return (line[:110].rstrip() + "…") if len(line) > 110 else line


def _stamp(created_at_i):
    try:
        return datetime.fromtimestamp(float(created_at_i), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return ""


def requests_quote(text: str) -> str:
    from urllib.parse import quote
    return quote(f'"{text}"')
