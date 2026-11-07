# ================= DASHBOARD (Streamlit) - LONG & SHORT =================
# Run:  streamlit run dashboard.py
import numpy as np, pandas as pd, streamlit as st
import plotly.graph_objects as go, plotly.express as px
from plotly.subplots import make_subplots
import collector as col, analyzer as an, playbook as pb
from config import *
import theme

st.set_page_config(page_title="Patternada", page_icon="📡", layout="wide")
COLORS = theme.ACTION_COLORS

@st.cache_data(ttl=60)
def load_signals():
    try:
        with col.db() as con: return pd.read_sql("SELECT * FROM signals", con)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_df(sym): return col.load_candles(sym)

@st.cache_data(ttl=300)
def scorecard():
    with col.db() as con:
        h = pd.read_sql("SELECT * FROM signal_history", con)
        if h.empty: return h
        c = pd.read_sql("SELECT symbol,open_time,close FROM candles WHERE open_time>=?", con,
                        params=(int(h["asof"].min()),))
    c = c.sort_values(["symbol", "open_time"])
    c["fwd4"] = c.groupby("symbol")["close"].shift(-4) / c["close"] - 1
    return h.merge(c[["symbol", "open_time", "fwd4"]], left_on=["symbol", "asof"],
                   right_on=["symbol", "open_time"]).dropna(subset=["fwd4"])

sig = load_signals()
theme.inject()
theme.hero("images/logo11.png", "Binance Futures · pattern-based predictions & prescriptions · LONG and SHORT analysis")
if sig.empty:
    st.warning("No data yet. Start the bot first:  `python bot.py`  (first run takes a few minutes).")
    st.stop()
if "short_score" not in sig.columns:
    st.warning("Your saved signals are from the long-only version. Stop and restart `python bot.py` "
               "to regenerate them with Long & Short analysis, then press Reload.")
    st.stop()

# ---------------- sidebar ----------------
st.sidebar.header("Filters")
bias_sel = st.sidebar.multiselect("Overall bias", ["LONG", "SHORT", "NEUTRAL"], default=["LONG", "SHORT", "NEUTRAL"])
min_score = st.sidebar.slider("Min best score (long or short)", 0, 100, 0)
min_vol = st.sidebar.slider("Min 24h volume (M USDT)", 0, 500, 5)
q = st.sidebar.text_input("Search coin").upper().strip()
if st.sidebar.button("🔄 Reload"): st.cache_data.clear()
sig["best"] = sig[["long_score", "short_score"]].max(axis=1)
f = sig[sig.bias.isin(bias_sel) & (sig.best >= min_score) & (sig.volume_24h >= min_vol * 1e6)]
if q: f = f[f.base.str.contains(q)]
st.sidebar.caption("Times are UTC. Analysis only — this app never places orders.")

t1, t2, t3, t4, t5 = st.tabs(["🎯 Long & Short", "📊 Market visuals", "🔍 Coin detail", "📖 Playbook", "🧪 Scorecard"])

# ---------------- tab 1 ----------------
with t1:
    c = st.columns(5)
    k = [("Coins analysed", len(sig), theme.ACCENT),
         ("Long candidates", int((sig.long_action == "LONG CANDIDATE").sum()), COLORS["LONG CANDIDATE"]),
         ("Short candidates", int((sig.short_action == "SHORT CANDIDATE").sum()), COLORS["SHORT CANDIDATE"]),
         ("Watchlist", int(((sig.long_action == "WATCHLIST") | (sig.short_action == "WATCHLIST")).sum()), COLORS["WATCHLIST"]),
         ("Neutral", int((sig.bias == "NEUTRAL").sum()), COLORS["WAIT"])]
    for col_, (l, v, clr) in zip(c, k): col_.markdown(theme.kpi(l, v, clr), unsafe_allow_html=True)
    st.caption(f"Last update: {sig.generated_at.iloc[0]} UTC · candles: 1h, last {HISTORY_DAYS} days")

    L, S = st.columns(2)
    for side, box, title in [("long", L, "🟢 LONG ideas"), ("short", S, "🔴 SHORT ideas")]:
        with box:
            st.subheader(title)
            d = f[f[f"{side}_action"] == f"{side.upper()} CANDIDATE"].sort_values(f"{side}_score", ascending=False).head(5)
            if d.empty:
                st.info(f"No {side} candidates right now. 'No edge' is a valid result.")
            for _, r in d.iterrows():
                st.markdown(theme.signal_card(r, side), unsafe_allow_html=True)

    st.subheader("All coins")
    t = f.sort_values("best", ascending=False)[["base", "bias", "long_score", "short_score", "headline",
        "ret_1h", "ret_24h", "dd_30d", "rsi", "an_p_up_4h", "an_p_dn_4h", "an_n", "live_price", "volume_24h"]].copy()
    for kk in ["ret_1h", "ret_24h", "dd_30d", "an_p_up_4h", "an_p_dn_4h"]: t[kk] = t[kk] * 100
    t["volume_24h"] = t["volume_24h"] / 1e6
    st.dataframe(t, hide_index=True, width="stretch", height=520, column_config={
        "base": "Coin", "bias": "Bias", "headline": "Situation",
        "long_score": st.column_config.ProgressColumn("Long score", min_value=0, max_value=100, format="%.0f"),
        "short_score": st.column_config.ProgressColumn("Short score", min_value=0, max_value=100, format="%.0f"),
        "ret_1h": st.column_config.NumberColumn("1h %", format="%.2f"),
        "ret_24h": st.column_config.NumberColumn("24h %", format="%.1f"),
        "dd_30d": st.column_config.NumberColumn("From 30d high %", format="%.0f"),
        "rsi": st.column_config.NumberColumn("RSI", format="%.0f"),
        "an_p_up_4h": st.column_config.NumberColumn("P(up 4h) %", format="%.0f"),
        "an_p_dn_4h": st.column_config.NumberColumn("P(down 4h) %", format="%.0f"),
        "an_n": "Similar cases", "live_price": st.column_config.NumberColumn("Price", format="%.6g"),
        "volume_24h": st.column_config.NumberColumn("24h Vol (M)", format="%.0f")})

