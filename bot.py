# ================= BOT: collect -> analyze -> store =================
# Run:  python bot.py           (loops forever, refresh every REFRESH_MINUTES)
#       python bot.py --once    (single run)
import sys, time, logging
from datetime import datetime, timezone
import pandas as pd
import collector as col, analyzer as an
from config import *

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")
log = logging.getLogger("bot")

def run_cycle():
    syms = col.get_symbols(); live = col.get_live_prices()
    log.info(f"Tracking {len(syms)} symbols. Syncing candles (first run takes a few minutes)...")
    for i, s in enumerate(syms, 1):
        try:
            col.sync_symbol(s["symbol"])
        except RuntimeError as e:
            log.error(e); return
        except Exception as e:
            log.warning(f"{s['symbol']}: sync failed ({e})")
        if i % 10 == 0: log.info(f"  synced {i}/{len(syms)}")
    rows = []
    for s in syms:
        res = an.analyze_symbol(s["symbol"], s["base"], col.load_candles(s["symbol"]))
        if res:
            res["volume_24h"] = s["volume_24h"]
            res["live_price"] = live.get(s["symbol"], res["price"])
            rows.append(res)
    if not rows:
        log.warning("Nothing analysed."); return
    sig = pd.DataFrame(rows)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    sig["generated_at"] = now
    with col.db() as con:
        sig.to_sql("signals", con, if_exists="replace", index=False)
        nz = lambda x: None if x is None or pd.isna(x) else float(x)
        con.executemany("INSERT OR IGNORE INTO signal_history (symbol,asof,generated_at,price,score,action,"
            "situation,p_up_4h,short_score,short_action,p_dn_4h) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [(r.symbol, int(r.asof), now, r.price, r.long_score, r.long_action, r.situation,
              nz(getattr(r, "an_p_up_4h", None)), r.short_score, r.short_action,
              nz(getattr(r, "an_p_dn_4h", None))) for r in sig.itertuples()])
    col.prune()
    log.info(f"Saved {len(sig)} signals.")
    log.info("Top 5 LONG ideas:")
    for r in sig.sort_values("long_score", ascending=False).head(5).itertuples():
        log.info(f"  {r.base:<8} {r.long_score:5.1f}  {r.long_action:<15} {r.headline}")
    log.info("Top 5 SHORT ideas:")
    for r in sig.sort_values("short_score", ascending=False).head(5).itertuples():
        log.info(f"  {r.base:<8} {r.short_score:5.1f}  {r.short_action:<15} {r.headline}")

if __name__ == "__main__":
    col.init_db()
    try:
        while True:
            run_cycle()
            if "--once" in sys.argv: break
            log.info(f"Sleeping {REFRESH_MINUTES} min...")
            time.sleep(REFRESH_MINUTES * 60)
    except KeyboardInterrupt:
        log.info("Stopped.")