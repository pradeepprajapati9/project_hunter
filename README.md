# Project Hunter

A daily lead scraper for freelancers. It collects **client posts** (people who want work done),
filters out scams, categorises every lead automatically, and shows everything on a local dashboard.

No API keys, no paid services, no database — plain Python and JSON files.

## Quick start

```bash
pip install -r requirements.txt
python hunter.py
```

Then open the dashboard: <http://localhost/pr/project-hunter/site/>
(any static web server works; the path above assumes XAMPP with the project inside `htdocs`)

A full run takes about 4-5 minutes because Reddit rate-limits anonymous feeds.
Messages like `rate limit, 15s ruk kar dubara...` in the console are expected — the script waits and retries.

To run it automatically, point Windows Task Scheduler at `run.bat` (twice a day works well).

## How it works

| Step | What happens |
|---|---|
| 1 | Fetch posts from Reddit RSS feeds (r/forhire, r/slavelabour, r/DoneDirtCheap, r/jobbit, r/HireaWriter) and the monthly Hacker News "Freelancer? Seeking freelancer?" thread |
| 2 | Keep only client posts — "for hire" self-promotion and adult work are rejected |
| 3 | Extract budget, contact channel (email / Telegram / form / DM), category, and flags (urgent, remote, onsite, long-term) |
| 4 | Run the scam filter — fake work never reaches the board |
| 5 | Drop duplicates using post id plus a title fingerprint, remembered for 30 days (this also catches cross-posts) |
| 6 | Score each lead from 0 to 100 |
| 7 | Publish everything above the score threshold to `data/leads.json` for the dashboard |

### Scoring

| Signal | Points |
|---|---|
| Budget stated in the post | +30 |
| Direct contact (email, Telegram, form, Discord) | +15 |
| Scam filter says clean | +20 |
| Project wording (freelance, contract, fixed price, …) | +15 |
| Posted within 24 hours | +20 (half if within 3 days) |

Leads scoring under 25 are dropped. Tune the weights in `config.json`.

## Scam filter

`lib/scam.py` runs 15 weighted rules over each lead:

* **60 points or more → scam.** Dropped from the board, logged to `data/rejected.jsonl`.
* **25 to 59 → suspicious.** Shown with a warning badge.
* **Below 25 → clean.**

What it catches: advance or registration fees, gift-card payment, cheque and money-mule work,
requests for ID / bank details / OTP, fake reviews and paid engagement, exam and assignment
cheating, hacking or verification bypass, MLM and "guaranteed returns" schemes, copy-paste
earning spam, unrealistic pay promises, Telegram-only contact, crypto-only payment,
unpaid or commission-only work, free test tasks, high pay for trivial work, and posts with no
detail at all.

Tested against 18 handcrafted samples (10 scam, 3 suspicious, 5 clean) — all classified correctly.

**Audit trail.** Every dropped lead is written to `data/rejected.jsonl` with the reason and the exact
text that triggered the rule, so a false positive is easy to spot. If a rule is too aggressive,
lower its weight or remove its pattern in `lib/scam.py`.

## Categories

Seventeen categories: web-dev, mobile-app, automation-bot, ai-ml, software-eng, data, design,
writing, translation, video-audio, marketing-seo, va-support, teaching, finance-legal, ecommerce,
field-trade, odd-jobs.

Classification runs in two passes:

1. **Phrase match** — an exact phrase such as "video editor" is a confident match.
2. **Word match** — individual words such as "video" and "editor" produce a best guess.
3. If both fail the lead becomes `other`, with a topic keyword attached as a hint.

To add a category, add its keywords to `categories` in `config.json`. No code changes needed.

## Dashboard

Built with Bootstrap 5 only — no custom CSS. Bootstrap is vendored in `site/vendor/`, so the page
also works offline or behind a CDN-blocking network.

* Stat tiles: live leads, posted today, budget stated, contacted
* Search, category dropdown with counts, and sorting by newest / score / budget
* Filter toggles: budget only, remote only, hide suspicious, hide contacted
* Each card shows the score, category, budget, and flags; "Details" opens the full post in a modal
* "Contacted" marks a lead as handled — stored in the browser via `localStorage`
* Light and dark theme toggle

## Telegram alerts (optional)

Speed matters: on busy subreddits the first few replies get the work, so a phone alert is worth setting up.

Set the credentials as environment variables:

```bash
set TELEGRAM_BOT_TOKEN=123456:abc
set TELEGRAM_CHAT_ID=987654321
python hunter.py
```

Or create `secrets.json` in the project root (it is git-ignored):

```json
{ "telegram_bot_token": "123456:abc", "telegram_chat_id": 987654321 }
```

Without credentials the notifier stays silent — nothing breaks.

## Project layout

```
hunter.py          main runner
config.json        sources, reject list, categories, score weights
lib/extract.py     budget, contact, category, flags, scoring
lib/scam.py        scam rules
lib/store.py       dedupe memory, leads.json, archive, rejected log
lib/net.py         HTTP with retries and rate-limit backoff
lib/notify.py      Telegram alerts (optional)
sources/reddit.py  Reddit RSS parser
sources/hn.py      Hacker News Algolia API
site/              dashboard (Bootstrap only)
data/              generated at runtime, never committed
```

## Data files

Everything under `data/` is git-ignored — scraped posts, author names and contact details stay on
your machine.

| File | Contents |
|---|---|
| `leads.json` | Current board, read by the dashboard |
| `seen.json` | Dedupe memory, 30 days |
| `archive.jsonl` | Every published lead, append-only |
| `rejected.jsonl` | Leads dropped as scams, with reasons |
| `run.log` | Output when started through `run.bat` |

## Known limits

* Reddit's `.json` API returns 403 without registered app credentials, so the public `.rss` feeds are
  used instead. They are rate-limited; the script backs off and retries automatically.
* `freelancer.com`, `remoteok.com` and `arbeitnow.com` failed with TLS errors on the network this was
  built on. They may work elsewhere and can be added as new modules under `sources/`.
* The Hacker News thread is monthly, so it contributes only a handful of leads — but usually good ones.
* The tool finds and ranks leads. Negotiating and closing is still a human job.

## Adding a source

Create a module in `sources/` exposing `NAME` and `fetch(cfg) -> list[dict]`, then add it to
`SOURCES` in `hunter.py`. Each lead dict needs: `id`, `fingerprint`, `source`, `source_detail`,
`title`, `url`, `posted_at` (`%Y-%m-%dT%H:%M:%SZ`), `author`, `body`, `budget`, `contact`,
`category`, `category_auto`, `topic`, `flags`. Use the helpers in `lib/extract.py` so the fields stay
consistent.
