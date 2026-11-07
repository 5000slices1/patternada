# ================= ANALYSIS ENGINE (read-only: no trading) =================
# Mirrors the "predictive analytics" toolkit from your slide:
#   1. Linear regression      -> trend slope + R2 on log price
#   2. Time-series analysis   -> pump/dump event study, hour-of-day seasonality
#   3. Data mining           -> nearest-neighbour pattern matching on past price action
import numpy as np, pandas as pd
from collections import defaultdict
from numpy.lib.stride_tricks import sliding_window_view
from config import *
import playbook as pb

def fp(x, d=1):
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:+.{d}%}"
def fu(x, d=0):
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{d}%}"

# ---------- helpers ----------
def rsi(close, n=14):
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))

def trend(logp):
    x = np.arange(len(logp))
    k, b = np.polyfit(x, logp, 1)
    fit = k * x + b
    ss_res = ((logp - fit) ** 2).sum(); ss_tot = ((logp - logp.mean()) ** 2).sum()
    return k, (1 - ss_res / ss_tot) if ss_tot > 0 else 0.0

def _dedupe(pos, gap):
    out = []
    for p in pos:
        if not out or p - out[-1] >= gap: out.append(int(p))
    return out

def detect_events(close):
    """Pumps/dumps = 4h move that is >= EVENT_Z x the coin's normal 4h volatility AND >= 3%."""
    r = close.pct_change(EVENT_HOURS)
    sig = r.rolling(720, min_periods=200).std().shift(1)
    z = r / sig
    pump = np.where(((z > EVENT_Z) & (r > MIN_EVENT_MOVE)).values)[0]
    dump = np.where(((z < -EVENT_Z) & (r < -MIN_EVENT_MOVE)).values)[0]
    return _dedupe(pump, EVENT_HOURS), _dedupe(dump, EVENT_HOURS), r

def _event_stats(pos, cv):
    fwd = np.array([cv[p + 4] / cv[p] - 1 for p in pos if p + 4 < len(cv)])
    if len(fwd) == 0: return 0, None, None, None
    return (len(fwd), float(fwd.mean()), float((fwd > WIN_THRESHOLD).mean()),
            float((fwd < -WIN_THRESHOLD).mean()))

def analog(close):
    """Data-mining step: find the K past moments whose last-24h return shape is most similar
    to now, and see what happened next (1h / 4h / 24h)."""
    lp = np.log(close.values.astype(float)); r = np.diff(lp); sd = r.std()
    W, K, H = PATTERN_WINDOW, PATTERN_K, max(HORIZONS)
    if len(r) < W + H + 300 or sd == 0: return None
    X = sliding_window_view(r / sd, W)
    nvalid = len(r) - W - H + 1
    d = np.linalg.norm(X[:nvalid] - X[-1], axis=1)
    pick = []
    for i in np.argsort(d):
        if all(abs(i - j) >= MIN_GAP for j in pick): pick.append(int(i))
        if len(pick) >= K: break
    pick = np.array(pick); end = pick + W - 1
    base = np.arange(nvalid) + W - 1
    res = {"n": len(pick), "avg_dist": float(d[pick].mean()), "fwd": {}}
    for h in HORIZONS:
        f = np.exp(lp[end + 1 + h] - lp[end + 1]) - 1
        allf = np.exp(lp[base + 1 + h] - lp[base + 1]) - 1
        res["fwd"][h] = f
        res[f"p_up_{h}h"] = float((f > WIN_THRESHOLD).mean())
        res[f"med_{h}h"] = float(np.median(f))
        res[f"base_{h}h"] = float((allf > WIN_THRESHOLD).mean())
        res[f"p_dn_{h}h"] = float((f < -WIN_THRESHOLD).mean())
        res[f"base_dn_{h}h"] = float((allf < -WIN_THRESHOLD).mean())
    res["mean_4h"] = float(res["fwd"][4].mean())
    res["q25_4h"], res["q75_4h"] = [float(v) for v in np.percentile(res["fwd"][4], [25, 75])]
    return res

