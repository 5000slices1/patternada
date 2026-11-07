# ================= PATTERN RADAR - SETTINGS =================
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "data", "market.db")   # SQLite file (created automatically)

FAPI_URL   = "https://fapi.binance.com"   # public endpoints only - NO API KEY needed
INTERVAL   = "1h"
CANDLE_MS  = 3_600_000
HISTORY_DAYS = 180                        # ~6 months of candles

# Universe
TOP_N_SYMBOLS        = 200                # top N USDT perpetuals by 24h volume
MIN_24H_QUOTE_VOLUME = 5_000_000          # ignore illiquid coins
STABLES = {"USDCUSDT", "FDUSDUSDT", "TUSDUSDT", "USDPUSDT", "DAIUSDT", "USDSUSDT", "BUSDUSDT"}

# Bot loop
REFRESH_MINUTES = 10
REQUEST_DELAY   = 0.5                     # seconds between kline requests (rate-limit safety)

# Analysis
HORIZONS       = [1, 4, 24]               # forecast horizons in hours
PATTERN_WINDOW = 24                       # hours of price action used for pattern matching
PATTERN_K      = 40                       # number of most-similar past situations
MIN_GAP        = 6                        # min hours between matched situations (avoid duplicates)
WIN_THRESHOLD  = 0.002                    # +0.2% counts as a "win" (covers fees)
EVENT_HOURS    = 4                        # pump/dump measured over 4h
EVENT_Z        = 2.5                      # move must be 2.5x the coin's normal 4h volatility
MIN_EVENT_MOVE = 0.03                     # ...and at least 3%
MIN_CANDLES    = 800                      # skip coins with too little history