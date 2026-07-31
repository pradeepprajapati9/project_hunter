"""project-hunter — collect client leads daily, dedupe them, write JSON for the dashboard.

Run:  python hunter.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib import extract, notify, scam  # noqa: E402
from lib.store import Store  # noqa: E402
from sources import hn, reddit  # noqa: E402

SOURCES = [reddit, hn]
CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_config() -> dict:
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    cfg = load_config()
    store = Store(cfg["seen_memory_days"], cfg["live_window_days"])

    scraped = []
    for src in SOURCES:
        print(f"[{src.NAME}]")
        try:
            scraped.extend(src.fetch(cfg))
        except Exception as err:  # one broken source must not stop the rest
            print(f"  ! {src.NAME} crashed: {type(err).__name__}: {err}")

    fresh, weak, scams, shady = [], 0, 0, 0
    for lead in scraped:
        if not store.is_new(lead):
            continue
        store.remember(lead)          # remember rejects too, so they do not return daily

        lead["trust"] = scam.check(lead)
        if lead["trust"]["level"] == "scam":
            scams += 1
            if cfg["drop_scams"]:
                store.reject(lead)
                print(f"  x SCAM: {lead['title'][:52]} -> {lead['trust']['reasons'][0]}")
                print(f"          match: {lead['trust']['matched']}")
                continue
        elif lead["trust"]["level"] == "suspicious":
            shady += 1

        lead["score"] = extract.score_lead(lead, cfg)
        if lead["score"] < cfg["min_score_to_publish"]:
            weak += 1
            continue
        fresh.append(lead)

    store.save_seen()
    payload = store.publish(fresh)
    store.publish_public(payload)   # sanitised copy for GitHub Pages

    print("\n" + "-" * 52)
    print(f"scraped   : {len(scraped)}")
    print(f"new       : {len(fresh)}")
    print(f"dropped   : {len(scraped) - len(fresh) - weak - scams} duplicates, "
          f"{scams} scams, {weak} low score")
    print(f"live board: {payload['total']} leads  ({shady} flagged suspicious)")

    with_budget = sum(1 for l in payload["leads"] if l["budget"]["stated"])
    print(f"budget stated: {with_budget}")

    by_cat = {}
    for lead in payload["leads"]:
        by_cat[lead["category"]] = by_cat.get(lead["category"], 0) + 1
    for cat, n in sorted(by_cat.items(), key=lambda kv: -kv[1]):
        print(f"  {cat:<16} {n}")

    if notify.send_leads(fresh):
        print("telegram alert sent")

    print("-" * 52)
    print("dashboard: http://localhost/pr/project-hunter/site/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
