"""Telegram alerts — new high-scoring leads pushed straight to a phone.

Credentials come from the environment (or secrets.json), never from config.json:
    set TELEGRAM_BOT_TOKEN=123:abc
    set TELEGRAM_CHAT_ID=987654
"""

import html
import json
import os

import requests

SECRETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "secrets.json")
API = "https://api.telegram.org/bot{token}/sendMessage"


def _creds():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("TELEGRAM_CHAT_ID", "")
    if token and chat:
        return token, chat
    try:
        with open(SECRETS, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("telegram_bot_token", ""), str(data.get("telegram_chat_id", ""))
    except (OSError, ValueError):
        return "", ""


def send_leads(leads: list, top: int = 8) -> bool:
    """Send the best leads to Telegram. Skips silently when credentials are missing."""
    token, chat = _creds()
    if not token or not chat:
        return False
    if not leads:
        return False

    best = sorted(leads, key=lambda l: -(l.get("score") or 0))[:top]
    lines = [f"<b>{len(leads)} new project leads</b>", ""]
    for l in best:
        money = l["budget"]["raw"] + ("/hr" if l["budget"]["hourly"] else "") if l["budget"]["stated"] else "budget ?"
        lines.append(
            f"[{l.get('score', 0)}] <b>{html.escape(l['title'][:90])}</b>\n"
            f"{html.escape(money)} · {l['category']} · {html.escape(l['source_detail'])}\n"
            f"{l['url']}\n"
        )
    if len(leads) > top:
        lines.append(f"+{len(leads) - top} more on the dashboard.")

    try:
        resp = requests.post(
            API.format(token=token),
            json={
                "chat_id": chat,
                "text": "\n".join(lines)[:4000],
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=20,
        )
        resp.raise_for_status()
        return True
    except requests.RequestException as err:
        print(f"  ! telegram alert failed: {type(err).__name__}")
        return False
