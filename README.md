# Golix Bridge

Bridge FastAPI pour interagir avec Binance via Render.

## Endpoints
- `/ping` → Test si le service tourne
- `/binance/price?symbol=BTCUSDT` → Prix en temps réel
- `/binance/order` → Placer un ordre (POST)

## Déploiement
- Variables Render nécessaires :
  - `BINANCE_API_KEY`
  - `BINANCE_API_SECRET`
  - `BINANCE_BASE_URL` = https://api.binance.com
  - `ADMIN_TOKEN`