# ---------- classification, scoring, language ----------
def classify(o):
    g = lambda k, d=None: o[k] if o.get(k) is not None else d
    hp, hd = g("hrs_since_pump"), g("hrs_since_dump")
    recent_pump = hp is not None and hp <= 6
    recent_dump = hd is not None and hd <= 24
    overbought = o["rsi"] >= 78 or o["z_7d"] >= 3
    ppn, ppa = g("post_pump_n", 0), g("post_pump_avg", 0)
    r2, slope, z = o["trend_7d_r2"], o["trend_7d"], o["z_7d"]
    if o["dd_30d"] <= -0.30 and o["making_new_lows"] and o["recovery"] < 0.25: return "FALLING_KNIFE"
    if recent_dump and o["making_new_lows"]: return "STILL_DUMPING"
    if recent_pump and overbought and (ppn < 3 or ppa <= 0.005): return "OVEREXTENDED"
    if recent_pump and not overbought and ppn >= 3 and ppa > 0.005 and g("post_pump_win", 0) >= 0.55:
        return "PUMP_MOMENTUM"
    if (o["dd_30d"] <= -0.20 or recent_dump) and not o["making_new_lows"] and o["rsi"] <= 42 \
            and o["bounce_from_low"] > 0.005: return "DUMP_STABILIZING"
    if r2 >= 0.5 and slope > 0 and z <= -0.8: return "UPTREND_PULLBACK"
    if r2 >= 0.5 and slope < 0: return "DOWNTREND_BOUNCE" if z >= 0.8 else "DOWNTREND"
    if g("an_n", 0) >= 25:
        edge_up = o["an_p_up_4h"] - o["an_base_4h"]; edge_dn = o["an_p_dn_4h"] - o["an_base_dn_4h"]
        if o["an_p_up_4h"] >= 0.6 and edge_up >= 0.08: return "PATTERN_BULLISH"
        if o["an_p_dn_4h"] >= 0.6 and edge_dn >= 0.08: return "PATTERN_BEARISH"
    if overbought: return "OVEREXTENDED"
    return "NO_EDGE"

LONG_ADJ  = {"PUMP_MOMENTUM": 8, "UPTREND_PULLBACK": 8, "DUMP_STABILIZING": 6, "PATTERN_BULLISH": 4,
             "NO_EDGE": 0, "PATTERN_BEARISH": -10, "DOWNTREND": -10, "DOWNTREND_BOUNCE": -10,
             "STILL_DUMPING": -15, "OVEREXTENDED": -15, "FALLING_KNIFE": -20}
SHORT_ADJ = {"OVEREXTENDED": 10, "STILL_DUMPING": 8, "DOWNTREND": 8, "DOWNTREND_BOUNCE": 8,
             "PATTERN_BEARISH": 4, "FALLING_KNIFE": 2, "NO_EDGE": 0, "PATTERN_BULLISH": -6,
             "DUMP_STABILIZING": -8, "UPTREND_PULLBACK": -10, "PUMP_MOMENTUM": -12}
LONG_SITS  = {"PUMP_MOMENTUM", "DUMP_STABILIZING", "UPTREND_PULLBACK", "PATTERN_BULLISH"}
SHORT_SITS = {"OVEREXTENDED", "STILL_DUMPING", "DOWNTREND", "DOWNTREND_BOUNCE", "PATTERN_BEARISH", "FALLING_KNIFE"}

def _conf(s, agree, n):
    return "HIGH" if s >= 70 and agree >= 4 and n >= 30 else "MEDIUM" if s >= 58 and agree >= 3 else "LOW"

def score_long(o, sit):
    s = 50.0 + LONG_ADJ[sit]
    if o.get("an_n"):
        s += float(np.clip((o["an_p_up_4h"] - o["an_base_4h"]) * 100, -20, 20))
        s += 3 if o["an_med_4h"] > 0 else -3
    s += float(np.clip(o["trend_7d"] * 100 * o["trend_7d_r2"] * 5, -10, 10))
    if o.get("hr_t") is not None: s += float(np.clip(o["hr_t"] * 2, -6, 6))
    if o["rsi"] > 80: s -= 8
    elif o["rsi"] < 30 and not o["making_new_lows"]: s += 4
    if o["vol_ratio"] > 1.5: s += 4 if o["ret_4h"] > 0 else -4
    s = float(np.clip(s, 0, 100))
    checks = [o.get("an_n") and o["an_p_up_4h"] - o["an_base_4h"] > 0.05, o["trend_7d"] > 0,
              o.get("hr_mean") is not None and o["hr_mean"] > 0, o["rsi"] < 75, not o["making_new_lows"]]
    conf = _conf(s, sum(bool(c) for c in checks), o.get("an_n", 0))
    if sit in LONG_SITS: action = "LONG CANDIDATE" if s >= 62 else "WATCHLIST"
    elif sit in SHORT_SITS: action = "AVOID"
    else: action = "WATCHLIST" if s >= 58 else "WAIT"
    return s, conf, action

