import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timezone
import time
import os

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

# Kaynak listesi API'den çekilir; API erişilemezse bu fallback kullanılır.
_SOURCES_FALLBACK = [
    "TRT Haber", "BBC Türkçe", "Hürriyet", "Hürriyet Spor",
    "Sabah", "CNN Türk", "Sözcü", "Habertürk", "HT Spor",
    "BBC Technology", "BBC Sport",
]

@st.cache_data(ttl=3600)
def fetch_sources():
    try:
        r = requests.get(f"{API_BASE}/news/sources", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return _SOURCES_FALLBACK

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

# ── SESSION STATE ─────────────────────────────────────────────────────────────
for k, v in [
    ("theme", "Midnight"), ("limit", 50), ("auto_refresh", False),
    ("search_results", None), ("search_error", None),
]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── API ───────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def fetch_news(limit):
    try:
        r = requests.get(f"{API_BASE}/news/", params={"limit": limit}, timeout=5)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return [], "API'ye bağlanılamadı"
    except Exception as e:
        return [], str(e)

def do_scrape(source):
    try:
        r = requests.post(f"{API_BASE}/news/scrape", json={"source": source}, timeout=10)
        return r.status_code == 200
    except Exception:
        return False

def do_search(query, n):
    try:
        r = requests.post(f"{API_BASE}/news/search", json={"query": query, "n_results": n}, timeout=15)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return [], "API'ye bağlanılamadı"
    except Exception as e:
        return [], str(e)

def do_reindex():
    try:
        r = requests.post(f"{API_BASE}/news/reindex", timeout=120)
        r.raise_for_status()
        return True, r.json()
    except Exception as e:
        return False, {"error": str(e)}

def rel_time(dt_str):
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        s = int((datetime.now(timezone.utc) - dt).total_seconds())
        if s < 60:    return f"{s}sn"
        if s < 3600:  return f"{s // 60}dk"
        if s < 86400: return f"{s // 3600}sa"
        return f"{s // 86400}g"
    except Exception:
        return dt_str

def score_cls(v):
    if v is None: return "neu"
    return "pos" if v > 0.1 else ("neg" if v < -0.1 else "neu")

# ── CSS ───────────────────────────────────────────────────────────────────────
t = THEMES[st.session_state.theme]

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&display=swap');

:root {{
    --bg:{t['bg']}; --surface:{t['surface']}; --border:{t['border']};
    --border2:{t['border2']}; --text:{t['text']}; --text2:{t['text2']};
    --text3:{t['text3']}; --accent:{t['accent']};
    --pos:{t['pos']}; --neg:{t['neg']}; --neu:{t['neu']};
    --pos-bg:{t['pos_bg']}; --neg-bg:{t['neg_bg']}; --neu-bg:{t['neu_bg']};
    --grid:{t['grid']};
}}
html,body,[class*="css"] {{
    font-family:'DM Mono',monospace;
    background-color:var(--bg) !important;
    color:var(--text);
}}
#MainMenu,footer,header,[data-testid="stToolbar"],
[data-testid="stSidebar"],[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {{ display:none !important; }}
.block-container {{ padding:1.5rem 2.5rem 2rem !important; max-width:100% !important; }}

.nx-logo {{
    font-family:'Syne',sans-serif; font-weight:800;
    font-size:1.45rem; letter-spacing:-0.04em; padding-top:0.2rem;
}}
.nx-logo span {{ color:var(--accent); }}
.nx-logo small {{
    font-size:0.6rem; font-weight:400; color:var(--text3);
    font-family:'DM Mono',monospace; letter-spacing:0.04em; margin-left:0.4rem;
}}

.nx-divider {{
    height:1px;
    background:linear-gradient(90deg,var(--accent) 0%,var(--border) 40%,transparent 100%);
    margin:0.6rem 0 1rem;
}}

.nx-status {{
    display:flex; align-items:center; gap:0.5rem;
    font-size:0.6rem; color:var(--text3); margin:0.25rem 0 1.25rem;
}}
.nx-dot {{
    width:6px; height:6px; border-radius:50%;
    background:var(--pos); animation:pulse 2s infinite; flex-shrink:0;
}}
@keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:0.3}} }}

