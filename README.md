# Project Hunter — Phase 1

Roz internet se **client leads** (jo log kaam karwana chahte hain) uthata hai, duplicate hataata hai,
category-wise score deta hai, aur ek professional dashboard pe live dikhata hai.

## Chalao

```
pip install -r requirements.txt
python hunter.py
```

Dashboard: <http://localhost/pr/project-hunter/site/> (XAMPP Apache chalu hona chahiye)

Roz automatic: Windows Task Scheduler me `run.bat` daal do (din me 2-3 baar — subah/shaam).

## Kya kya hota hai

| Step | Kaam |
|---|---|
| 1 | Reddit RSS (r/forhire, r/slavelabour, r/DoneDirtCheap, r/jobbit, r/HireaWriter) + HN ka monthly "Seeking freelancer" thread se posts uthana |
| 2 | Sirf hiring/client posts rakhna — "for hire" self-promo aur adult kaam reject |
| 3 | Har lead se budget, contact (email/telegram/form/DM), category, urgent/remote/onsite flags nikalna |
| 4 | **Scam check** — 15 rules (neeche), fake kaam board pe nahi aata |
| 5 | Duplicate hataana — post-id + title fingerprint, 30 din ki memory (cross-post bhi pakadta hai) |
| 6 | Score dena (0-100): budget likha hai +30, direct contact +15, trust clean +20, project words +15, aaj ka post +20 |
| 7 | 25 se kam score wale drop, baaki `data/leads.json` me → dashboard |

## Fake kaam ka filter (`lib/scam.py`)

Har lead pe 15 rules chalte hain, points judte hain:
**60+ = scam** (board pe nahi aayega, terminal me `x SCAM` print hoga) · **25-59 = suspicious** (aayega par ⚠ badge ke saath) · **baaki clean**.

Kya pakadta hai: advance/registration fee · gift card se payment · cheque/money-mule kaam ·
Aadhaar/bank/OTP maangna · fake review & paid comment/like/vote · exam-assignment cheating ·
hacking/OTP-bypass · MLM/forex "guaranteed returns" · "copy-paste se weekly earning" spam ·
"earn $500/day" jhoot · sirf-Telegram contact · crypto-only payment · unpaid/commission-only ·
pehle free test task · mamuli kaam pe mota paisa · zero detail wale post.

Testing: 18 nakli leads pe check kiya — 10 scam, 3 suspicious, 5 clean, sab sahi pakde.

**Audit trail:** jo lead scam bola gaya, wo `data/rejected.jsonl` me poora save hota hai (reason +
kaunsa text match hua). Kabhi shaq ho ki acha lead galti se kat gaya, wahi file kholo.
Rule galat lage to `lib/scam.py` me weight kam kar do ya pattern hata do.

## Categorization — har kaam ko, automatically

17 categories (web-dev, mobile-app, automation-bot, ai-ml, software-eng, data, design, writing,
translation, video-audio, marketing-seo, va-support, teaching, finance-legal, ecommerce,
field-trade, odd-jobs). Do pass chalte hain:

1. **Phrase match** ("video editor") → pakka match, normal badge
2. **Word match** ("video", "editor") → andaza, dashed badge + topic hint
3. Dono fail → `other` + topic keyword (57 leads me sirf 1 baar hua)

Nayi category chahiye to bas `config.json` ke `categories` me keywords daal do — code chhune ki zarurat nahi.

## Files

```
hunter.py          main runner
config.json        sources, reject words, categories, score weights
lib/extract.py     budget/contact/category/score nikalna
lib/store.py       dedupe memory + leads.json + archive.jsonl
lib/net.py         HTTP (retry + rate-limit backoff)
lib/notify.py      Telegram alert (optional)
sources/reddit.py  Reddit RSS parser
sources/hn.py      HN Algolia API
site/              dashboard (index.html + style.css + app.js)
data/              leads.json (live), seen.json (dedupe), archive.jsonl (history)
```

## Telegram alert (optional, speed ke liye)

Post ke 5-10 minute andar reply karne wale ko kaam milta hai — isliye phone pe alert.

```
set TELEGRAM_BOT_TOKEN=123456:abc
set TELEGRAM_CHAT_ID=987654321
python hunter.py
```

Ya `secrets.json` bana lo (gitignored):
```json
{ "telegram_bot_token": "123456:abc", "telegram_chat_id": 987654321 }
```

## Dashboard features

- Stats: live leads / aaj ke / budget wale / direct contact / contacted
- Category chips (count ke saath), search, sort (newest / best score / budget first)
- "Budget wale" aur "contacted chhupao" filter
- Har card pe score badge, budget badge, urgent flag, contact channel
- "Mark contacted" button — browser me save hota hai (localStorage), pipeline track karne ke liye

## Notes / limits

- Reddit ka `.json` API ab bina app-credentials **403** deta hai; isliye public `.rss` use kiya hai.
  RSS pe rate limit hai — script khud 15-30s ruk kar retry karta hai, ek run ~3-4 min lagta hai.
- `freelancer.com`, `remoteok.com`, `arbeitnow.com` is network pe SSL-block hain (office WiFi).
  Ghar/hotspot pe test karke `sources/` me add kar sakte hain.
- HN thread mahine me ek baar aata hai — waha se 1-5 leads hi milte hain, par quality high hoti hai.
- Bot deal nahi karta. Wo tumhara kaam hai — bot sirf table pe leads laata hai.
