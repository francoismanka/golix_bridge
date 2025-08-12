[GOLIX_RESTART_KIT_V2 — Reprise intégrale]

OBJECTIF
Mon assistant “Trading François” (GPT perso) pilote mon backend **golix-bridge** pour:
- Prix crypto: /binance/price (Binance → fallback Coinpaprika)
- Recherche web: /web/search (Brave/Serper)
- Actus crypto: /rss/crypto
- Sentiment marché: /sentiment
- Mémo: stockage dans Firebase
- Route /chat pour commandes depuis GPT ou Tampermonkey

ÉTAT ACTUEL (OK/KO)
- Render URL: https://golix-bridge.onrender.com
- /ping → {"ok":true,"firebase":true} ✅
- /rss/crypto → OK ✅
- /sentiment → OK ✅
- /web/search → OK si BRAVE_API_KEY est posée (sinon message d’erreur contrôlé)
- /binance/price → doit marcher avec fallback Coinpaprika (aucune 500 attendue) ✅ après code ci-dessous
- GPT “Trading François”: Actions branchées avec header `x-admin-token`

RENDER — CONFIG À AVOIR
Build Command:
  pip install -r requirements.txt
Start Command:
  uvicorn main:app --host 0.0.0.0 --port $PORT

requirements.txt:
  fastapi
  uvicorn
  httpx
  feedparser
  firebase-admin

Procfile:
  web: uvicorn main:app --host 0.0.0.0 --port $PORT

ENV VARS (Render → Settings → Environment) — mettre vos vraies valeurs
  ADMIN_TOKEN              = <long_token_secret>
  FIREBASE_SERVICE_ACCOUNT = { ...JSON complet du compte de service... }
  FIREBASE_STORAGE_BUCKET  = <ex: bot-crypto-xxxx.appspot.com>
  # Optionnels
  BRAVE_API_KEY            = <token Brave>     # /web/search
  SERPER_API_KEY           = <clé Serper>      # alternative web
  OPENAI_API_KEY           = sk-...            # si réponses LLM via /chat
  MODEL_NAME               = gpt-4o-mini
  COINGECKO_API_KEY        = <clé>             # 3e fallback prix (optionnel)

CODE — main.py (colle TOUT)
---------------------------------------------------------
import os, json, time, urllib.parse, math
from datetime import datetime, timedelta
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import httpx, feedparser

# === ENV ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")                 # optionnel
MODEL_NAME     = os.getenv("MODEL_NAME", "gpt-4o-mini")
ADMIN_TOKEN    = os.getenv("ADMIN_TOKEN", "change-me")

