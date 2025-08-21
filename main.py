from fastapi import FastAPI
from utils.binance_client import get_binance_price, place_order
from config.settings import ADMIN_TOKEN

app = FastAPI()

@app.get("/ping")
def ping():
    return {"ok": True}

@app.get("/binance/price")
def price(symbol: str):
    return get_binance_price(symbol)

@app.post("/binance/order")
def order(symbol: str, side: str, quantity: float, token: str):
    if token != ADMIN_TOKEN:
        return {"error": "Unauthorized"}
    return place_order(symbol, side, quantity)
