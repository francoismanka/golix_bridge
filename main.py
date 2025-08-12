import os, json, time, urllib.parse
from datetime import datetime
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import httpx, feedparser

# --- ENV ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")          # optionnel (si tu veux zéro coût, laisse vide)
MODEL_NAME     = os.getenv("MODEL_NAME", "gpt-4o-mini")
ADMIN_TOKEN    = os.getenv("ADMIN_TOKEN", "change-me")

BRAVE_API_KEY  = os.getenv("BRAVE_API_KEY")           # pour recherche web gratuite
SERPER_API_KEY = os.getenv("SERPER_API_KEY")          # alternative à Brave (facultatif)

FIREBASE_SERVICE_ACCOUNT = os.getenv("FIREBASE_SERVICE_ACCOUNT")  # JSON complet
FIREBASE_STORAGE_BUCKET  = os.getenv("FIREBASE_STORAGE_BUCKET")   # ex: ton-projet.appspot.com

BINANCE_API_KEY    = os.getenv("BINANCE_API_KEY")     # pas utilisé pour le MVP
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")  # pas utilisé pour le MVP

app = FastAPI(title="Golix Bridge")

# --- Firebase (mémoire) ---
firebase_ready = False
try:
    if FIREBASE_SERVICE_ACCOUNT and FIREBASE_STORAGE_BUCKET:
        import firebase_admin
        from firebase_admin import credentials, storage
        cred = credentials.Certificate(json.loads(FIREBASE_SERVICE_ACCOUNT))
        firebase_admin.initialize_app(cred, {"storageBucket": FIREBASE_STORAGE_BUCKET})
        firebase_ready = True
except Exception as e:
    firebase_ready = False

# --- Modèles de données ---
class ChatIn(BaseModel):
    user_id: str | None = None
    message: str
    context: dict | None = None

# --- Helpers HTTP & OpenAI ---
async def http_get_json(url, headers=None):
    async with httpx.AsyncClient(timeout=30) as cli:
        r = await cli.get(url, headers=headers)
        r.raise_for_status()
        return r.json()

async def openai_answer(prompt: str) -> str:
    if not OPENAI_API_KEY:
        return "📝 (Pas d'OPENAI_API_KEY — réponse générée sans LLM)."
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    payload = {
        "model": MODEL_NAME,
        "temperature": 0.2,
        "messages": [
            {"role":"system","content":"Réponds brièvement et clairement."},
            {"role":"user","content": prompt}
        ],
    }
    async with httpx.AsyncClient(timeout=60) as cli:
        r = await cli.post(url, headers=headers, json=payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

# --- Outils gratuits ---
async def binance_price(symbol: str):
    s = symbol.upper().replace("/", "")
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={s}"
    data = await http_get_json(url)
    return {"symbol": s, "price": float(data["price"])}

async def web_search(query: str):
    # Priorité Brave (gratuit). Sinon Serper si dispo. Sinon message d’erreur.
    q = query.strip()
    if BRAVE_API_KEY:
        headers = {"X-Subscription-Token": BRAVE_API_KEY}
        qs = urllib.parse.quote(q)
        url = f"https://api.search.brave.com/res/v1/web/search?q={qs}&count=5&freshness=pd"
        data = await http_get_json(url, headers=headers)
        items = []
        for it in data.get("web", {}).get("results", []):
            items.append({"title": it.get("title"), "url": it.get("url")})
        return {"engine":"brave", "query": q, "results": items}
    if SERPER_API_KEY:
        headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type":"application/json"}
        body = {"q": q, "num": 5}
        async with httpx.AsyncClient(timeout=30) as cli:
            r = await cli.post("https://google.serper.dev/search", headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
        items = []
        for it in data.get("organic", [])[:5]:
            items.append({"title": it.get("title"), "url": it.get("link")})
        return {"engine":"serper", "query": q, "results": items}
    return {"error":"Aucune clé de recherche web (BRAVE_API_KEY ou SERPER_API_KEY)"}

CRYPTO_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://www.theblock.co/rss.xml",
    "https://cryptopotato.com/feed/",
    "https://cointelegraph.com/rss",
    "https://www.reuters.com/markets/cryptocurrency/rss"
]

async def rss_crypto_top(n=6):
    items = []
    now = time.time()
    for url in CRYPTO_FEEDS:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:4]:
                ts = time.mktime(e.published_parsed) if hasattr(e, "published_parsed") and e.published_parsed else now
                items.append({
                    "title": getattr(e, "title", "(sans titre)"),
                    "link": getattr(e, "link", ""),
                    "published": ts
                })
        except Exception:
            continue
    items.sort(key=lambda x: x["published"], reverse=True)
    out = []
    for it in items[:n]:
        dt = datetime.utcfromtimestamp(it["published"]).strftime("%Y-%m-%d %H:%M UTC")
        out.append(f"{dt} — {it['title']} ({it['link']})")
    return out

