# ================= LOOK & FEEL (CSS + Plotly styling) =================
import html
import base64
import streamlit as st
import plotly.graph_objects as go
import plotly.io as pio

ACCENT = "#6366f1"
ACTION_COLORS = {"LONG CANDIDATE": "#22c55e", "SHORT CANDIDATE": "#ef4444", "WATCHLIST": "#f59e0b",
                 "WAIT": "#64748b", "AVOID": "#a855f7"}
BIAS_COLORS = {"LONG": "#22c55e", "SHORT": "#ef4444", "NEUTRAL": "#64748b"}
UP, DOWN = "#22c55e", "#ef4444"
COLORWAY = ["#6366f1", "#22c55e", "#f59e0b", "#06b6d4", "#ec4899", "#a855f7", "#ef4444", "#84cc16", "#14b8a6"]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, .stApp, p, h1, h2, h3, h4, label, button, input, textarea, [data-testid="stMarkdownContainer"] {
  font-family: 'Inter', system-ui, sans-serif; }
/* keep Streamlit's icon font intact (expander arrows, etc.) */
[data-testid="stIconMaterial"], .material-symbols-rounded, span[class*="material"] {
  font-family: 'Material Symbols Rounded', 'Material Icons' !important; }
.stApp {
  background-image:
    radial-gradient(1100px 480px at 8% -8%, rgba(99,102,241,.08), transparent 60%),
    radial-gradient(900px 420px at 100% 0%, rgba(34,197,94,.05), transparent 55%);
}
[data-testid="stHeader"] { background: transparent; }
footer { visibility: hidden; }
.block-container { padding-top: 1.5rem; max-width: 1400px; }
[data-testid="stSidebar"] { border-right: 1px solid rgba(128,128,128,.22); }
h1, h2, h3, h4 { letter-spacing: -0.02em; font-weight: 700; }

/* Hero container - Horizontal Layout */
.hero-container { 
    display: flex; 
    flex-direction: row; 
    align-items: center; 
    justify-content: center; 
    flex-wrap: wrap; 
    gap: 24px; 
    background: rgba(255, 255, 255, 0.6); 
    backdrop-filter: blur(10px);
    border: 1px solid rgba(128,128,128,.15); 
    border-radius: 12px; 
    padding: 16px 32px; 
    margin-bottom: 20px; 
    box-shadow: 0 4px 15px rgba(0,0,0,.02); 
}

.hero-logo { 
    max-height: 65px; 
    width: auto;
    margin: 0; 
}

.hero-subtitle { 
    color: #475569; 
    font-size: 1.1rem; 
    font-weight: 500; 
    text-align: left; 
    margin: 0; 
    border-left: 2px solid rgba(128,128,128,.25); 
    padding-left: 24px;
}

@media (max-width: 768px) {
    .hero-container { flex-direction: column; gap: 12px; text-align: center; padding: 20px; }
    .hero-subtitle { border-left: none; padding-left: 0; text-align: center; font-size: 0.95rem; }
}

/* KPI cards */
.kpi { background:rgba(128,128,128,.08); border:1px solid rgba(128,128,128,.22); border-top-width:3px;
       border-radius:16px; padding:14px 18px; }
.kpi .l { font-size:.72rem; text-transform:uppercase; letter-spacing:.08em; opacity:.65; font-weight:600; }
.kpi .v { font-size:1.9rem; font-weight:800; line-height:1.2; }

/* Signal cards */
.scard { background:rgba(128,128,128,.08); border:1px solid rgba(128,128,128,.22); border-radius:18px;
         padding:16px 18px; margin-bottom:14px; transition:transform .15s, box-shadow .15s; }
.scard:hover { transform:translateY(-2px); box-shadow:0 10px 26px rgba(0,0,0,.18); }
.scard .top { display:flex; justify-content:space-between; align-items:center; }
.scard .coin { font-size:1.35rem; font-weight:800; }
.scard .px { opacity:.55; font-size:.82rem; margin-left:8px; }
.scard .sub { opacity:.7; font-size:.82rem; margin:2px 0 10px; }
.scard .bar { height:7px; border-radius:99px; background:rgba(128,128,128,.25); overflow:hidden; }
.scard .bar > div { height:100%; border-radius:99px; }
.scard .sc { font-size:.75rem; opacity:.7; margin:4px 0 8px; font-weight:600; }
.scard .pred { font-size:.9rem; line-height:1.5; margin:0 0 8px; }
.scard .presc { font-size:.82rem; line-height:1.45; opacity:.75; border-top:1px dashed rgba(128,128,128,.35); padding-top:8px; }
.badge { display:inline-block; padding:3px 11px; border-radius:999px; font-size:.7rem; font-weight:700; letter-spacing:.04em; }