BRAVE_API_KEY  = os.getenv("BRAVE_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

FIREBASE_SERVICE_ACCOUNT = os.getenv("FIREBASE_SERVICE_ACCOUNT")
FIREBASE_STORAGE_BUCKET  = os.getenv("FIREBASE_STORAGE_BUCKET")

COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")  # optionnel

app = FastAPI(title="Golix Bridge")

# === Firebase (mémoire; optionnel) ===
firebase_ready = False
try:
    if FIREBASE_SERVICE_ACCOUNT and FIREBASE_STORAGE_BUCKET:
        import firebase_admin
        from firebase_admin import credentials, storage, db
        cred = credentials.Certificate(json.loads(FIREBASE_SERVICE_ACCOUNT))
        firebase_admin.initialize_app(cred, {"storageBucket": FIREBASE_STORAGE_BUCKET})
        firebase_ready = True
except Exception:
    firebase_ready = False

# === Models ===
class ChatIn(BaseModel):
    user_id: str | None = None
    message: str
    context: dict | None = None

# === HTTP helper ===
async def http_get_json(url, headers=None):
    async with httpx.AsyncClient(timeout=30) as cli:
        r = await cli.get(url, headers=headers)
        r.raise_for_status()
        return r.json()

# === LLM (optionnel) ===
async def openai_answer(prompt: str) -> str:
    if not OPENAI_API_KEY:
        return "📝 (OPENAI_API_KEY absent — réponse courte hors LLM)."
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

# === Prix: Binance -> fallback Coinpaprika -> (optionnel) CoinGecko ===
COINPAPRIKA_IDS = {
    "BTC":"btc-bitcoin","ETH":"eth-ethereum","BNB":"bnb-binance-coin","XRP":"xrp-xrp",
    "SOL":"sol-solana","ADA":"ada-cardano","DOGE":"doge-dogecoin","AVAX":"avax-avalanche",
    "DOT":"dot-polkadot","MATIC":"matic-polygon","TRX":"trx-tron","LINK":"link-chainlink",
    "ATOM":"atom-cosmos","OP":"op-optimism","ARB":"arb-arbitrum"
}
COINGECKO_IDS = {"BTC":"bitcoin","ETH":"ethereum","BNB":"binancecoin","XRP":"ripple","SOL":"solana"}

def _split(sym: str):
    s = sym.upper().replace("/", "")
    if s.endswith(("USDT","USDC")): return s[:-4], "USD"
    if s.endswith("USD"): return s[:-3], "USD"
    return s, "USD"

async def safe_price(symbol: str):
    base, _ = _split(symbol)
    pair = f"{base}USDT"
    # 1) Binance
    try:
        data = await http_get_json(f"https://api.binance.com/api/v3/ticker/price?symbol={pair}")
        p = float(data["price"])
        if math.isfinite(p):
            return {"source":"binance","symbol":pair,"price":p}
    except Exception as e:
        binance_err = str(e)
    # 2) Coinpaprika
    try:
        pid = COINPAPRIKA_IDS.get(base)
        if pid:
            data = await http_get_json(f"https://api.coinpaprika.com/v1/tickers/{pid}")
            p = float(data["quotes"]["USD"]["price"])
            return {"source":"coinpaprika","symbol":f"{base}USD","price":p}
    except Exception as e:
        paprika_err = str(e)
    # 3) CoinGecko (si clé)
    if COINGECKO_API_KEY and base in COINGECKO_IDS:
        try:
            headers = {"accept":"application/json","x-cg-api-key": COINGECKO_API_KEY}
            cid = COINGECKO_IDS[base]
            data = await http_get_json(f"https://api.coingecko.com/api/v3/simple/price?ids={cid}&vs_currencies=usd", headers=headers)
            return {"source":"coingecko","symbol":f"{base}USD","price": float(data[cid]["usd"])}
        except Exception:
            pass
    # 4) Jamais 500: retour clair
    return {
        "error": f"Prix indisponible pour {symbol}",
        "binance_error": locals().get("binance_err"),
        "coinpaprika_error": locals().get("paprika_err")
    }

# === Recherche Web ===
async def web_search(query: str):
    q = query.strip()
    if BRAVE_API_KEY:
        headers = {"X-Subscription-Token": BRAVE_API_KEY}
        qs = urllib.parse.quote(q)
        url = f"https://api.search.brave.com/res/v1/web/search?q={qs}&count=5&freshness=pd"
        data = await http_get_json(url, headers=headers)
        items = [{"title": it.get("title"), "url": it.get("url")}
                 for it in data.get("web", {}).get("results", [])]
        return {"engine":"brave", "query": q, "results": items}
    if SERPER_API_KEY:
        headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type":"application/json"}
        body = {"q": q, "num": 5}
        async with httpx.AsyncClient(timeout=30) as cli:
            r = await cli.post("https://google.serper.dev/search", headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
        items = [{"title": it.get("title"), "url": it.get("link")} for it in data.get("organic", [])[:5]]
        return {"engine":"serper", "query": q, "results": items}
    return {"error":"Aucune clé de recherche web (BRAVE_API_KEY ou SERPER_API_KEY)"}

# === RSS + Sentiment ===
CRYPTO_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://www.theblock.co/rss.xml",
    "https://cryptopotato.com/feed/",
    "https://cointelegraph.com/rss",
    "https://www.reuters.com/markets/cryptocurrency/rss"
]
async def rss_crypto_top(n=6):
    items, now = [], time.time()
    for url in CRYPTO_FEEDS:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:4]:
                ts = time.mktime(e.published_parsed) if getattr(e,"published_parsed",None) else now
                items.append({"title": getattr(e,"title","(sans titre)"),
                              "link": getattr(e,"link",""), "published": ts})
        except Exception:
            continue
    items.sort(key=lambda x: x["published"], reverse=True)
    out = []
    for it in items[:n]:
        dt = datetime.utcfromtimestamp(it["published"]).strftime("%Y-%m-%d %H:%M UTC")
        out.append(f"{dt} — {it['title']} ({it['link']})")
    return out

async def fear_greed():
    data = await http_get_json("https://api.alternative.me/fng/?limit=1&format=json")
    v = data.get("data", [{}])[0]
    return {"value": v.get("value"), "classification": v.get("value_classification"),
            "timestamp": v.get("timestamp")}

# === Firebase log (optionnel) ===
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

# === Routes ===
@app.get("/")
async def root(): return {"ok": True, "service": "golix-bridge"}