.kpi-grid {{
    display:grid; grid-template-columns:repeat(4,1fr);
    gap:0.75rem; margin-bottom:1.5rem;
}}
.kpi-card {{
    background:var(--surface); border:1px solid var(--border);
    border-radius:10px; padding:1rem 1.25rem; overflow:hidden; position:relative;
}}
.kpi-card::before {{ content:''; position:absolute; top:0; left:0; right:0; height:2px; }}
.kpi-card.total::before {{ background:var(--accent); }}
.kpi-card.pos::before   {{ background:var(--pos); }}
.kpi-card.neg::before   {{ background:var(--neg); }}
.kpi-card.neu::before   {{ background:var(--neu); }}
.kpi-label {{ font-size:0.58rem; color:var(--text2); letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.4rem; }}
.kpi-value {{ font-family:'Syne',sans-serif; font-size:2rem; font-weight:700; color:var(--text); line-height:1; }}
.kpi-unit  {{ font-size:1rem; opacity:0.4; }}
.kpi-sub   {{ font-size:0.58rem; color:var(--text3); margin-top:0.3rem; }}

.nx-section {{
    font-family:'Syne',sans-serif; font-size:0.67rem; font-weight:600;
    color:var(--text2); letter-spacing:0.14em; text-transform:uppercase;
    display:flex; align-items:center; gap:0.6rem; margin-bottom:0.75rem;
}}
.nx-section::after {{ content:''; flex:1; height:1px; background:var(--border); }}

.nx-card {{
    background:var(--surface); border:1px solid var(--border);
    border-radius:10px; padding:1rem 1.2rem; margin-bottom:0.5rem;
    display:flex; gap:1rem; align-items:flex-start;
    transition:border-color 0.2s,transform 0.15s;
}}
.nx-card:hover {{ border-color:var(--border2); transform:translateX(2px); }}
.nx-score {{
    flex-shrink:0; text-align:center; width:3.5rem; padding-top:0.1rem;
}}
.nx-score-val {{
    font-family:'Syne',sans-serif; font-size:1.25rem; font-weight:700; line-height:1;
}}
.nx-score-val.pos {{ color:var(--pos); }}
.nx-score-val.neg {{ color:var(--neg); }}
.nx-score-val.neu {{ color:var(--neu); }}
.nx-score-lbl {{ font-size:0.5rem; color:var(--text3); letter-spacing:0.08em; margin-top:0.2rem; }}
.nx-body {{ flex:1; min-width:0; }}
.nx-title {{
    font-family:'Syne',sans-serif; font-size:0.9rem; font-weight:600;
    color:var(--text); line-height:1.45; margin-bottom:0.3rem;
}}
.nx-title a {{ text-decoration:none; color:inherit; }}
.nx-title a:hover {{ color:var(--accent); }}
.nx-summary {{
    font-size:0.71rem; color:var(--text2); line-height:1.6; margin-bottom:0.35rem;
    display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;
}}
.nx-meta {{ display:flex; align-items:center; gap:0.75rem; font-size:0.58rem; color:var(--text3); }}
.nx-source {{
    padding:0.15rem 0.5rem; border-radius:4px;
    background:var(--border); color:var(--text2) !important; font-size:0.57rem; font-weight:500;
}}
.nx-badge {{ flex-shrink:0; padding-top:0.1rem; }}
.nx-badge-inner {{
    padding:0.2rem 0.6rem; border-radius:5px;
    font-size:0.55rem; font-weight:500; letter-spacing:0.06em; text-transform:uppercase;
}}
.badge-Positive {{ background:var(--pos-bg); color:var(--pos) !important; }}
.badge-Negative {{ background:var(--neg-bg); color:var(--neg) !important; }}
.badge-Neutral  {{ background:var(--neu-bg); color:var(--neu) !important; }}