# ---------------- tab 2 ----------------
with t2:
    a, b = st.columns(2)
    cnt = sig.headline.value_counts().reset_index(); cnt.columns = ["Situation", "Coins"]
    a.plotly_chart(px.bar(cnt, x="Coins", y="Situation", orientation="h", title="Coins per situation"),
                   width="stretch")
    b.plotly_chart(px.scatter(sig, x="long_score", y="short_score", color="bias", hover_name="base",
        color_discrete_map=theme.BIAS_COLORS, title="Long score vs short score (top-left = short, bottom-right = long)"),
        width="stretch")
    s2 = sig.assign(dd=sig.dd_30d * 100, size=np.log10(sig.volume_24h))
    st.plotly_chart(px.scatter(s2, x="dd", y="rsi", color="headline", size="size", hover_name="base",
        title="Drawdown from 30d high vs RSI (bottom-left = beaten-down & oversold, top-right = stretched)",
        labels={"dd": "% from 30d high"}), width="stretch")
    a, b = st.columns(2)
    mv = sig.assign(r=sig.ret_24h * 100).sort_values("r")
    a.plotly_chart(px.bar(pd.concat([mv.head(10), mv.tail(10)]), x="base", y="r",
                          title="Biggest 24h movers (%)"), width="stretch")
    b.plotly_chart(px.scatter(sig, x="trend_7d_r2", y=sig.trend_7d * 100, hover_name="base", color="bias",
        color_discrete_map=theme.BIAS_COLORS, title="7d trend strength (R²) vs slope (%/day)",
        labels={"y": "%/day"}), width="stretch")

# ---------------- tab 3 ----------------
with t3:
    base = st.selectbox("Coin", sig.sort_values("best", ascending=False).base.tolist())
    r = sig[sig.base == base].iloc[0]; df = load_df(r.symbol)
    st.markdown(f"### {r.base} — {r.headline}  ·  overall bias: **{r.bias}**")
    m = st.columns(5)
    m[0].metric("Long score", f"{r.long_score:.0f}", r.long_action)
    m[1].metric("Short score", f"{r.short_score:.0f}", r.short_action)
    m[2].metric("24h", f"{r.ret_24h:+.1%}"); m[3].metric("From 30d high", f"{r.dd_30d:+.0%}")
    m[4].metric("RSI", f"{r.rsi:.0f}")
    cl, cs = st.columns(2)
    cl.success(f"**🟢 LONG view ({r.long_action}, confidence {r.long_confidence})**\n\n"
               f"**Prediction:** {r.long_prediction}\n\n**Prescription:** {r.long_prescription}")
    cs.error(f"**🔴 SHORT view ({r.short_action}, confidence {r.short_confidence})**\n\n"
             f"**Prediction:** {r.short_prediction}\n\n**Prescription:** {r.short_prescription}")
    st.caption(r.profile)
    days = st.radio("Chart window (days)", [7, 30, 90, 180], index=1, horizontal=True)
    sub = df.tail(days * 24)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=sub.index, open=sub.open, high=sub.high, low=sub.low, close=sub.close,
        name="Price", increasing_line_color=theme.UP, decreasing_line_color=theme.DOWN), row=1, col=1)
    x = np.arange(len(sub)); kk, b0 = np.polyfit(x, np.log(sub.close.values), 1)
    fig.add_trace(go.Scatter(x=sub.index, y=np.exp(kk * x + b0), name="Linear trend",
                             line=dict(dash="dash", width=2)), row=1, col=1)
    pumps, dumps, _ = an.detect_events(df.close)
    for pos, nm, sym_, colr, mult in [(pumps, "Pump", "triangle-up", "#22c55e", 1.01),
                                      (dumps, "Dump", "triangle-down", "#ef4444", 0.99)]:
        idx = df.index[pos]; idx = idx[idx >= sub.index[0]]
        if len(idx):
            y = df.loc[idx, "high" if nm == "Pump" else "low"] * mult
            fig.add_trace(go.Scatter(x=idx, y=y, mode="markers", name=nm,
                          marker=dict(symbol=sym_, size=11, color=colr)), row=1, col=1)
    fig.add_trace(go.Bar(x=sub.index, y=sub.quote_volume, name="Volume", marker_color="rgba(148,163,184,.55)"), row=2, col=1)
    fig.update_layout(height=620, xaxis_rangeslider_visible=False, margin=dict(t=30))
    st.plotly_chart(fig, width="stretch")
    a, b, c3 = st.columns(3)
    dd = (sub.close / sub.close.cummax() - 1) * 100
    a.plotly_chart(go.Figure(go.Scatter(x=sub.index, y=dd, fill="tozeroy", line_color="#ef4444"))
                   .update_layout(title="Drawdown from running high (%)", height=320), width="stretch")
    r1 = df.close.pct_change().dropna() * 100; hm = r1.groupby(r1.index.hour).mean()
    nxt = int(r.hr_next)
    b.plotly_chart(go.Figure(go.Bar(x=hm.index, y=hm.values,
        marker_color=["#f59e0b" if h == nxt else "#64748b" for h in hm.index]))
        .update_layout(title=f"Avg 1h return by UTC hour (next = {nxt:02d}:00)", height=320), width="stretch")
    ana = an.analog(df.close)
    if ana:
        c3.plotly_chart(px.histogram(x=ana["fwd"][4] * 100, nbins=15,
            title=f"What happened 4h after {ana['n']} similar setups (%)").update_layout(height=320),
            width="stretch")

