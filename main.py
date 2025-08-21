import os, time, hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

import httpx, feedparser
from fastapi import FastAPI, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN_WEBPULSE", "change_me")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY", "")  # optionnel

SOURCES = [
    # RSS crypto fiables (sans clé)
    ("CoinDesk",       "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("CoinTelegraph",  "https://cointelegraph.com/rss"),
    ("TheBlock",       "https://www.theblock.co/rss"),
    ("BinanceBlog",    "https://www.binance.com/en/blog/rss"),
    ("Decrypt",        "https://decrypt.co/feed")
]

KEYWORDS_BULL = ["etf approved","partnership","mainnet","integration","upgrade","bull","rally","breakout","funding secured","listing"]
KEYWORDS_BEAR = ["hack","exploit","ban","lawsuit","sec sues","delist","halt","freeze","leveraged liquidation","outage","security incident"]

app = FastAPI(title="WebPulse (Realtime Web Intel)", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

def _auth(x_admin_token: Optional[str]):
    if not x_admin_token or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(401, "Unauthorized")

def _ts(dt: datetime) -> int:
    return int(dt.replace(tzinfo=timezone.utc).timestamp()*1000)

def _simple_sentiment(text: str) -> float:
    t = (text or "").lower()
    score = 0
    for k in KEYWORDS_BULL:
        if k in t: score += 1
    for k in KEYWORDS_BEAR:
        if k in t: score -= 1
    # clamp -1..1
    return max(-1.0, min(1.0, score/3.0))

@app.get("/ping")
def ping():
    return {"ok": True, "gnews": bool(GNEWS_API_KEY)}

@app.get("/web/news")
def web_news(
    q: str = Query("", description="mots-clés, ex: btc OR bitcoin"),
    since_minutes: int = Query(180, ge=5, le=1440),
    limit: int = Query(30, ge=1, le=100),
    x_admin_token: Optional[str] = Header(None, convert_underscores=False)
):
    _auth(x_admin_token)
    now = datetime.utcnow()
    cutoff = now - timedelta(minutes=since_minutes)
    items: List[Dict[str, Any]] = []

    # RSS sources
    for name, url in SOURCES:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:50]:
                pub = None
                if "published_parsed" in e and e.published_parsed:
                    pub = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
                elif "updated_parsed" in e and e.updated_parsed:
                    pub = datetime(*e.updated_parsed[:6], tzinfo=timezone.utc)
                else:
                    pub = now
                if pub < cutoff: 
                    continue
                title = getattr(e, "title", "")
                summary = getattr(e, "summary", "")
                link = getattr(e, "link", "")
                full = (title + " " + summary).lower()
                if q and q.lower() not in full:
                    continue
                items.append({
                    "source": name,
                    "title": title,
                    "url": link,
                    "published_at": pub.isoformat(),
                    "score": _simple_sentiment(title + " " + summary)
                })
        except Exception:
            continue

    # Optionnel: GNews (si clé fournie)
    if GNEWS_API_KEY and q:
        try:
            # GNews API (ex: gnews.io) format: https://gnews.io/api/v4/search?q=...&token=...
            # Tu peux adapter si tu utilises un autre fournisseur.
            with httpx.Client(timeout=10) as client:
                r = client.get("https://gnews.io/api/v4/search",
                               params={"q": q, "lang":"en", "sortby":"publishedAt", "max": 20, "token": GNEWS_API_KEY})
                if r.status_code == 200:
                    data = r.json().get("articles", [])
                    for a in data:
                        pub = datetime.fromisoformat(a.get("publishedAt","").replace("Z","+00:00"))
                        if pub < cutoff: continue
                        items.append({
                            "source": a.get("source", {}).get("name","GNews"),
                            "title": a.get("title",""),
                            "url": a.get("url",""),
                            "published_at": pub.isoformat(),
                            "score": _simple_sentiment(a.get("title","") + " " + a.get("description",""))
                        })
        except Exception:
            pass

    # Déduplication par (titre+source)
    seen = set()
    deduped = []
    for it in sorted(items, key=lambda x: x["published_at"], reverse=True):
        key = (it["title"].strip().lower(), it["source"])
        if key in seen: 
            continue
        seen.add(key)
        deduped.append(it)
        if len(deduped) >= limit:
            break

    # Score global (moyenne)
    if deduped:
        bias = sum(x["score"] for x in deduped) / len(deduped)
    else:
        bias = 0.0
    return {"count": len(deduped), "bias": bias, "items": deduped}

@app.get("/web/alerts")
def web_alerts(
    symbol: str = Query("BTC"),
    since_minutes: int = Query(60, ge=5, le=1440),
    x_admin_token: Optional[str] = Header(None, convert_underscores=False)
):
    _auth(x_admin_token)
    res = web_news(q=symbol, since_minutes=since_minutes, x_admin_token=x_admin_token)
    alerts = []
    for it in res["items"]:
        t = (it["title"] or "").lower()
        if any(k in t for k in ["hack","exploit","sec","binance halts","delist","ban"]):
            alerts.append(it)
    return {"count": len(alerts), "alerts": alerts}