def score_short(o, sit):
    s = 50.0 + SHORT_ADJ[sit]
    if o.get("an_n"):
        s += float(np.clip((o["an_p_dn_4h"] - o["an_base_dn_4h"]) * 100, -20, 20))
        s += 3 if o["an_med_4h"] < 0 else -3
    s += float(np.clip(-o["trend_7d"] * 100 * o["trend_7d_r2"] * 5, -10, 10))
    if o.get("hr_t") is not None: s += float(np.clip(-o["hr_t"] * 2, -6, 6))
    if o["rsi"] > 80: s += 8                       # stretched -> good for fading
    elif o["rsi"] < 25: s -= 8                     # oversold -> squeeze risk
    if o["vol_ratio"] > 1.5: s += 4 if o["ret_4h"] < 0 else -4
    s = float(np.clip(s, 0, 100))
    checks = [o.get("an_n") and o["an_p_dn_4h"] - o["an_base_dn_4h"] > 0.05, o["trend_7d"] < 0,
              o.get("hr_mean") is not None and o["hr_mean"] < 0, o["rsi"] > 25,
              bool(o["making_new_lows"]) or o["z_7d"] > 1.5]
    conf = _conf(s, sum(bool(c) for c in checks), o.get("an_n", 0))
    if sit in SHORT_SITS: action = "SHORT CANDIDATE" if s >= 62 else "WATCHLIST"
    elif sit in LONG_SITS: action = "AVOID"
    else: action = "WATCHLIST" if s >= 58 else "WAIT"
    return s, conf, action

def fields(o):
    f = defaultdict(lambda: "n/a")
    f.update(sym=o["base"], ret_1h=fp(o["ret_1h"]), ret_4h=fp(o["ret_4h"]), ret_24h=fp(o["ret_24h"]),
        dd30=fp(o["dd_30d"], 0), dd90=fp(o["dd_90d"], 0), rec=fu(o["recovery"]), rsi=f"{o['rsi']:.0f}",
        z7=f"{o['z_7d']:+.1f}", trend7=fp(o["trend_7d"], 2), r2=f"{o['trend_7d_r2']:.2f}",
        n_an=o.get("an_n", 0), p_up4=fu(o.get("an_p_up_4h")), p_dn4=fu(o.get("an_p_dn_4h")),
        base4=fu(o.get("an_base_4h")), base_dn4=fu(o.get("an_base_dn_4h")),
        med4=fp(o.get("an_med_4h")), q25=fp(o.get("an_q25_4h")), q75=fp(o.get("an_q75_4h")),
        last_pump=fp(o.get("last_pump_move")), hrs_pump=o.get("hrs_since_pump", "n/a"),
        post_pump_n=o.get("post_pump_n", 0), post_pump_avg=fp(o.get("post_pump_avg")),
        post_pump_win=fu(o.get("post_pump_win")), post_pump_dn=fu(o.get("post_pump_dn")),
        last_dump=fp(o.get("last_dump_move")), hrs_dump=o.get("hrs_since_dump", "n/a"),
        post_dump_n=o.get("post_dump_n", 0), post_dump_avg=fp(o.get("post_dump_avg")),
        post_dump_win=fu(o.get("post_dump_win")), post_dump_dn=fu(o.get("post_dump_dn")))
    return f

def build_text(o, sit):
    f = fields(o); t = pb.SITUATIONS[sit]
    lp = t["long_prediction"].format_map(f); sp = t["short_prediction"].format_map(f)
    hrt = o.get("hr_t")
    if hrt is not None and hrt >= 2:
        lp += (f" Seasonality: {o['hr_next']:02d}:00 UTC candles have averaged {fp(o['hr_mean'], 2)} "
               f"(positive on {fu(o['hr_win'])} of {o['hr_n']} days).")
    if hrt is not None and hrt <= -2:
        sp += (f" Seasonality: {o['hr_next']:02d}:00 UTC candles have averaged {fp(o['hr_mean'], 2)} "
               f"(negative on {fu(1 - o['hr_win'])} of {o['hr_n']} days).")
    prof = (f"Profile (180d): {o['pump_n180']} pumps / {o['dump_n180']} dumps"
            f" ({o['pump_n30']} / {o['dump_n30']} in the last 30d)")
    if o.get("pump_hour") is not None:
        prof += f"; pumps cluster around {o['pump_hour']:02d}:00 UTC ({fu(o['pump_hour_share'])} of them)"
    return dict(headline=t["label"], long_prediction=lp, long_prescription=t["long_prescription"].format_map(f),
                short_prediction=sp, short_prescription=t["short_prescription"].format_map(f), profile=prof + ".")

