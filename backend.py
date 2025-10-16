from fastapi import FastAPI, HTTPException
from datetime import datetime, timedelta
import yfinance as yf
from typing import Dict, Any

app = FastAPI()

CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_MINUTES = 15


def get_current_quarter_timestamp():
    now = datetime.utcnow().replace(second=0, microsecond=0)
    quarter = now.minute // 15 * 15
    return now.replace(minute=quarter)


def fetch_stock_data(ticker: str):
    t = yf.Ticker(ticker)
    info = t.fast_info
    price = info["last_price"]
    history = t.history(period="max")

    now = datetime.utcnow()

    ranges = {
        "1w": history.last("7D"),
        "1m": history.last("30D"),
        "3m": history.last("90D"),
        "ytd": history[history.index >= datetime(now.year, 1, 1)],
        "1y": history.last("365D"),
        "3y": history.last("1095D"),
        "5y": history.last("1825D"),
        "max": history,
    }

    return {
        "ticker": ticker.upper(),
        "last_updated": now.isoformat(),
        "price": price,
        "historical": {
            key: [{"date": str(d.date()), "close": float(v)} for d, v in val["Close"].items()]
            for key, val in ranges.items()
        }
    }


@app.get("/stock")
def get_stock(ticker: str):
    ticker = ticker.upper()
    now_quarter = get_current_quarter_timestamp()

    cached = CACHE.get(ticker)
    if cached and cached["quarter"] == now_quarter:
        return cached["data"]

    try:
        data = fetch_stock_data(ticker)
        CACHE[ticker] = {"data": data, "quarter": now_quarter}
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