.stButton>button {{
    background:var(--surface) !important; border:1px solid var(--border) !important;
    color:var(--text) !important; font-family:'DM Mono',monospace !important;
    font-size:0.72rem !important; border-radius:7px !important; transition:all 0.2s !important;
}}
.stButton>button:hover {{ border-color:var(--accent) !important; color:var(--accent) !important; }}
.stTextInput>div>div>input {{
    background:var(--surface) !important; border-color:var(--border) !important;
    color:var(--text) !important; font-family:'DM Mono',monospace !important;
    font-size:0.75rem !important; border-radius:7px !important;
}}
.stTextInput>div>div>input:focus {{
    border-color:var(--accent) !important; box-shadow:0 0 0 1px var(--accent) !important;
}}
.stMultiSelect>div>div {{
    background:var(--surface) !important; border-color:var(--border) !important;
    color:var(--text) !important; font-size:0.75rem !important; border-radius:7px !important;
}}
</style>
""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────────────────────
h1, _, h3 = st.columns([3, 5, 2])

with h1:
    st.markdown('<div class="nx-logo">Nex<span>Stream</span><small>· News Engine</small></div>', unsafe_allow_html=True)

with h3:
    with st.popover("⚙ Ayarlar", width='stretch'):
        st.selectbox("Tema", list(THEMES.keys()),
            index=list(THEMES.keys()).index(st.session_state.theme),
            key="theme")

        st.divider()
        st.caption("VERİ ÇEKME")
        _sources = fetch_sources()
        if st.button("⚡ Tüm Kaynakları Çek", width='stretch'):
            bar = st.progress(0, text="Başlıyor…")
            for i, src in enumerate(_sources):
                do_scrape(src)
                bar.progress((i + 1) / len(_sources), text=src)
            bar.empty()
            st.success(f"✓ {len(_sources)} kaynak Kafka kuyruğuna alındı — haberler 1–3 dk içinde görünür")

        with st.expander("Tek kaynak çek"):
            src_sel = st.selectbox("Kaynak", _sources, label_visibility="collapsed", key="src_single")
            if st.button("Çek", key="btn_single"):
                ok = do_scrape(src_sel)
                if ok:
                    st.cache_data.clear()
                    st.success("✓ Tamamlandı")
                else:
                    st.error("✗ Hata")

        st.divider()
        st.caption("VEKTÖR İNDEKS")
        if st.button("⟳ Yeniden İndeksle", width='stretch'):
            with st.spinner("İndeksleniyor…"):
                ok, res = do_reindex()
            if ok:
                st.success(f"✓ {res.get('indexed', 0)}/{res.get('total', 0)} haber")
            else:
                st.error(str(res))

        st.divider()
        st.caption("GÖRÜNÜM")
        st.select_slider("Haber limiti", options=[25, 50, 100, 200], key="limit")
        st.toggle("Otomatik yenile (30s)", key="auto_refresh")

st.markdown('<div class="nx-divider"></div>', unsafe_allow_html=True)

# ── SEARCH ────────────────────────────────────────────────────────────────────
sc1, sc2, sc3 = st.columns([6, 1, 1])
with sc1:
    query = st.text_input(
        "search",
        placeholder="Anlamsal arama… örn. 'yapay zeka', 'Beşiktaş maç sonucu', 'AI developments'",
        label_visibility="collapsed",
    )
with sc2:
    n_res = st.selectbox("n", [5, 10, 20], index=1, label_visibility="collapsed")
with sc3:
    search_btn = st.button("Ara", width='stretch')

if search_btn:
    if query.strip():
        with st.spinner("Aranıyor…"):
            results, err = do_search(query.strip(), n_res)
        st.session_state.search_results = results
        st.session_state.search_error = err
    else:
        st.session_state.search_results = None
        st.session_state.search_error = None

if st.session_state.search_results is not None:
    rc1, rc2 = st.columns([5, 1])
    with rc1:
        st.markdown(
            f'<div class="nx-section">Arama Sonuçları · {len(st.session_state.search_results)}</div>',
            unsafe_allow_html=True,
        )
    with rc2:
        if st.button("× Kapat", width='stretch'):
            st.session_state.search_results = None
            st.rerun()

    if st.session_state.search_error:
        st.error(f"⚠ {st.session_state.search_error}")
    elif not st.session_state.search_results:
        st.info("Sonuç bulunamadı. Ayarlar > Yeniden İndeksle butonuna bas.")
    else:
        cards = []
        for item in st.session_state.search_results:
            pct = int(item["score"] * 100)
            summary = (item.get("summary") or item.get("content", ""))[:180]
            cards.append(f"""
            <div class="nx-card">
                <div class="nx-score">
                    <div class="nx-score-val neu">{pct}<span style="font-size:0.65rem">%</span></div>
                    <div class="nx-score-lbl">EŞLEŞME</div>
                </div>
                <div class="nx-body">
                    <div class="nx-title"><a href="{item['url']}" target="_blank">{item['title']}</a></div>
                    <div class="nx-summary">{summary}</div>
                    <div class="nx-meta"><span class="nx-source">{item['source']}</span></div>
                </div>
            </div>""")
        st.markdown("".join(cards), unsafe_allow_html=True)

    st.markdown('<div class="nx-divider"></div>', unsafe_allow_html=True)