# ---------- main entry ----------
def analyze_symbol(sym, base, df):
    if len(df) < MIN_CANDLES: return None
    c = df["close"]; cv = c.values.astype(float); n = len(cv); price = float(cv[-1])
    lows = df["low"].values; v = df["quote_volume"]
    o = {"symbol": sym, "base": base, "price": price, "asof": int(c.index[-1].value // 10**6)}
    for k, h in [("ret_1h", 1), ("ret_4h", 4), ("ret_24h", 24), ("ret_7d", 168)]:
        o[k] = float(cv[-1] / cv[-1 - h] - 1)
    for tag, w in [("7d", 168), ("30d", 720)]:
        k, r2 = trend(np.log(cv[-w:]))
        o[f"trend_{tag}"] = float(np.exp(k * 24) - 1); o[f"trend_{tag}_r2"] = float(r2)
    hi30, lo30, hi90 = cv[-720:].max(), cv[-720:].min(), cv[-2160:].max()
    o["dd_30d"] = float(price / hi30 - 1); o["dd_90d"] = float(price / hi90 - 1)
    o["recovery"] = float((price - lo30) / (hi30 - lo30)) if hi30 > lo30 else 0.5
    o["rsi"] = float(rsi(c).iloc[-1])
    m = cv[-168:]; o["z_7d"] = float((price - m.mean()) / m.std()) if m.std() > 0 else 0.0
    o["vol_ratio"] = float(v.iloc[-4:].mean() / v.iloc[-720:].mean())
    o["making_new_lows"] = int(lows[-4:].min() < lows[-28:-4].min())
    o["bounce_from_low"] = float(price / lows[-12:].min() - 1)

    # time-series: pump / dump event study
    pumps, dumps, r4 = detect_events(c)
    for name, pos in [("pump", pumps), ("dump", dumps)]:
        o[f"{name}_n180"] = len(pos); o[f"{name}_n30"] = sum(p >= n - 720 for p in pos)
        o[f"hrs_since_{name}"] = (n - 1 - pos[-1]) if pos else None
        o[f"last_{name}_move"] = float(r4.iloc[pos[-1]]) if pos else None
        cnt, avg, win, dn = _event_stats(pos, cv)
        o[f"post_{name}_n"], o[f"post_{name}_avg"] = cnt, avg
        o[f"post_{name}_win"], o[f"post_{name}_dn"] = win, dn
    o["pump_hour"], o["pump_hour_share"] = None, None
    if len(pumps) >= 5:
        hrs = np.bincount(c.index[pumps].hour, minlength=24)
        o["pump_hour"] = int(hrs.argmax()); o["pump_hour_share"] = float(hrs.max() / hrs.sum())

    # time-series: hour-of-day seasonality for the NEXT candle
    r1 = c.pct_change().dropna(); nxt = (c.index[-1].hour + 1) % 24
    hr = r1[r1.index.hour == nxt]
    o["hr_next"], o["hr_n"], o["hr_mean"], o["hr_win"], o["hr_t"] = nxt, len(hr), None, None, None
    if len(hr) >= 60 and hr.std() > 0:
        o["hr_mean"] = float(hr.mean()); o["hr_win"] = float((hr > 0).mean())
        o["hr_t"] = float(hr.mean() / (hr.std() / np.sqrt(len(hr))))

    # data mining: pattern matching
    a = analog(c)
    if a:
        o["an_n"] = a["n"]; o["an_dist"] = a["avg_dist"]
        for h in HORIZONS:
            for key in ("p_up", "med", "base", "p_dn", "base_dn"):
                o[f"an_{key}_{h}h"] = a[f"{key}_{h}h"]
        o["an_mean_4h"], o["an_q25_4h"], o["an_q75_4h"] = a["mean_4h"], a["q25_4h"], a["q75_4h"]
    else:
        o["an_n"] = 0

    sit = classify(o); o["situation"] = sit
    o["long_score"], o["long_confidence"], o["long_action"] = score_long(o, sit)
    o["short_score"], o["short_confidence"], o["short_action"] = score_short(o, sit)
    d = o["long_score"] - o["short_score"]
    o["bias"] = "LONG" if (o["long_score"] >= 58 and d >= 10) else \
                "SHORT" if (o["short_score"] >= 58 and d <= -10) else "NEUTRAL"
    o.update(build_text(o, sit))
    return o