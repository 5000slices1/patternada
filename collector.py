# ================= DATA COLLECTION + STORAGE (SQLite) =================
import os, time, sqlite3, logging, requests
from contextlib import contextmanager
import pandas as pd
from config import *

log = logging.getLogger("collector")
session = requests.Session()

@contextmanager
def db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    try:
        yield con
        con.commit()
    finally:
        con.close()

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS candles(
            symbol TEXT, open_time INTEGER, open REAL, high REAL, low REAL,
            close REAL, volume REAL, quote_volume REAL,
            PRIMARY KEY(symbol, open_time));
        CREATE TABLE IF NOT EXISTS signal_history(
            symbol TEXT, asof INTEGER, generated_at TEXT, price REAL, score REAL,
            action TEXT, situation TEXT, p_up_4h REAL,
            short_score REAL, short_action TEXT, p_dn_4h REAL,
            PRIMARY KEY(symbol, asof));
        """)
        # migrate databases created by the long-only version
        have = {r[1] for r in con.execute("PRAGMA table_info(signal_history)")}
        for col_, typ in [("short_score", "REAL"), ("short_action", "TEXT"), ("p_dn_4h", "REAL")]:
            if col_ not in have: con.execute(f"ALTER TABLE signal_history ADD COLUMN {col_} {typ}")

def _get(path, params=None):
    for _ in range(5):
        r = session.get(FAPI_URL + path, params=params, timeout=20)
        if r.status_code == 429:
            try: wait = int(r.headers.get("Retry-After", 15))
            except ValueError: wait = 15
            log.warning(f"Rate limited, sleeping {wait}s"); time.sleep(wait); continue
        if r.status_code == 418:
            raise RuntimeError("Binance temporarily banned this IP (418). Wait a while and rerun.")
        r.raise_for_status()
        if int(r.headers.get("x-mbx-used-weight-1m", 0)) > 2000:
            time.sleep(20)
        return r.json()
    raise RuntimeError(f"Too many retries for {path}")

def get_symbols():
    info = _get("/fapi/v1/exchangeInfo")
    ok = {s["symbol"]: s["baseAsset"] for s in info["symbols"]
          if s["contractType"] == "PERPETUAL" and s["quoteAsset"] == "USDT" and s["status"] == "TRADING"}
    rows = []
    for t in _get("/fapi/v1/ticker/24hr"):
        s = t["symbol"]; v = float(t["quoteVolume"])
        if s in ok and s not in STABLES and v >= MIN_24H_QUOTE_VOLUME:
            rows.append({"symbol": s, "base": ok[s], "volume_24h": v})
    rows.sort(key=lambda x: -x["volume_24h"])
    return rows[:TOP_N_SYMBOLS]

def get_live_prices():
    return {d["symbol"]: float(d["price"]) for d in _get("/fapi/v1/ticker/price")}

def sync_symbol(sym):
    """Download only the candles we don't have yet. Returns number of new candles."""
    now = int(time.time() * 1000)
    with db() as con:
        last = con.execute("SELECT MAX(open_time) FROM candles WHERE symbol=?", (sym,)).fetchone()[0]
    if last is not None and now < last + 2 * CANDLE_MS:
        return 0                                   # no new closed candle yet
    start = now - HISTORY_DAYS * 86_400_000 if last is None else last + CANDLE_MS
    rows = []
    while start < now:
        data = _get("/fapi/v1/klines", {"symbol": sym, "interval": INTERVAL,
                                         "startTime": start, "limit": 1500})
        if not data: break
        rows += [(sym, int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]),
                  float(k[5]), float(k[7])) for k in data if int(k[6]) < now]   # closed candles only
        start = int(data[-1][0]) + CANDLE_MS
        time.sleep(REQUEST_DELAY)
        if len(data) < 1500: break
    if rows:
        with db() as con:
            con.executemany("INSERT OR REPLACE INTO candles VALUES (?,?,?,?,?,?,?,?)", rows)
    return len(rows)

def prune():
    cutoff = int(time.time() * 1000) - (HISTORY_DAYS + 10) * 86_400_000
    with db() as con:
        con.execute("DELETE FROM candles WHERE open_time < ?", (cutoff,))

def load_candles(sym):
    q = ("SELECT open_time,open,high,low,close,volume,quote_volume "
         "FROM candles WHERE symbol=? ORDER BY open_time")
    with db() as con:
        df = pd.read_sql(q, con, params=(sym,))
    df.index = pd.to_datetime(df.pop("open_time"), unit="ms")
    return df