# ── FİLTRELER ────────────────────────────────────────────────────────────────
f1, f2, f3 = st.columns([2.5, 3.5, 2])
with f1:
    sentiment = st.pills(
        "Duygu", ["Hepsi", "Positive", "Negative", "Neutral"],
        default="Hepsi", label_visibility="collapsed",
    )
with f2:
    selected_sources = st.multiselect(
        "Kaynaklar", fetch_sources(),
        placeholder="Tüm kaynaklar…",
        label_visibility="collapsed",
    )
with f3:
    sort_by = st.segmented_control(
        "Sıralama", ["Yeni", "↑ Skor", "↓ Skor"],
        default="Yeni", label_visibility="collapsed",
    )

# ── VERİ ─────────────────────────────────────────────────────────────────────
news, error = fetch_news(st.session_state.limit)
if error:
    st.error(f"⚠ {error}")
    st.stop()

df = pd.DataFrame(news or [])
if df.empty:
    st.info("Haber bulunamadı. Ayarlar menüsünden 'Tüm Kaynakları Çek' butonuna bas.")
    st.stop()

df["created_at_dt"] = pd.to_datetime(df["created_at"])
df["sentiment_score"] = df["sentiment_score"].fillna(0)
df["sentiment_label"] = df["sentiment_label"].fillna("Neutral")

# Filtreler
sentiment = sentiment or "Hepsi"
if sentiment != "Hepsi":
    df = df[df["sentiment_label"] == sentiment]
if selected_sources:
    df = df[df["source"].isin(selected_sources)]

# Sıralama
sort_by = sort_by or "Yeni"
if sort_by == "↑ Skor":
    df = df.sort_values("sentiment_score", ascending=False)
elif sort_by == "↓ Skor":
    df = df.sort_values("sentiment_score", ascending=True)
else:
    df = df.sort_values("created_at_dt", ascending=False)

# Durum çubuğu
now_str = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
src_count = df["source"].nunique()
st.markdown(f"""
<div class="nx-status">
    <span class="nx-dot"></span>
    <span>CANLI</span>&nbsp;·&nbsp;
    <span>{len(df)} haber</span>&nbsp;·&nbsp;
    <span>{src_count} kaynak</span>&nbsp;·&nbsp;
    <span>{now_str}</span>
</div>
""", unsafe_allow_html=True)

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
        <div class="kpi-label">Toplam Haber</div>
        <div class="kpi-value">{total}</div>
        <div class="kpi-sub">{src_count} aktif kaynak</div>
    </div>
    <div class="kpi-card pos">
        <div class="kpi-label">Pozitif</div>
        <div class="kpi-value">{pos_pct}<span class="kpi-unit">%</span></div>
        <div class="kpi-sub">{pos_n} haber</div>
    </div>
    <div class="kpi-card neg">
        <div class="kpi-label">Negatif</div>
        <div class="kpi-value">{neg_pct}<span class="kpi-unit">%</span></div>
        <div class="kpi-sub">{neg_n} haber</div>
    </div>
    <div class="kpi-card neu">
        <div class="kpi-label">Ort. Duygu Skoru</div>
        <div class="kpi-value">{avg_score:+.2f}</div>
        <div class="kpi-sub">duygu indeksi</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── GRAFİKLER ─────────────────────────────────────────────────────────────────
cc1, cc2 = st.columns([1, 2])

