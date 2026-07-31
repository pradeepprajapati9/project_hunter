"""Filter that catches fake and scam leads.

Every rule carries a weight. The total decides the level:
    >= 60  scam        (kept off the board)
    >= 25  suspicious  (shown with a warning badge)
    else   clean
"""

import re

# (weight, reason, pattern)
RULES = [
    # --- money asked upfront: always a scam ---
    (60, "asks for an advance fee",
     r"\b(registration|joining|training|onboarding|security|application)\s+fee\b"
     r"|\bpay\s+(?:a\s+)?(?:deposit|fee|upfront|in advance)\b"
     r"|\bupfront\s+payment\s+(?:required|needed)\b"
     r"|\bbuy\s+(?:your own\s+)?(?:equipment|software|kit)\s+first\b"),

    (60, "payment in gift cards or vouchers",
     r"\bgift\s?cards?\b|\bsteam\s?cards?\b|\bitunes\s?cards?\b|\bgoogle play cards?\b"),

    (60, "money mule / cheque scam",
     r"\bcash(?:ing)?\s+(?:a\s+)?che(?:ck|que)\b|\bdeposit\s+(?:this|the)\s+che(?:ck|que)\b"
     r"|\breship(?:ping)?\b|\breceive\s+(?:and forward\s+)?packages?\b"
     r"|\bwestern union\b|\bmoney\s?gram\b|\bmoney transfer agent\b"
     r"|\buse\s+your\s+(?:own\s+)?bank\s+account\b|\bbank\s+account\s+(?:rent|lend)\b"),

    (60, "asks for ID, bank details or OTP",
     r"\baadha?ar\b|\bpan\s?card\b|\bssn\b|\bsocial security number\b"
     r"|\bselfie\s+with\s+(?:your\s+)?id\b|\bid\s?proof\b"
     r"|\b(?:share|send)\s+your\s+(?:bank|account)\s+details\b|\botp\b"
     r"|\byour\s+(?:sim|phone number)\s+for\s+verification\b"),

    # --- the work itself is fake or illegal ---
    (60, "fake reviews or fake engagement",
     r"\bfake\s+(?:reviews?|accounts?|profiles?|traffic|followers?)\b"
     r"|\b(?:write|post|leave)\s+(?:a\s+)?(?:5|five)[\s-]?star\s+reviews?\b"
     r"|\bupvotes?\s+for\s+(?:money|pay)\b|\bvote\s+manipulation\b"
     r"|\bcaptcha\s+(?:farm|solving)\b|\bclick\s?farm\b"
     r"|\bcreate\s+(?:multiple|bulk|verified)\s+accounts?\b"),

    (60, "exam / assignment cheating",
     r"\b(?:take|write|sit|do)\s+my\s+(?:exam|test|quiz|assignment|online class)\b"
     r"|\bexam\s+(?:proxy|helper)\b|\blogin\s+as\s+me\s+for\s+(?:class|exam)\b"
     r"|\bimpersonate\b|\bpretend\s+to\s+be\s+me\b"),

    (60, "hacking or verification bypass",
     r"\bhack(?:ing)?\s+(?:into|account|instagram|facebook|whatsapp|phone)\b"
     r"|\bbypass\s+(?:verification|kyc|otp|2fa|paywall|ban)\b"
     r"|\bcarding\b|\bcc\s+dumps?\b|\bphishing\b|\bddos\b|\bspoof(?:ing)?\s+(?:caller|sms)\b"
     r"|\bcrack(?:ed)?\s+(?:license|software)\b"),

    (60, "MLM / investment scheme",
     r"\bmlm\b|\bnetwork marketing\b|\bdownline\b|\brecruit\s+(?:others|more people)\b"
     r"|\bjoin\s+my\s+team\s+and\s+earn\b|\bpassive income opportunity\b"
     r"|\bforex\s+signals?\b|\bguaranteed\s+(?:returns?|profit)\b|\bdouble\s+your\s+money\b"
     r"|\bbinary options\b|\bhyip\b"),

    # --- classic fake job posting patterns ---
    (60, "paying for engagement (comments, likes, follows, votes)",
     # "paid per comment", "$2 for each review" — a rate per engagement
     r"\b(?:pay|paid|paying|\$\s?\d+)\s+(?:per|for each|for every|each|a)\s+"
     r"(?:comment|like|upvote|follow(?:er)?|subscriber?|review|vote|rating|share)s?\b"
     # "upvote my listing", "subscribe to our channel" — engagement on a commercial page
     # (note: plain "comment on this post" is excluded — that is how people apply on Reddit)
     r"|\b(?:like|upvote|subscribe|follow|vote|rate)\w*\s+(?:on\s+|for\s+|to\s+)?(?:my|mine|our|this)\b"
     r"[^.\n]{0,40}\b(?:listing|channel|profile|product|store|app|business)s?\b"
     r"|\bboost\s+(?:my|our)\s+(?:post|engagement|ranking|rating)\b"
     r"|\b(?:need|want|looking for)\s+\d+\s+(?:upvotes?|likes?|followers?|reviews?|ratings?)\b"),

    (60, "copy-paste weekly earning recruitment spam",
     r"\burgent\s+recruitment\b"
     r"|\bearn\s+up\s+to\s+\$?\d+[^.\n]{0,30}\b(?:weekly|per week|daily|per day)\b"
     r"|\b(?:simple|easy)\s+copy\s?(?:&|and|-)?\s?paste\b"
     r"|\bdata entry\s+(?:job\s+)?from home[^.\n]{0,30}\bno experience\b"
     r"|\bwork from home\s+(?:job\s+)?(?:with\s+)?daily payment\b"),

    (35, "unrealistic earning promise",
     r"\bearn\s+\$?\d{3,}\s*(?:\+|plus)?\s*(?:per|/|a)\s?day\b"
     r"|\b\$\d{3,}\s*(?:per|/|a)\s?day\b|\beasy money\b|\bunlimited earning\b"
     r"|\bno experience (?:needed|required)[^.]{0,40}\$\d{3,}\b"
     r"|\bwork\s+(?:just\s+)?\d\s?hours?\s+(?:a|per)\s?day[^.]{0,30}\$\d{3,}\b"),

    (30, "contact only through Telegram or WhatsApp",
     r"\b(?:text|message|dm|contact)\s+me\s+on\s+(?:telegram|whatsapp)\s+only\b"
     r"|\btelegram\s+only\b|\bwhatsapp\s+only\b"),

    (30, "classic 'personal assistant' scam",
     r"\bpersonal\s+assistant\b(?=[\s\S]{0,300}\b(?:che(?:ck|que)|errands?|deposit|weekly\s+\$)\b)"),

    (25, "crypto-only payment",
     r"\b(?:paid|payment|pay)\s+(?:in|via|with)\s+(?:usdt|btc|bitcoin|eth|crypto)\b"
     r"|\bcrypto\s+wallet\s+(?:address\s+)?(?:required|needed)\b"),

    (25, "anonymous or dark-web framing",
     r"\bno questions asked\b|\bdiscreet\s+(?:work|job)\b|\buntraceable\b"
     r"|\bburner\s+(?:account|phone)\b|\bfake\s+(?:id|documents?|certificates?)\b"),
]

