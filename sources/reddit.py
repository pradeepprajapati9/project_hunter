"""Reddit hiring posts.

Reddit ka .json endpoint ab bina app-credentials 403 deta hai,
par public .rss feed khulta hai — isliye Atom parse karte hain.
"""

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from lib import extract
from lib.net import get_text
from lib.store import lead_key, title_fingerprint

NAME = "reddit"
ATOM = "{http://www.w3.org/2005/Atom}"


def fetch(cfg: dict) -> list:
    ua = cfg["user_agent"]
    rcfg = cfg["reddit"]
    leads = []

    for sub in rcfg["subreddits"]:
        url = f"https://www.reddit.com/r/{sub['name']}/new.rss?limit={rcfg['limit_per_sub']}"
        xml = get_text(url, ua, cfg["request_timeout"], cfg["request_delay_sec"])
        if not xml:
            continue

        try:
            entries = ET.fromstring(xml).findall(f"{ATOM}entry")
        except ET.ParseError:
            print(f"  ! r/{sub['name']}: feed parse fail")
            continue

        hits = 0
        for entry in entries:
            lead = _to_lead(entry, sub, cfg)
            if lead:
                leads.append(lead)
                hits += 1
        print(f"  r/{sub['name']:<18} {hits:>3} hiring / {len(entries):>3} posts")

    return leads


def _to_lead(entry, sub: dict, cfg: dict):
    title = _text(entry, "title")
    low = title.lower()

    if not any(tag in low[:40] for tag in sub["tags"]):
        return None
    if any(bad in low for bad in cfg["reject_keywords"]):
        return None

    body = extract.clean_text(_text(entry, "content"))
    body = _drop_reddit_footer(body)
    blob = f"{title}\n{body}"
    clean_title = extract.strip_tag(title)

    link_el = entry.find(f"{ATOM}link")
    url = link_el.get("href", "") if link_el is not None else ""
    cls = extract.classify(clean_title, body, cfg["categories"])

    author = ""
    author_el = entry.find(f"{ATOM}author/{ATOM}name")
    if author_el is not None and author_el.text:
        author = author_el.text.lstrip("/").removeprefix("u/")

    return {
        "id": lead_key(NAME, _text(entry, "id") or url or title),
        "fingerprint": title_fingerprint(clean_title),
        "source": "Reddit",
        "source_detail": "r/" + sub["name"],
        "title": clean_title,
        "url": url,
        "posted_at": _stamp(_text(entry, "published") or _text(entry, "updated")),
        "author": author,
        "body": body,
        "budget": extract.find_budget(blob),
        "contact": extract.find_contact(blob),
        "category": cls["category"],
        "category_auto": cls["auto"],
        "topic": cls["topic"],
        "flags": extract.find_flags(blob),
    }


def _text(entry, tag: str) -> str:
    el = entry.find(f"{ATOM}{tag}")
    return (el.text or "").strip() if el is not None else ""


_FOOTER = re.compile(r"submitted by\s+/u/\S+.*$", re.I | re.S)


def _drop_reddit_footer(body: str) -> str:
    return _FOOTER.sub("", body).strip()


def _stamp(value: str) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return ""