# ---------------- tab 4 ----------------
with t4:
    st.write("Every prediction/prescription uses one of these templates, filled with the coin's own numbers. "
             "Each situation has wording for both the long and the short side.")
    for key, tpl in pb.SITUATIONS.items():
        with st.expander(f"{tpl['icon']} {tpl['label']}  ({key})"):
            st.markdown(f"**When it triggers:** {tpl['when']}")
            a, b = st.columns(2)
            a.markdown("##### 🟢 Long")
            a.markdown(f"**Prediction:** {tpl['long_prediction']}"); a.markdown(f"**Prescription:** {tpl['long_prescription']}")
            b.markdown("##### 🔴 Short")
            b.markdown(f"**Prediction:** {tpl['short_prediction']}"); b.markdown(f"**Prescription:** {tpl['short_prescription']}")

# ---------------- tab 5 ----------------
with t5:
    st.write("Does the radar actually work? Each signal is graded 4h later against the real price. "
             "Trust a side only if its 'CANDIDATE' row clearly beats the baseline over a large sample.")
    sc = scorecard()
    if sc.empty:
        st.info("Not enough history yet. Keep the bot running — grades appear 4+ hours after the first signals.")
    else:
        a, b = st.columns(2)
        gl = sc.groupby("action").agg(signals=("fwd4", "size"),
              hit_rate=("fwd4", lambda s: (s > WIN_THRESHOLD).mean() * 100),
              avg_ret=("fwd4", lambda s: s.mean() * 100)).round(2)
        gl.loc["ALL (baseline)"] = [len(sc), round((sc.fwd4 > WIN_THRESHOLD).mean() * 100, 2), round(sc.fwd4.mean() * 100, 2)]
        a.markdown("##### 🟢 Long signals (win = price up >0.2% after 4h)")
        a.dataframe(gl.rename(columns={"hit_rate": "Hit rate %", "avg_ret": "Avg 4h return %"}), width="stretch")
        ss = sc.dropna(subset=["short_action"])
        if ss.empty:
            b.info("Short signals will appear after the bot has run for a few hours.")
        else:
            gs = ss.groupby("short_action").agg(signals=("fwd4", "size"),
                  hit_rate=("fwd4", lambda s: (s < -WIN_THRESHOLD).mean() * 100),
                  avg_ret=("fwd4", lambda s: -s.mean() * 100)).round(2)
            gs.loc["ALL (baseline)"] = [len(ss), round((ss.fwd4 < -WIN_THRESHOLD).mean() * 100, 2), round(-ss.fwd4.mean() * 100, 2)]
            b.markdown("##### 🔴 Short signals (win = price down >0.2% after 4h)")
            b.dataframe(gs.rename(columns={"hit_rate": "Hit rate %", "avg_ret": "Avg 4h return % (short)"}), width="stretch")
st.caption("⚠️ Statistical pattern analysis, not financial advice. Shorting carries squeeze and liquidation risk. Past patterns do not guarantee future moves.")