/* Native widgets */
[data-testid="stMetric"] { background:rgba(128,128,128,.08); border:1px solid rgba(128,128,128,.22);
                           padding:12px 16px; border-radius:14px; }
[data-testid="stMetricLabel"] p { opacity:.65; font-size:.78rem; text-transform:uppercase; letter-spacing:.05em; }
[data-testid="stMetricValue"] { font-weight:800; }
[data-testid="stAlert"] { border-radius:14px; }
[data-testid="stDataFrame"] { border:1px solid rgba(128,128,128,.22); border-radius:14px; overflow:hidden; }
[data-testid="stExpander"] { border-radius:14px; border:1px solid rgba(128,128,128,.22); }
.stButton > button { border-radius:12px; font-weight:600; border:1px solid rgba(128,128,128,.3); }
.stButton > button:hover { border-color:#6366f1; color:#6366f1; }
.stTabs [data-baseweb="tab-list"] { gap:6px; border-bottom:1px solid rgba(128,128,128,.22); }
.stTabs [data-baseweb="tab"] { padding:10px 16px; border-radius:10px 10px 0 0; font-weight:600; }
.stTabs [data-baseweb="tab-highlight"] { background:#6366f1; height:3px; }
.stTabs [aria-selected="true"] { color:#6366f1; }
</style>
"""

def inject():
    st.markdown(CSS, unsafe_allow_html=True)
    # Plotly: transparent background + grey text/grid that reads well on light AND dark
    t = go.layout.Template(pio.templates["plotly"])
    t.layout.update(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", colorway=COLORWAY,
        font=dict(family="Inter, sans-serif", color="#94a3b8"),
        xaxis=dict(gridcolor="rgba(128,128,128,.18)", zerolinecolor="rgba(128,128,128,.3)"),
        yaxis=dict(gridcolor="rgba(128,128,128,.18)", zerolinecolor="rgba(128,128,128,.3)"),
        title=dict(font=dict(size=15)), legend=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=40, r=20, t=50, b=40))
    pio.templates["radar"] = t; pio.templates.default = "radar"
    # make st.plotly_chart respect our template instead of Streamlit's own
    if not getattr(st.plotly_chart, "_radar", False):
        orig = st.plotly_chart
        def patched(fig, *a, **k):
            k.setdefault("theme", None); return orig(fig, *a, **k)
        patched._radar = True; st.plotly_chart = patched

def hero(logo_path, subtitle):
    """Renders the logo and subtitle in a centered, horizontal container."""
    try:
        with open(logo_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        img_html = f'<img src="data:image/png;base64,{img_b64}" class="hero-logo">'
    except FileNotFoundError:
        img_html = '<h2 style="margin:0;">📡 Patternada</h2>' # Fallback if logo is missing
        
    st.markdown(f'''
        <div class="hero-container">
            {img_html}
            <p class="hero-subtitle">{html.escape(subtitle)}</p>
        </div>
    ''', unsafe_allow_html=True)

def kpi(label, value, color=ACCENT):
    return (f'<div class="kpi" style="border-top-color:{color}"><div class="l">{html.escape(str(label))}</div>'
            f'<div class="v">{value}</div></div>')

def badge(text, color):
    return f'<span class="badge" style="background:{color}22;color:{color};border:1px solid {color}55">{html.escape(text)}</span>'

def _e(s): return html.escape(str(s)).replace("$", "&#36;")

def signal_card(r, side="long"):
    """One card for a coin, showing the LONG or SHORT view."""
    sc, act, conf = r[f"{side}_score"], r[f"{side}_action"], r[f"{side}_confidence"]
    c = ACTION_COLORS.get(act, "#64748b")
    return (f'<div class="scard" style="border-left:4px solid {c}"><div class="top"><div><span class="coin">{_e(r["base"])}</span>'
            f'<span class="px">{r["live_price"]:.6g}</span></div>{badge(act, c)}</div>'
            f'<div class="sub">{_e(r["headline"])} · confidence {_e(conf)}</div>'
            f'<div class="bar"><div style="width:{sc:.0f}%;background:linear-gradient(90deg,{c}99,{c})"></div></div>'
            f'<div class="sc">{side.title()} score {sc:.0f} / 100</div>'
            f'<p class="pred">{_e(r[side + "_prediction"])}</p>'
            f'<div class="presc">➡️ {_e(r[side + "_prescription"])}</div></div>')