with cc1:
    st.markdown('<div class="nx-section">Duygu Dağılımı</div>', unsafe_allow_html=True)
    pie_df = df["sentiment_label"].value_counts().reset_index()
    pie_df.columns = ["label", "count"]
    color_map = {"Positive": t["pos"], "Negative": t["neg"], "Neutral": t["neu"]}

    fig_pie = go.Figure(go.Pie(
        labels=pie_df["label"], values=pie_df["count"], hole=0.65,
        marker=dict(
            colors=[color_map.get(l, t["text2"]) for l in pie_df["label"]],
            line=dict(color=t["bg"], width=3),
        ),
        textfont=dict(family="DM Mono", size=10, color=t["text"]),
        hovertemplate="<b>%{label}</b><br>%{value} · %{percent}<extra></extra>",
    ))
    fig_pie.add_annotation(
        text=f"<b>{total}</b>", x=0.5, y=0.5, showarrow=False,
        font=dict(family="Syne", size=26, color=t["text"]),
    )
    fig_pie.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=5, b=5, l=5, r=5), height=230,
        legend=dict(
            font=dict(family="DM Mono", size=10, color=t["text2"]),
            bgcolor="rgba(0,0,0,0)", orientation="h",
            yanchor="bottom", y=-0.12, xanchor="center", x=0.5,
        ),
    )
    st.plotly_chart(fig_pie, width='stretch')

with cc2:
    st.markdown('<div class="nx-section">Kaynak Dağılımı</div>', unsafe_allow_html=True)
    src_counts = df["source"].value_counts().sort_values(ascending=True)
    src_sentiment = df.groupby("source")["sentiment_score"].mean()
    bar_colors = [
        t["pos"] if src_sentiment.get(s, 0) > 0.1
        else (t["neg"] if src_sentiment.get(s, 0) < -0.1 else t["neu"])
        for s in src_counts.index
    ]
    fig_src = go.Figure(go.Bar(
        x=src_counts.values,
        y=src_counts.index,
        orientation="h",
        marker=dict(color=bar_colors, line=dict(width=0)),
        text=src_counts.values,
        textposition="outside",
        textfont=dict(family="DM Mono", size=9, color=t["text2"]),
        hovertemplate="<b>%{y}</b><br>%{x} haber<extra></extra>",
    ))
    fig_src.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=5, b=5, l=5, r=45), height=230,
        xaxis=dict(showgrid=True, gridcolor=t["grid"], zeroline=False,
                   tickfont=dict(family="DM Mono", size=9, color=t["text3"])),
        yaxis=dict(showgrid=False, zeroline=False,
                   tickfont=dict(family="DM Mono", size=9, color=t["text2"])),
    )
    st.plotly_chart(fig_src, width='stretch')

# ── HABERLER ──────────────────────────────────────────────────────────────────
st.markdown('<div class="nx-section">Son Haberler</div>', unsafe_allow_html=True)

if df.empty:
    st.info("Filtre kriterlerine uyan haber bulunamadı.")
else:
    cards = []
    for _, row in df.iterrows():
        label   = row.get("sentiment_label", "Neutral") or "Neutral"
        score   = float(row.get("sentiment_score", 0) or 0)
        sc      = score_cls(score)
        title   = row.get("title", "—")
        url     = row.get("url", "#")
        summary = (row.get("summary") or row.get("content", ""))[:180]
        source  = row.get("source", "—")
        age     = rel_time(row.get("created_at", ""))
        cards.append(f"""
        <div class="nx-card">
            <div class="nx-score">
                <div class="nx-score-val {sc}">{score:+.1f}</div>
                <div class="nx-score-lbl">SKOR</div>
            </div>
            <div class="nx-body">
                <div class="nx-title"><a href="{url}" target="_blank">{title}</a></div>
                <div class="nx-summary">{summary}</div>
                <div class="nx-meta">
                    <span class="nx-source">{source}</span>
                    <span>{age}</span>
                </div>
            </div>
            <div class="nx-badge">
                <div class="nx-badge-inner badge-{label}">{label}</div>
            </div>
        </div>""")
    st.markdown("".join(cards), unsafe_allow_html=True)

# ── OTOMATİK YENİLEME ────────────────────────────────────────────────────────
if st.session_state.auto_refresh:
    time.sleep(30)
    st.cache_data.clear()
    st.rerun()
