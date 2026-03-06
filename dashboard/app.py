import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time
import os

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
REFRESH_INTERVAL = 30

st.set_page_config(
    page_title="NexStream · News Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

THEMES = {
    "Midnight": {
        "bg": "#080c10", "surface": "#0d1117", "border": "#1e2d3a",
        "border2": "#2a3f52", "text": "#c8d6e0", "text2": "#4a6070",
        "text3": "#2a3f52", "accent": "#3b9eff",
        "pos": "#2dce89", "neg": "#f5365c", "neu": "#fb6340",
        "pos_bg": "#0a2e1f", "neg_bg": "#2e0a14", "neu_bg": "#1e2210",
        "grid": "#0f1820",
    },
    "Slate": {
        "bg": "#0f1117", "surface": "#161b22", "border": "#21262d",
        "border2": "#30363d", "text": "#e6edf3", "text2": "#7d8590",
        "text3": "#484f58", "accent": "#58a6ff",
        "pos": "#3fb950", "neg": "#f85149", "neu": "#d29922",
        "pos_bg": "#0d2119", "neg_bg": "#2d1117", "neu_bg": "#271d0b",
        "grid": "#161b22",
    },
    "Obsidian": {
        "bg": "#13111c", "surface": "#1a1825", "border": "#2d2b3d",
        "border2": "#3d3b52", "text": "#e2dff0", "text2": "#6e6a8a",
        "text3": "#3d3b52", "accent": "#a78bfa",
        "pos": "#34d399", "neg": "#f87171", "neu": "#fbbf24",
        "pos_bg": "#0c2017", "neg_bg": "#2d1515", "neu_bg": "#2a1f08",
        "grid": "#1a1825",
    },
}

@st.cache_data(ttl=REFRESH_INTERVAL)
def fetch_news(limit, sentiment=None):
    try:
        params = {"limit": limit}
        if sentiment and sentiment != "All":
            params["sentiment"] = sentiment
        r = requests.get(f"{API_BASE}/news/", params=params, timeout=5)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return [], "API'ye bağlanılamadı."
    except Exception as e:
        return [], str(e)

def trigger_scrape(source):
    try:
        r = requests.post(f"{API_BASE}/news/scrape", json={"source": source}, timeout=5)
        return r.status_code == 200, r.json()
    except Exception as e:
        return False, {"message": str(e)}

def score_class(score):
    if score is None: return "neu"
    if score > 0.1:   return "pos"
    if score < -0.1:  return "neg"
    return "neu"

def format_date(dt_str):
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y · %H:%M")
    except:
        return dt_str

# ── TOP CONTROLS ──────────────────────────────────────────────────────────────
col_logo, col_theme, col_sentiment, col_limit, col_sort, col_source, col_btns, col_auto = st.columns([3, 1.5, 1.5, 1.5, 1.5, 1.5, 2, 1.5])

with col_logo:
    st.markdown("""
    <div style='display:flex;align-items:baseline;gap:0.5rem;padding-top:0.5rem'>
        <div style='font-family:Syne,sans-serif;font-weight:800;font-size:1.4rem;letter-spacing:-0.03em'>
            Nex<span style='color:var(--accent)'>Stream</span>
        </div>
        <div style='font-size:0.55rem;color:var(--text3);letter-spacing:0.1em;text-transform:uppercase'>
            News Engine
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_theme:
    theme_name = st.selectbox("Theme", list(THEMES.keys()), label_visibility="collapsed")

with col_sentiment:
    sentiment_filter = st.selectbox("Sentiment", ["All", "Positive", "Negative", "Neutral"], label_visibility="collapsed")

with col_limit:
    limit = st.selectbox("Limit", [10, 25, 50, 100], index=2, label_visibility="collapsed")

with col_sort:
    sort_by = st.selectbox("Sort", ["Newest First", "Highest Score", "Lowest Score"], label_visibility="collapsed")

with col_source:
    selected_source = st.selectbox("Source", ["BBC Technology"], label_visibility="collapsed")

with col_btns:
    btn1, btn2 = st.columns(2)
    with btn1:
        if st.button("⚡ Scrape", use_container_width=True):
            with st.spinner(""):
                ok, resp = trigger_scrape(selected_source)
                # ⚡ Scrape butonunda artık API'ye POST isteği atılıyor. API, mesajı Kafka'ya yayınlayacak ve worker'lar bu mesajı alıp haberleri çekecekler.
            if ok:
                st.success(f"✓ Scrape triggered")
                st.cache_data.clear()
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"✗ {resp.get('message', 'Failed')}")
    with btn2:
        if st.button("↺ Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

with col_auto:
    auto_refresh = st.toggle("Auto", value=False)

t = THEMES[theme_name]

# ── STYLES ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&display=swap');

:root {{
    --bg: {t['bg']}; --surface: {t['surface']}; --border: {t['border']};
    --border2: {t['border2']}; --text: {t['text']}; --text2: {t['text2']};
    --text3: {t['text3']}; --accent: {t['accent']};
    --pos: {t['pos']}; --neg: {t['neg']}; --neu: {t['neu']};
    --pos-bg: {t['pos_bg']}; --neg-bg: {t['neg_bg']}; --neu-bg: {t['neu_bg']};
    --grid: {t['grid']};
}}

html, body, [class*="css"] {{
    font-family: 'DM Mono', monospace;
    background-color: var(--bg) !important;
    color: var(--text);
}}

#MainMenu, footer, header, [data-testid="stToolbar"],
[data-testid="stSidebar"], [data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {{ display: none !important; }}

.block-container {{ padding: 1rem 2rem 2rem 2rem !important; max-width: 100% !important; }}

.nx-divider {{
    height: 1px;
    background: linear-gradient(90deg, var(--accent) 0%, var(--border) 50%, transparent 100%);
    margin: 0.5rem 0 1.5rem 0;
}}

.kpi-grid {{
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 1rem; margin-bottom: 1.5rem;
}}
.kpi-card {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 8px; padding: 1.25rem 1.5rem;
    position: relative; overflow: hidden; transition: border-color 0.2s;
}}
.kpi-card:hover {{ border-color: var(--border2); }}
.kpi-card::before {{ content:''; position:absolute; top:0; left:0; right:0; height:2px; }}
.kpi-card.total::before {{ background: var(--accent); }}
.kpi-card.pos::before   {{ background: var(--pos); }}
.kpi-card.neg::before   {{ background: var(--neg); }}
.kpi-card.neu::before   {{ background: var(--neu); }}
.kpi-label {{ font-size:0.62rem; color:var(--text2); letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.5rem; }}
.kpi-value {{ font-family:'Syne',sans-serif; font-size:2.2rem; font-weight:700; color:var(--text); line-height:1; }}
.kpi-sub {{ font-size:0.62rem; color:var(--text3); margin-top:0.4rem; }}

.section-title {{
    font-family:'Syne',sans-serif; font-size:0.72rem; font-weight:600;
    color:var(--text2); letter-spacing:0.14em; text-transform:uppercase;
    margin-bottom:1rem; display:flex; align-items:center; gap:0.5rem;
}}
.section-title::after {{ content:''; flex:1; height:1px; background:var(--border); }}

.status-bar {{
    display:flex; align-items:center; gap:0.6rem;
    font-size:0.62rem; color:var(--text3); margin-bottom:1.5rem;
}}
.status-dot {{
    width:6px; height:6px; border-radius:50%;
    background:var(--pos); animation:pulse 2s infinite;
}}
@keyframes pulse {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:0.4; }} }}

.news-card {{
    background:var(--surface); border:1px solid var(--border);
    border-radius:8px; padding:1rem 1.25rem; margin-bottom:0.6rem;
    display:flex; gap:1.25rem; align-items:flex-start;
    transition:border-color 0.2s, transform 0.15s;
}}
.news-card:hover {{ border-color:var(--border2); transform:translateX(3px); }}
.news-badge {{
    flex-shrink:0; padding:0.2rem 0.55rem; border-radius:4px;
    font-size:0.58rem; font-weight:500; letter-spacing:0.08em;
    text-transform:uppercase; margin-top:0.15rem;
}}
.badge-Positive {{ background:var(--pos-bg); color:var(--pos) !important; }}
.badge-Negative {{ background:var(--neg-bg); color:var(--neg) !important; }}
.badge-Neutral  {{ background:var(--neu-bg); color:var(--neu) !important; }}
.news-title {{ font-family:'Syne',sans-serif; font-size:0.92rem; font-weight:600; color:var(--text); line-height:1.4; margin-bottom:0.35rem; }}
.news-title a {{ text-decoration:none; color:inherit; }}
.news-title a:hover {{ color:var(--accent); }}
.news-summary {{ font-size:0.73rem; color:var(--text2); line-height:1.6; margin-bottom:0.4rem; }}
.news-meta {{ display:flex; gap:1rem; font-size:0.6rem; color:var(--text3); }}
.news-score {{ flex-shrink:0; text-align:center; min-width:3rem; }}
.score-val {{ font-family:'Syne',sans-serif; font-size:1.3rem; font-weight:700; }}
.score-val.pos {{ color:var(--pos); }}
.score-val.neg {{ color:var(--neg); }}
.score-val.neu {{ color:var(--neu); }}
.score-label {{ font-size:0.52rem; color:var(--text3); letter-spacing:0.08em; }}

.stButton > button {{
    background:var(--surface) !important; border:1px solid var(--border) !important;
    color:var(--text) !important; font-family:'DM Mono',monospace !important;
    font-size:0.7rem !important; border-radius:6px !important;
    transition:all 0.2s !important; height:38px !important;
}}
.stButton > button:hover {{ border-color:var(--accent) !important; color:var(--accent) !important; }}

.stSelectbox > div > div {{
    background:var(--surface) !important; border-color:var(--border) !important;
    color:var(--text) !important; font-family:'DM Mono',monospace !important;
    font-size:0.72rem !important;
}}

.stAlert {{
    background:var(--surface) !important; border:1px solid var(--border) !important;
    border-radius:8px !important; font-size:0.75rem !important;
}}
</style>
""", unsafe_allow_html=True)

# ── DIVIDER ───────────────────────────────────────────────────────────────────
st.markdown('<div class="nx-divider"></div>', unsafe_allow_html=True)

# ── DATA ──────────────────────────────────────────────────────────────────────
news, error = fetch_news(limit, sentiment_filter if sentiment_filter != "All" else None)

now = datetime.now().strftime("%H:%M:%S")
st.markdown(f"""
<div class="status-bar">
    <div class="status-dot"></div>
    <span>LIVE</span>·
    <span>{len(news)} articles</span>·
    <span>{now}</span>·
    <span>{theme_name}</span>·
    <span>Auto {'ON' if auto_refresh else 'OFF'}</span>
</div>
""", unsafe_allow_html=True)

if error:
    st.error(f"⚠ {error}")
    st.stop()

if not news:
    st.info("No articles found. Click ⚡ Scrape to fetch news.")
    st.stop()

df = pd.DataFrame(news)
df["created_at_dt"] = pd.to_datetime(df["created_at"])
df["sentiment_score"] = df["sentiment_score"].fillna(0)
df["sentiment_label"] = df["sentiment_label"].fillna("Neutral")

# ── KPI ───────────────────────────────────────────────────────────────────────
total     = len(df)
pos_n     = (df["sentiment_label"] == "Positive").sum()
neg_n     = (df["sentiment_label"] == "Negative").sum()
avg_score = df["sentiment_score"].mean()
pos_pct   = round(pos_n / total * 100) if total else 0
neg_pct   = round(neg_n / total * 100) if total else 0

st.markdown(f"""
<div class="kpi-grid">
    <div class="kpi-card total">
        <div class="kpi-label">Total Articles</div>
        <div class="kpi-value">{total}</div>
        <div class="kpi-sub">in current view</div>
    </div>
    <div class="kpi-card pos">
        <div class="kpi-label">Positive</div>
        <div class="kpi-value">{pos_pct}<span style='font-size:1rem;opacity:0.4'>%</span></div>
        <div class="kpi-sub">{pos_n} articles</div>
    </div>
    <div class="kpi-card neg">
        <div class="kpi-label">Negative</div>
        <div class="kpi-value">{neg_pct}<span style='font-size:1rem;opacity:0.4'>%</span></div>
        <div class="kpi-sub">{neg_n} articles</div>
    </div>
    <div class="kpi-card neu">
        <div class="kpi-label">Avg Score</div>
        <div class="kpi-value">{avg_score:+.2f}</div>
        <div class="kpi-sub">sentiment index</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── CHARTS ────────────────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 2])

with col1:
    st.markdown('<div class="section-title">Sentiment Distribution</div>', unsafe_allow_html=True)
    pie_df = df["sentiment_label"].value_counts().reset_index()
    pie_df.columns = ["label", "count"]
    color_map = {"Positive": t["pos"], "Negative": t["neg"], "Neutral": t["neu"]}

    fig_pie = go.Figure(go.Pie(
        labels=pie_df["label"], values=pie_df["count"], hole=0.65,
        marker=dict(colors=[color_map.get(l, t["text2"]) for l in pie_df["label"]], line=dict(color=t["bg"], width=2)),
        textfont=dict(family="DM Mono", size=11, color=t["text"]),
        hovertemplate="<b>%{label}</b><br>%{value} · %{percent}<extra></extra>",
    ))
    fig_pie.add_annotation(text=f"<b>{total}</b>", x=0.5, y=0.5, showarrow=False,
        font=dict(family="Syne", size=24, color=t["text"]))
    fig_pie.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=10, l=10, r=10), height=240,
        legend=dict(font=dict(family="DM Mono", size=10, color=t["text2"]),
            bgcolor="rgba(0,0,0,0)", orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    st.markdown('<div class="section-title">Sentiment Score Timeline</div>', unsafe_allow_html=True)
    tl = df.sort_values("created_at_dt").copy()
    tl["rolling"] = tl["sentiment_score"].rolling(3, min_periods=1).mean()

    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(
        x=tl["created_at_dt"], y=tl["sentiment_score"], mode="markers", name="Score",
        marker=dict(color=tl["sentiment_score"],
            colorscale=[[0, t["neg"]], [0.5, t["neu"]], [1, t["pos"]]], size=8, line=dict(width=0)),
        hovertemplate="<b>%{text}</b><br>%{y:.2f}<extra></extra>",
        text=tl["title"].str[:50] + "...",
    ))
    fig_line.add_trace(go.Scatter(
        x=tl["created_at_dt"], y=tl["rolling"], mode="lines", name="Trend",
        line=dict(color=t["accent"], width=2, dash="dot"),
    ))
    fig_line.add_hline(y=0, line_color=t["border"], line_width=1)
    fig_line.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=10, l=10, r=10), height=240,
        xaxis=dict(showgrid=False, zeroline=False, tickfont=dict(family="DM Mono", size=9, color=t["text3"]), tickformat="%d %b %H:%M"),
        yaxis=dict(showgrid=True, gridcolor=t["grid"], zeroline=False, tickfont=dict(family="DM Mono", size=9, color=t["text3"]), range=[-1.1, 1.1]),
        legend=dict(font=dict(family="DM Mono", size=10, color=t["text2"]), bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
    )
    st.plotly_chart(fig_line, use_container_width=True)

st.markdown('<div class="section-title">Score Distribution</div>', unsafe_allow_html=True)
bins = pd.cut(df["sentiment_score"], bins=[-1.0, -0.6, -0.2, 0.2, 0.6, 1.0],
              labels=["Very Neg", "Negative", "Neutral", "Positive", "Very Pos"])
bin_counts = bins.value_counts().sort_index()

fig_bar = go.Figure(go.Bar(
    x=bin_counts.index.tolist(), y=bin_counts.values,
    marker=dict(color=[t["neg"], t["neg"], t["neu"], t["pos"], t["pos"]], line=dict(width=0)),
    hovertemplate="<b>%{x}</b><br>%{y} articles<extra></extra>",
))
fig_bar.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=10, b=10, l=10, r=10), height=140, bargap=0.3,
    xaxis=dict(showgrid=False, zeroline=False, tickfont=dict(family="DM Mono", size=10, color=t["text2"])),
    yaxis=dict(showgrid=True, gridcolor=t["grid"], zeroline=False, tickfont=dict(family="DM Mono", size=9, color=t["text3"])),
)
st.plotly_chart(fig_bar, use_container_width=True)

# ── NEWS LIST ─────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Latest Articles</div>', unsafe_allow_html=True)

if sort_by == "Newest First":
    display_df = df.sort_values("created_at_dt", ascending=False)
elif sort_by == "Highest Score":
    display_df = df.sort_values("sentiment_score", ascending=False)
else:
    display_df = df.sort_values("sentiment_score", ascending=True)

for _, row in display_df.iterrows():
    label   = row.get("sentiment_label", "Neutral")
    score   = row.get("sentiment_score", 0) or 0
    sc      = score_class(score)
    title   = row.get("title", "—")
    url     = row.get("url", "#")
    summary = row.get("summary") or row.get("content", "")[:120]
    source  = row.get("source", "—")
    date    = format_date(row.get("created_at", ""))

    st.markdown(f"""
    <div class="news-card">
        <div class="news-score">
            <div class="score-val {sc}">{score:+.1f}</div>
            <div class="score-label">SCORE</div>
        </div>
        <div style="flex:1;min-width:0;">
            <div class="news-title"><a href="{url}" target="_blank">{title}</a></div>
            <div class="news-summary">{summary}</div>
            <div class="news-meta"><span>{source}</span><span>{date}</span></div>
        </div>
        <div><span class="news-badge badge-{label}">{label}</span></div>
    </div>
    """, unsafe_allow_html=True)

if auto_refresh:
    refresh_rate = REFRESH_INTERVAL
    time.sleep(refresh_rate)
    st.cache_data.clear()
    st.rerun()