@app.get("/ping")
async def ping(): return {"ok": True, "firebase": firebase_ready}

@app.get("/binance/price")
async def http_binance_price(symbol: str):
    return await safe_price(symbol)

@app.get("/web/search")
async def http_web_search(q: str):
    return await web_search(q)

@app.get("/rss/crypto")
async def http_rss_crypto():
    return {"top": await rss_crypto_top()}

@app.get("/sentiment")
async def http_sentiment():
    return await fear_greed()

@app.post("/chat")
async def chat(body: ChatIn, x_admin_token: str = Header(None)):
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    msg = (body.message or "").strip()
    if msg.lower().startswith("prix "):
        pair = msg.split(" ", 1)[1].strip()
        out = await safe_price(pair)
        if "error" in out:
            return {"answer": f"Prix indisponible ({out['error']})", "tools_ran":["price"]}
        return {"answer": f"{out['symbol']}: {out['price']:.4f} (src: {out['source']})", "tools_ran":["price"]}
    if msg.lower().startswith("web:"):
        q = msg.split(":", 1)[1].strip()
        out = await web_search(q)
        if "error" in out:
            return {"answer": f"Recherche web désactivée ({out['error']}).", "tools_ran":[]}
        lines = [f"- {r['title']} ({r['url']})" for r in out["results"][:5]]
        return {"answer": "Top résultats :\n" + "\n".join(lines), "tools_ran":["web_search"]}
    if msg.lower() == "actu crypto":
        top = await rss_crypto_top()
        return {"answer": "Dernières actus :\n" + "\n".join(top), "tools_ran":["rss_crypto"]}
    if msg.lower() == "sentiment":
        s = await fear_greed()
        return {"answer": f"Fear&Greed: {s['value']} ({s['classification']})", "tools_ran":["fear_greed"]}
    if msg.lower().startswith("memo:"):
        note = msg.split(":",1)[1].strip()
        res = await firebase_log(note)
        if res.get("ok"):
            return {"answer": f"Mémo enregistré: {res['path']}", "tools_ran":["firebase_log"]}
        else:
            return {"answer": f"Impossible d'enregistrer le mémo ({res.get('error')}).", "tools_ran":[]}
    text = await openai_answer(msg)
    return {"answer": text, "tools_ran":[]}
---------------------------------------------------------

TESTS RAPIDES (navigateur)
  /ping
  /binance/price?symbol=BTCUSDT
  /rss/crypto
  /sentiment
  /web/search?q=bitcoin   (si BRAVE_API_KEY posée)

GPT “Trading François” — Actions (OpenAPI)
Colle ce YAML dans l’éditeur GPT → Actions → Import:
---------------------------------------------------------
openapi: 3.1.0
info:
  title: Golix Bridge Actions
  version: '1.0'
servers:
  - url: https://golix-bridge.onrender.com
paths:
  /binance/price:
    get:
      operationId: binance_price
      summary: Prix spot d'une paire (Binance → fallback Coinpaprika)
      parameters:
        - in: query
          name: symbol
          required: true
          schema: { type: string, example: BTCUSDT }
  /web/search:
    get:
      operationId: web_search
      parameters:
        - in: query
          name: q
          required: true
          schema: { type: string, example: bitcoin regulation }
  /rss/crypto:
    get:
      operationId: rss_crypto
  /sentiment:
    get:
      operationId: sentiment_fng
  /chat:
    post:
      operationId: router_chat
      security: [ { adminToken: [] } ]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                user_id: { type: string, example: francois }
                message:  { type: string, example: "prix BTCUSDT" }
components:
  securitySchemes:
    adminToken:
      type: apiKey
      in: header
      name: x-admin-token
---------------------------------------------------------

GPT — Auth de l’Action
  Type: Clé API  → Personnalisé
  Header name: x-admin-token
  Value: <ADMIN_TOKEN exact de Render>

COMMANDES À UTILISER (dans le GPT)
  prix BTCUSDT
  web: bitcoin regulation
  actu crypto
  sentiment
  memo: idée de test

DÉPANNAGE EXPRESS
- /ping = firebase:false → vérifier FIREBASE_SERVICE_ACCOUNT (JSON complet) + FIREBASE_STORAGE_BUCKET, redeploy
- Actions GPT “Regeneration must have conversation_id” → fermer l’éditeur, nouveau chat, ou ré-enregistrer l’auth
- Prix renvoie {error:…} → copie le JSON et corrigeons la cause (réseau/ratelimit). Le service ne renverra plus 500.

[FIN GOLIX_RESTART_KIT_V2]
