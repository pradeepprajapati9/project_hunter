"""Dedupe memory and lead files. Plain JSON, no database."""

import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
SEEN_FILE = os.path.join(DATA_DIR, "seen.json")
LEADS_FILE = os.path.join(DATA_DIR, "leads.json")
ARCHIVE_FILE = os.path.join(DATA_DIR, "archive.jsonl")
REJECTED_FILE = os.path.join(DATA_DIR, "rejected.jsonl")
PUBLIC_FILE = os.path.join(DATA_DIR, "leads.public.json")

_STOP = {"a", "an", "the", "for", "to", "of", "and", "or", "in", "on", "with", "need",
         "needed", "looking", "want", "wanted", "help", "please", "someone", "hiring",
         "my", "me", "i", "we", "is", "are", "who", "can", "will", "usd", "paid"}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def title_fingerprint(title: str) -> str:
    """Catches cross-posts: same words means same lead, whatever the word order."""
    words = re.findall(r"[a-z0-9]+", (title or "").lower())
    core = sorted({w for w in words if w not in _STOP and len(w) > 2})
    return hashlib.sha1(" ".join(core[:12]).encode()).hexdigest()[:16]


def lead_key(source: str, external_id: str) -> str:
    return hashlib.sha1(f"{source}:{external_id}".encode()).hexdigest()[:16]


class Store:
    def __init__(self, seen_memory_days: int = 30, live_window_days: int = 7):
        self.seen_memory_days = seen_memory_days
        self.live_window_days = live_window_days
        os.makedirs(DATA_DIR, exist_ok=True)
        self.seen = self._load_seen()

    # -- seen memory -------------------------------------------------------

    def _load_seen(self) -> dict:
        try:
            with open(SEEN_FILE, encoding="utf-8") as f:
                seen = json.load(f)
        except (OSError, ValueError):
            return {}
        cutoff = now_utc() - timedelta(days=self.seen_memory_days)
        return {k: v for k, v in seen.items() if _parse(v) and _parse(v) > cutoff}

    def is_new(self, lead: dict) -> bool:
        return lead["id"] not in self.seen and lead["fingerprint"] not in self.seen

    def remember(self, lead: dict) -> None:
        stamp = _iso(now_utc())
        self.seen[lead["id"]] = stamp
        self.seen[lead["fingerprint"]] = stamp

    def save_seen(self) -> None:
        _write_json(SEEN_FILE, self.seen)

    # -- leads -------------------------------------------------------------

    def reject(self, lead: dict) -> None:
        """Keep everything dropped as a scam, so false positives can be reviewed."""
        with open(REJECTED_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(lead, ensure_ascii=False) + "\n")

    def load_leads(self) -> list:
        try:
            with open(LEADS_FILE, encoding="utf-8") as f:
                return json.load(f).get("leads", [])
        except (OSError, ValueError):
            return []

    @staticmethod
    def publish_public(payload: dict) -> str:
        """Safe copy for GitHub Pages, without poster names or contact values.

        The link to the original post stays, since that post is already public;
        nobody's personal details get republished on our page.
        """
        safe = []
        for lead in payload["leads"]:
            copy = dict(lead)
            copy["author"] = ""
            copy["contact"] = {"kind": lead["contact"]["kind"], "value": ""}
            copy.pop("fingerprint", None)
            safe.append(copy)

        _write_json(PUBLIC_FILE, {**payload, "leads": safe, "public": True})
        return PUBLIC_FILE

    def publish(self, fresh: list) -> dict:
        """Merge new leads with existing ones and drop anything past the window."""
        cutoff = now_utc() - timedelta(days=self.live_window_days)
        merged, keys = [], set()
        for lead in fresh + self.load_leads():
            if lead["id"] in keys:
                continue
            posted = _parse(lead.get("posted_at"))
            if posted and posted < cutoff:
                continue
            keys.add(lead["id"])
            merged.append(lead)

        merged.sort(key=lambda l: l.get("posted_at") or "", reverse=True)
        payload = {
            "generated_at": _iso(now_utc()),
            "total": len(merged),
            "new_this_run": len(fresh),
            "leads": merged,
        }
        _write_json(LEADS_FILE, payload)

        if fresh:
            with open(ARCHIVE_FILE, "a", encoding="utf-8") as f:
                for lead in fresh:
                    f.write(json.dumps(lead, ensure_ascii=False) + "\n")
        return payload


def _parse(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _write_json(path: str, data) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
