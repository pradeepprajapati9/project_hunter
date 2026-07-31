"""Pull the useful bits out of a lead: budget, contact, category, flags, score."""

import html
import re
import unicodedata

# --- budget ---------------------------------------------------------------

_CUR = r"(?:\$|₹|€|£|USD|usd|INR|inr|EUR|eur|GBP|gbp|Rs\.?|rs\.?)"
_NUM = r"\d{1,3}(?:[,\s]\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?"

_BUDGET_PATTERNS = [
    # $500 - $1000  /  ₹5,000 to ₹10,000
    re.compile(rf"{_CUR}\s?(?:{_NUM})\s?(?:-|–|—|to|~)\s?{_CUR}?\s?(?:{_NUM})", re.I),
    # $500  /  ₹5,000  /  Rs 2000
    re.compile(rf"{_CUR}\s?(?:{_NUM})\s?(?:k\b)?", re.I),
    # 500 USD  /  2000 rs
    re.compile(rf"(?:{_NUM})\s?(?:k\s?)?{_CUR}\b", re.I),
]

_HOURLY = re.compile(r"(?:/\s?hr\b|/\s?hour\b|per\s?hour|hourly|an hour)", re.I)
_BUDGET_WORD = re.compile(r"\b(budget|pay(?:ing|ment)?|rate|price|offer(?:ing)?|comp(?:ensation)?|salary|fee)\b", re.I)

# "100k views", "4k video", "1080p" — numbers that are not money
_FALSE_MONEY = re.compile(r"\b\d+\s?(?:k)?\s?(?:views?|subs?|subscribers?|followers?|words?|px|p\b|fps|gb|mb|hours?|days?|weeks?|months?)\b", re.I)


def find_budget(text: str) -> dict:
    """Return {'raw': '$500', 'hourly': bool, 'stated': bool}."""
    if not text:
        return {"raw": "", "hourly": False, "stated": False}

    for pat in _BUDGET_PATTERNS:
        for m in pat.finditer(text):
            raw = m.group(0).strip(" .,;:")
            window = text[max(0, m.start() - 40): m.end() + 40]
            if _FALSE_MONEY.search(raw):
                continue
            # a bare number counts only when a money word sits next to it
            if not re.search(_CUR, raw) and not _BUDGET_WORD.search(window):
                continue
            return {
                "raw": re.sub(r"\s+", " ", raw),
                "hourly": bool(_HOURLY.search(window)),
                "stated": True,
            }

    if _BUDGET_WORD.search(text):
        return {"raw": "", "hourly": bool(_HOURLY.search(text)), "stated": False}
    return {"raw": "", "hourly": False, "stated": False}


# --- contact --------------------------------------------------------------

_EMAIL = re.compile(r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}", re.I)
_TELEGRAM = re.compile(r"(?:t\.me/|telegram[:\s@]+)([a-z0-9_]{4,})", re.I)
_DISCORD = re.compile(r"discord[:\s]*([a-z0-9._#]{3,})", re.I)
_DM = re.compile(r"\b(dm|pm|message|msg|chat|reach out|contact)\s?(me|us)?\b", re.I)
_APPLY_LINK = re.compile(r"https?://(?:www\.)?(?:forms\.gle|docs\.google\.com/forms|airtable\.com|typeform\.com|calendly\.com)\S*", re.I)


def find_contact(text: str) -> dict:
    """Find how to reach the poster. Email beats telegram beats form beats DM."""
    out = {"kind": "", "value": ""}
    if not text:
        return out

    m = _EMAIL.search(text)
    if m:
        return {"kind": "email", "value": m.group(0)}
    m = _APPLY_LINK.search(text)
    if m:
        return {"kind": "form", "value": m.group(0)}
    m = _TELEGRAM.search(text)
    if m:
        return {"kind": "telegram", "value": "@" + m.group(1)}
    m = _DISCORD.search(text)
    if m:
        return {"kind": "discord", "value": m.group(1)}
    if _DM.search(text):
        return {"kind": "dm", "value": ""}
    return out


# --- category -------------------------------------------------------------

def classify(title: str, body: str, categories: dict) -> dict:
    """Give every lead a category, in two passes.

    Pass 1: whole phrase match ("video editor")  -> weight 3
    Pass 2: single word match ("video", "editor") -> weight 1
    Neither hits -> 'other', with a topic keyword as a hint.

    Return {'category': 'web-dev', 'auto': False, 'topic': 'scraper'}
    """
    blob = " " + f"{title} {title} {body}".lower() + " "   # title counts double
    words = set(re.findall(r"[a-z][a-z+#.]{2,}", blob))
    topic = _topic_hint(title, body)

    scores = {}
    for cat, phrases in categories.items():
        hit = 0
        for phrase in phrases:
            if phrase in blob:
                hit += 3
            else:
                tokens = [t for t in re.split(r"[^a-z+#.]+", phrase) if len(t) > 3]
                hit += sum(1 for t in tokens if t in words)
        if hit:
            scores[cat] = hit

    if scores:
        best = max(scores, key=lambda c: (scores[c], c))
        if scores[best] >= 3:                       # confident match
            return {"category": best, "auto": False, "topic": topic}
        if scores[best] >= 2:                       # word-level guess
            return {"category": best, "auto": True, "topic": topic}

    return {"category": "other", "auto": True, "topic": topic}


