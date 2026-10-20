"""AI: generated cloud adapter. Deploy one worker; all clients share cached data."""
from datetime import datetime, timezone
from threading import Lock
import logging
import os
import time
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import yfinance as yf
from market import FollowSun, idle, readings, schedule
import pandas as pd

app = FastAPI(title='Market Reactive', docs_url=None, redoc_url=None)
selector = FollowSun()
lock = Lock()
cache = None
cached_at = 0.
frames = {}
# Suppress provider exception bodies; no cookies/credentials appear in app logs.
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

@app.get('/health')
def health():
    return {'status':'ok','schema':1}

@app.get('/v1/market')
def market():
    global cache,cached_at
    now = datetime.now(timezone.utc)
    with lock:
        exchange = selector.select(now)
        key = exchange.code if exchange else ''
        if cache is not None and cache['exchange'] == key and time.monotonic()-cached_at < 60:
            return JSONResponse(cache, headers={'Cache-Control':'no-store'})
        if exchange is None:
            result = idle(now,'closed',next_open=selector.next_open(now))
        else:
            try:
                saved = frames.get(key)
                if saved is None or time.monotonic()-saved[0] >= 300:
                    # No retries or alternate identities to evade provider rate limits.
                    frame = yf.Ticker(exchange.symbol).history(period='1mo',interval='5m',
                        prepost=False,auto_adjust=True,actions=False,timeout=12)
                    daily = yf.Ticker(exchange.symbol).history(period='1mo',interval='1d',
                        auto_adjust=True,actions=False,timeout=12)
                    past = schedule(exchange.calendar,now.date())
                    past = past[past.market_close < pd.Timestamp(now)]
                    previous_close = None
                    if not past.empty and not daily.empty:
                        previous_day = past.index[-1].date()
                        previous = daily[daily.index.date == previous_day]
                        if not previous.empty: previous_close = float(previous.Close.iloc[-1])
                    frames[key] = (time.monotonic(),frame,previous_close)
                result = readings(exchange,now,frames[key][1],frames[key][2])
            except Exception:
                result = idle(now,'unavailable',exchange)
        # Validity is intentionally short even for delayed quotes: detect service failure.
        cache,cached_at = result,time.monotonic()
        return JSONResponse(result,headers={'Cache-Control':'no-store'})