_COMPILED = [(w, reason, re.compile(pat, re.I)) for w, reason, pat in RULES]

# no money involved — not a scam, but not worth the time either
_UNPAID = re.compile(
    r"\b(?:unpaid|no pay|non-?paying|for exposure|for free|volunteer)\b"
    r"|\bcommission\s?only\b|\brev(?:enue)?\s?share\s+only\b|\bequity\s+only\b"
    r"|\bportfolio\s+(?:work|building)\s+only\b|\bunpaid\s+(?:trial|test|internship)\b",
    re.I,
)

_FREE_TEST = re.compile(r"\b(?:free|unpaid)\s+(?:test|trial|sample)\s+(?:task|work|project)\b", re.I)

# trivial work with a large payout is a red flag
_EASY_TASK = re.compile(r"\b(?:data entry|typing|survey|copy paste|copy-paste|chat(?:ting)? support|form filling|simple task)\b", re.I)


def check(lead: dict) -> dict:
    """Return {'level': 'clean|suspicious|scam', 'points': int, 'reasons': [...]}."""
    blob = f"{lead.get('title', '')}\n{lead.get('body', '')}"
    points, reasons = 0, []

    matched = []
    for weight, reason, pattern in _COMPILED:
        m = pattern.search(blob)
        if m:
            points += weight
            reasons.append(reason)
            matched.append(m.group(0)[:60])

    if _UNPAID.search(blob):
        points += 20
        reasons.append("unpaid or commission-only work")

    if _FREE_TEST.search(blob):
        points += 20
        reasons.append("asks for a free test task first")

    # trivial work with a large payout
    if _EASY_TASK.search(blob) and _big_money(lead):
        points += 30
        reasons.append("payout too high for the work described")

    # no budget, no details, no contact
    if len(lead.get("body", "")) < 60 and not lead["budget"]["stated"] and not lead["contact"]["kind"]:
        points += 25
        reasons.append("no details at all — no budget, no contact")

    level = "scam" if points >= 60 else "suspicious" if points >= 25 else "clean"
    return {"level": level, "points": min(100, points), "reasons": reasons[:4], "matched": matched[:4]}


def _big_money(lead: dict) -> bool:
    """True when the budget is $300 or more (₹25,000 or more)."""
    if not lead["budget"]["stated"]:
        return False
    raw = lead["budget"]["raw"]
    nums = [float(n.replace(",", "").replace(" ", "")) for n in re.findall(r"\d[\d,\s]*(?:\.\d+)?", raw)]
    if not nums:
        return False
    top = max(nums)
    if lead["budget"]["hourly"]:
        return top >= 60
    if re.search(r"₹|rs\.?|inr", raw, re.I):
        return top >= 25000
    return top >= 300