# words too generic to describe what the work is
_NOISE = {
    "hiring", "hire", "hired", "need", "needed", "needs", "looking", "look", "want", "wanted",
    "someone", "somebody", "person", "people", "help", "please", "urgent", "asap", "paid",
    "pay", "payment", "budget", "price", "cost", "money", "rate", "hour", "hourly", "week",
    "weekly", "month", "monthly", "year", "day", "daily", "time", "part", "full", "remote",
    "online", "offline", "work", "working", "worker", "job", "jobs", "task", "tasks", "gig",
    "project", "projects", "freelance", "freelancer", "contract", "long", "term", "small",
    "quick", "easy", "simple", "good", "best", "great", "experience", "experienced", "expert",
    "professional", "team", "company", "business", "client", "clients", "start", "starting",
    "available", "apply", "message", "email", "contact", "details", "more", "also", "with",
    "from", "have", "will", "your", "this", "that", "there", "here", "about", "into", "only",
    "usd", "inr", "dollar", "rupees", "and", "the", "for", "you", "our", "who", "can", "must",
    "should", "would", "like", "know", "make", "made", "using", "used", "based", "per",
    "week's", "new", "very", "well", "each", "some", "any", "all", "one", "two", "first",
}


def _topic_hint(title: str, body: str) -> str:
    """One keyword for the card — roughly what the work is about."""
    weights = {}
    for text, weight in ((title, 4), (body[:400], 1)):
        for word in re.findall(r"[a-z][a-z'\-]{3,}", (text or "").lower()):
            word = word.strip("'-")
            if len(word) < 4 or word in _NOISE:
                continue
            weights[word] = weights.get(word, 0) + weight

    if not weights:
        return ""

    top = max(weights, key=lambda w: (weights[w], len(w)))
    if len(top) > 4 and top.endswith("s") and not top.endswith("ss"):
        top = top[:-1]
    return top


# --- misc ----------------------------------------------------------------

_URGENT = re.compile(r"\b(asap|urgent(?:ly)?|immediately|today|right now|by tomorrow|deadline)\b", re.I)
_LONGTERM = re.compile(r"\b(long[\s-]?term|ongoing|monthly|retainer|recurring|full[\s-]?time)\b", re.I)
_REMOTE = re.compile(r"\b(remote|work from home|wfh|anywhere|worldwide|online)\b", re.I)
_ONSITE = re.compile(r"\b(on-?site|in[\s-]person|walk[\s-]?in|must be located|local only|based in)\b", re.I)


def find_flags(text: str) -> list:
    text = text or ""
    flags = []
    if _URGENT.search(text):
        flags.append("urgent")
    if _LONGTERM.search(text):
        flags.append("long-term")
    if _ONSITE.search(text):
        flags.append("onsite")
    elif _REMOTE.search(text):
        flags.append("remote")
    return flags


def score_lead(lead: dict, cfg: dict) -> int:
    """0-100. How much this lead is worth spending time on."""
    from datetime import datetime, timedelta, timezone

    w = cfg["score_weights"]
    blob = f"{lead.get('title','')} {lead.get('body','')}".lower()
    score = 0

    if lead["budget"]["stated"]:
        score += w["budget_stated"]
    if lead["contact"]["kind"] in ("email", "telegram", "form", "discord"):
        score += w["contact_direct"]
    elif lead["contact"]["kind"] == "dm":
        score += w["contact_direct"] // 3
    if lead.get("trust", {}).get("level") == "clean":
        score += w["trust_clean"]
    if any(word in blob for word in cfg["project_words"]):
        score += w["project_words"]

    try:
        posted = datetime.strptime(lead.get("posted_at", ""), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - posted
        if age < timedelta(hours=24):
            score += w["fresh_today"]
        elif age < timedelta(days=3):
            score += w["fresh_today"] // 2
    except (ValueError, TypeError):
        pass

    return min(100, score)


def clean_text(raw: str, limit: int = 700) -> str:
    """Strip HTML tags and entities, normalise whitespace, trim."""
    if not raw:
        return ""
    txt = re.sub(r"<br\s*/?>|</p>|</div>", "\n", raw, flags=re.I)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = html.unescape(txt)
    txt = unicodedata.normalize("NFKC", txt)
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt).strip()
    return txt[:limit].rstrip() + ("…" if len(txt) > limit else "")


def strip_tag(title: str) -> str:
    """'[Hiring] Need a scraper' -> 'Need a scraper'."""
    return re.sub(r"^\s*[\[\(][^\]\)]{1,20}[\]\)]\s*", "", title or "").strip()