async def fear_greed():
    url = "https://api.alternative.me/fng/?limit=1&format=json"
    data = await http_get_json(url)
    v = data.get("data", [{}])[0]
    return {
        "value": v.get("value"),
        "classification": v.get("value_classification"),
        "timestamp": v.get("timestamp")
    }

async def firebase_log(text: str):
    if not firebase_ready:
        return {"ok": False, "error":"Firebase non configuré"}
    from firebase_admin import storage
    bucket = storage.bucket()
    iso = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = f"golix_logs/{iso}.txt"
    blob = bucket.blob(path)
    blob.upload_from_string(text.encode("utf-8"), content_type="text/plain")
    return {"ok": True, "path": path}

# --- Routes HTTP ---
@app.get("/ping")
async def ping(): return {"ok": True, "firebase": firebase_ready}

@app.get("/binance/price")
async def http_binance_price(symbol: str):
    return await binance_price(symbol)

@app.get("/web/search")
async def http_web_search(q: str):
    return await web_search(q)

@app.get("/rss/crypto")
async def http_rss_crypto():
    return {"top": await rss_crypto_top()}

@app.get("/sentiment")
async def http_sentiment():
    return await fear_greed()

# --- Route pilotée par Tampermonkey ---
@app.post("/chat")
async def chat(body: ChatIn, x_admin_token: str = Header(None)):
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    msg = (body.message or "").strip()

    # 1) prix <pair>
    if msg.lower().startswith("prix "):
        symbol = msg.split(" ", 1)[1].strip()
        out = await binance_price(symbol)
        return {"answer": f"{out['symbol']}: {out['price']}", "tools_ran":["binance_price"]}

    # 2) web: <requete>
    if msg.lower().startswith("web:"):
        q = msg.split(":", 1)[1].strip()
        out = await web_search(q)
        if "error" in out:
            return {"answer": f"Recherche web désactivée ({out['error']}).", "tools_ran":[]}
        lines = [f"- {r['title']} ({r['url']})" for r in out["results"][:5]]
        return {"answer": "Top résultats :\n" + "\n".join(lines), "tools_ran":["web_search"]}

    # 3) actu crypto
    if msg.lower() == "actu crypto":
        top = await rss_crypto_top()
        return {"answer": "Dernières actus :\n" + "\n".join(top), "tools_ran":["rss_crypto"]}

    # 4) sentiment
    if msg.lower() == "sentiment":
        s = await fear_greed()
        return {"answer": f"Fear&Greed: {s['value']} ({s['classification']})", "tools_ran":["fear_greed"]}

    # 5) memo: <texte> -> Firebase
    if msg.lower().startswith("memo:"):
        note = msg.split(":",1)[1].strip()
        res = await firebase_log(note)
        if res.get("ok"):
            return {"answer": f"Mémo enregistré: {res['path']}", "tools_ran":["firebase_log"]}
        else:
            return {"answer": f"Impossible d'enregistrer le mémo ({res.get('error')}).", "tools_ran":[]}

    # 6) sinon → petite réponse (OpenAI si dispo)
    text = await openai_answer(msg)
    return {"answer": text, "tools_ran":[]}
