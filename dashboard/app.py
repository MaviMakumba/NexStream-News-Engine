import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timezone
import time
import os

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
API_KEY  = os.getenv("API_KEY", "dev-key-change-me")

_SOURCES_FALLBACK = [
    "TRT Haber", "BBC Türkçe", "Hürriyet", "Hürriyet Spor",
    "Sabah", "CNN Türk", "Sözcü", "Habertürk", "HT Spor",
    "BBC Technology", "BBC Sport",
]

@st.cache_data(ttl=30)
def fetch_health():
    try:
        r = requests.get(f"{API_BASE}/health", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

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

LANGS = {
    "TR": {
        "settings":        "⚙ Ayarlar",
        "language":        "Dil",
        "theme":           "Tema",
        "data_pull":       "VERİ ÇEKME",
        "fetch_all":       "⚡ Tüm Kaynakları Çek",
        "fetch_single":    "Tek kaynak çek",
        "source":          "Kaynak",
        "fetch_btn":       "Çek",
        "fetch_queued":    "kaynak Kafka kuyruğuna alındı — haberler 1–3 dk içinde görünür",
        "fetch_ok":        "✓ Tamamlandı",
        "fetch_err":       "✗ Hata",
        "vector_index":    "VEKTÖR İNDEKS",
        "reindex_btn":     "⟳ Yeniden İndeksle",
        "reindex_ok":      "haber",
        "view":            "GÖRÜNÜM",
        "limit_label":     "Haber limiti",
        "auto_refresh":    "Otomatik yenile (30s)",
        "search_ph":       "Anlamsal arama… örn. 'yapay zeka', 'Beşiktaş maç sonucu'",
        "search_btn":      "Ara",
        "search_close":    "× Kapat",
        "search_title":    "Arama Sonuçları",
        "search_none":     "Sonuç bulunamadı. Ayarlar > Yeniden İndeksle butonuna bas.",
        "search_err":      "API'ye bağlanılamadı",
        "hist_tooltip":    "sonuç",
        "sentiment_lbl":   "Duygu",
        "sent_all":        "Hepsi",
        "sources_ph":      "Tüm kaynaklar…",
        "sort_lbl":        "Sıralama",
        "sort_new":        "Yeni",
        "sort_high":       "↑ Skor",
        "sort_low":        "↓ Skor",
        "status_live":     "CANLI",
        "status_articles": "haber",
        "status_sources":  "kaynak",
        "kpi_total":       "Toplam Haber",
        "kpi_pos":         "Pozitif",
        "kpi_neg":         "Negatif",
        "kpi_avg":         "Ort. Duygu Skoru",
        "kpi_sub_total":   "aktif kaynak",
        "kpi_sub_score":   "duygu indeksi",
        "chart_pie":       "Duygu Dağılımı",
        "chart_src":       "Kaynak Bazlı Duygu",
        "legend_pos":      "Pozitif",
        "legend_neu":      "Nötr",
        "legend_neg":      "Negatif",
        "section_news":    "Son Haberler",
        "no_news":         "Haber bulunamadı. Ayarlar > 'Tüm Kaynakları Çek' butonuna bas.",
        "no_filter":       "Filtre kriterlerine uyan haber bulunamadı.",
        "api_err":         "API'ye bağlanılamadı",
        "score_lbl":       "SKOR",
        "match_lbl":       "EŞLEŞME",
        "detail_full":     "Tam içeriği gör",
        "detail_go":       "🔗 Habere Git",
        "detail_empty":    "İçerik mevcut değil.",
    },
    "EN": {
        "settings":        "⚙ Settings",
        "language":        "Language",
        "theme":           "Theme",
        "data_pull":       "DATA PULL",
        "fetch_all":       "⚡ Fetch All Sources",
        "fetch_single":    "Fetch single source",
        "source":          "Source",
        "fetch_btn":       "Fetch",
        "fetch_queued":    "sources queued — articles appear in 1–3 min",
        "fetch_ok":        "✓ Done",
        "fetch_err":       "✗ Error",
        "vector_index":    "VECTOR INDEX",
        "reindex_btn":     "⟳ Reindex",
        "reindex_ok":      "articles",
        "view":            "VIEW",
        "limit_label":     "Article limit",
        "auto_refresh":    "Auto refresh (30s)",
        "search_ph":       "Semantic search… e.g. 'AI developments', 'match result'",
        "search_btn":      "Search",
        "search_close":    "× Close",
        "search_title":    "Search Results",
        "search_none":     "No results. Try Settings > Reindex first.",
        "search_err":      "Cannot reach API",
        "hist_tooltip":    "results",
        "sentiment_lbl":   "Sentiment",
        "sent_all":        "All",
        "sources_ph":      "All sources…",
        "sort_lbl":        "Sort",
        "sort_new":        "New",
        "sort_high":       "↑ Score",
        "sort_low":        "↓ Score",
        "status_live":     "LIVE",
        "status_articles": "articles",
        "status_sources":  "sources",
        "kpi_total":       "Total Articles",
        "kpi_pos":         "Positive",
        "kpi_neg":         "Negative",
        "kpi_avg":         "Avg Sentiment",
        "kpi_sub_total":   "active sources",
        "kpi_sub_score":   "sentiment index",
        "chart_pie":       "Sentiment Distribution",
        "chart_src":       "Source Sentiment",
        "legend_pos":      "Positive",
        "legend_neu":      "Neutral",
        "legend_neg":      "Negative",
        "section_news":    "Latest Articles",
        "no_news":         "No articles. Settings > 'Fetch All Sources'.",
        "no_filter":       "No articles match the current filters.",
        "api_err":         "Cannot reach API",
        "score_lbl":       "SCORE",
        "match_lbl":       "MATCH",
        "detail_full":     "View full content",
        "detail_go":       "🔗 Open Article",
        "detail_empty":    "No content available.",
    },
}

# ── SESSION STATE ─────────────────────────────────────────────────────────────
for k, v in [
    ("theme", "Midnight"), ("lang", "TR"), ("limit", 50), ("auto_refresh", False),
    ("search_results", None), ("search_error", None),
    ("search_history", []), ("pending_query", None), ("pending_n", 10),
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
        r = requests.post(
            f"{API_BASE}/news/scrape",
            json={"source": source},
            headers={"X-Api-Key": API_KEY},
            timeout=10,
        )
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
        r = requests.post(
            f"{API_BASE}/news/reindex",
            headers={"X-Api-Key": API_KEY},
            timeout=120,
        )
        r.raise_for_status()
        return True, r.json()
    except Exception as e:
        return False, {"error": str(e)}

def rel_time(dt_str, lang="TR"):
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        s = int((datetime.now(timezone.utc) - dt).total_seconds())
        if lang == "TR":
            if s < 60:    return f"{s}sn"
            if s < 3600:  return f"{s // 60}dk"
            if s < 86400: return f"{s // 3600}sa"
            return f"{s // 86400}g"
        else:
            if s < 60:    return f"{s}s"
            if s < 3600:  return f"{s // 60}m"
            if s < 86400: return f"{s // 3600}h"
            return f"{s // 86400}d"
    except Exception:
        return dt_str

def score_cls(v):
    if v is None: return "neu"
    return "pos" if v > 0.1 else ("neg" if v < -0.1 else "neu")

def _add_to_history(query, n, count):
    hist = [h for h in st.session_state.search_history if h["query"] != query]
    hist.insert(0, {"query": query, "n": n, "count": count})
    st.session_state.search_history = hist[:8]

# ── DETAIL DIALOG ─────────────────────────────────────────────────────────────
@st.dialog("Haber Detayı · Article Detail", width="large")
def show_detail(article):
    L = LANGS[st.session_state.lang]
    title   = article.get("title", "—")
    url     = article.get("url") or ""
    source  = article.get("source", "—")
    label   = article.get("sentiment_label", "Neutral") or "Neutral"
    score   = float(article.get("sentiment_score") or 0)
    content = article.get("content") or article.get("summary") or ""
    created = article.get("published_at") or article.get("created_at", "")
    sc      = score_cls(score)

    st.markdown(f"""
<div style="margin-bottom:1.2rem">
  <div style="font-family:'Syne',sans-serif;font-size:1.05rem;font-weight:700;
              color:var(--text);line-height:1.5;margin-bottom:0.75rem">{title}</div>
  <div style="display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap;font-size:0.65rem">
    <span class="nx-source">{source}</span>
    <span class="nx-badge-inner badge-{label}">{label}</span>
    <span class="nx-score-val {sc}" style="font-size:0.85rem">{score:+.2f}</span>
    <span style="color:var(--text3)">{rel_time(created, st.session_state.lang)}</span>
  </div>
</div>
<hr style="border:none;border-top:1px solid var(--border);margin:0.75rem 0"/>
<div style="font-size:0.78rem;color:var(--text2);line-height:1.85;white-space:pre-wrap">{content or L["detail_empty"]}</div>
""", unsafe_allow_html=True)

    if url:
        st.link_button(L["detail_go"], url, width="stretch")

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
[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] {{ display:none !important; }}
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

# Dil kısayolu — her render'da güncel
L = LANGS[st.session_state.lang]

# ── HEADER ────────────────────────────────────────────────────────────────────
h1, _, h3 = st.columns([3, 5, 2])

with h1:
    st.markdown('<div class="nx-logo">Nex<span>Stream</span><small>· News Engine</small></div>', unsafe_allow_html=True)

with h3:
    with st.popover(L["settings"], width='stretch'):
        st.selectbox(L["language"], ["TR", "EN"],
            index=0 if st.session_state.lang == "TR" else 1,
            key="lang")

        st.selectbox(L["theme"], list(THEMES.keys()),
            index=list(THEMES.keys()).index(st.session_state.theme),
            key="theme")

        st.divider()
        st.caption(L["data_pull"])
        _sources = fetch_sources()
        if st.button(L["fetch_all"], width='stretch'):
            bar = st.progress(0, text="…")
            for i, src in enumerate(_sources):
                do_scrape(src)
                bar.progress((i + 1) / len(_sources), text=src)
            bar.empty()
            st.success(f"✓ {len(_sources)} {L['fetch_queued']}")

        with st.expander(L["fetch_single"]):
            src_sel = st.selectbox(L["source"], _sources, label_visibility="collapsed", key="src_single")
            if st.button(L["fetch_btn"], key="btn_single"):
                ok = do_scrape(src_sel)
                if ok:
                    st.cache_data.clear()
                    st.success(L["fetch_ok"])
                else:
                    st.error(L["fetch_err"])

        st.divider()
        st.caption(L["vector_index"])
        if st.button(L["reindex_btn"], width='stretch'):
            with st.spinner("…"):
                ok, res = do_reindex()
            if ok:
                st.success(f"✓ {res.get('indexed', 0)}/{res.get('total', 0)} {L['reindex_ok']}")
            else:
                st.error(str(res))

        st.divider()
        st.caption(L["view"])
        st.select_slider(L["limit_label"], options=[25, 50, 100, 200], key="limit")
        st.toggle(L["auto_refresh"], key="auto_refresh")

st.markdown('<div class="nx-divider"></div>', unsafe_allow_html=True)

# ── SEARCH ────────────────────────────────────────────────────────────────────

# History chip tıklandıysa pending_query dolu gelir
if st.session_state.pending_query is not None:
    _pq = st.session_state.pending_query
    _pn = st.session_state.pending_n
    st.session_state.pending_query = None
    st.session_state["_search_input"] = _pq
    with st.spinner("…"):
        _res, _err = do_search(_pq, _pn)
    st.session_state.search_results = _res
    st.session_state.search_error   = _err
    _add_to_history(_pq, _pn, len(_res))

sc1, sc2, sc3 = st.columns([6, 1, 1])
with sc1:
    query = st.text_input(
        "search",
        placeholder=L["search_ph"],
        label_visibility="collapsed",
        key="_search_input",
    )
with sc2:
    n_res = st.selectbox("n", [5, 10, 20], index=1, label_visibility="collapsed")
with sc3:
    search_btn = st.button(L["search_btn"], width='stretch')

if search_btn:
    if query.strip():
        with st.spinner("…"):
            results, err = do_search(query.strip(), n_res)
        st.session_state.search_results = results
        st.session_state.search_error   = err
        _add_to_history(query.strip(), n_res, len(results))
    else:
        st.session_state.search_results = None
        st.session_state.search_error   = None

# ── SEARCH HISTORY ────────────────────────────────────────────────────────────
if st.session_state.search_history:
    hist = st.session_state.search_history
    n_h  = min(len(hist), 6)
    _spacer_weight = max(1, 12 - n_h * 2)
    hist_cols = st.columns([2] * n_h + [_spacer_weight])
    for i, h in enumerate(hist[:n_h]):
        with hist_cols[i]:
            lbl = h["query"] if len(h["query"]) <= 13 else h["query"][:11] + "…"
            if st.button(f"↺ {lbl}", key=f"hist_{i}",
                         help=f"{h['query']} · {h['count']} {L['hist_tooltip']}"):
                st.session_state.pending_query = h["query"]
                st.session_state.pending_n     = h["n"]
                st.rerun()

# ── SEARCH RESULTS ────────────────────────────────────────────────────────────
if st.session_state.search_results is not None:
    rc1, rc2 = st.columns([5, 1])
    with rc1:
        st.markdown(
            f'<div class="nx-section">{L["search_title"]} · {len(st.session_state.search_results)}</div>',
            unsafe_allow_html=True,
        )
    with rc2:
        if st.button(L["search_close"], width='stretch'):
            st.session_state.search_results = None
            st.rerun()

    if st.session_state.search_error:
        st.error(f"⚠ {st.session_state.search_error}")
    elif not st.session_state.search_results:
        st.info(L["search_none"])
    else:
        for i, item in enumerate(st.session_state.search_results):
            pct     = int(item["score"] * 100)
            summary = (item.get("summary") or item.get("content") or "")[:200]
            col_card, col_det = st.columns([11, 1])
            with col_card:
                st.markdown(f"""
<div class="nx-card">
  <div class="nx-score">
    <div class="nx-score-val neu">{pct}<span style="font-size:0.65rem">%</span></div>
    <div class="nx-score-lbl">{L["match_lbl"]}</div>
  </div>
  <div class="nx-body">
    <div class="nx-title"><a href="{item['url']}" target="_blank">{item['title']}</a></div>
    <div class="nx-summary">{summary}</div>
    <div class="nx-meta"><span class="nx-source">{item['source']}</span></div>
  </div>
</div>""", unsafe_allow_html=True)
            with col_det:
                if st.button("›", key=f"sd_{i}", help=L["detail_full"]):
                    show_detail(item)

    st.markdown('<div class="nx-divider"></div>', unsafe_allow_html=True)

# ── FİLTRELER ────────────────────────────────────────────────────────────────
f1, f2, f3 = st.columns([2.5, 3.5, 2])
with f1:
    sentiment = st.pills(
        L["sentiment_lbl"],
        [L["sent_all"], "Positive", "Negative", "Neutral"],
        default=L["sent_all"], label_visibility="collapsed",
    )
with f2:
    selected_sources = st.multiselect(
        L["sources_ph"], fetch_sources(),
        placeholder=L["sources_ph"],
        label_visibility="collapsed",
    )
with f3:
    sort_by = st.segmented_control(
        L["sort_lbl"],
        [L["sort_new"], L["sort_high"], L["sort_low"]],
        default=L["sort_new"], label_visibility="collapsed",
    )

# ── VERİ ─────────────────────────────────────────────────────────────────────
news, error = fetch_news(st.session_state.limit)
if error:
    st.error(f"⚠ {L['api_err']}: {error}")
    st.stop()

df = pd.DataFrame(news or [])
if df.empty:
    st.info(L["no_news"])
    st.stop()

df["created_at_dt"]   = pd.to_datetime(df["created_at"])
df["sentiment_score"] = df["sentiment_score"].fillna(0)
df["sentiment_label"] = df["sentiment_label"].fillna("Neutral")

sentiment = sentiment or L["sent_all"]
if sentiment != L["sent_all"]:
    df = df[df["sentiment_label"] == sentiment]
if selected_sources:
    df = df[df["source"].isin(selected_sources)]

sort_by = sort_by or L["sort_new"]
if sort_by == L["sort_high"]:
    df = df.sort_values("sentiment_score", ascending=False)
elif sort_by == L["sort_low"]:
    df = df.sort_values("sentiment_score", ascending=True)
else:
    df = df.sort_values("created_at_dt", ascending=False)

now_str   = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
src_count = df["source"].nunique()
health    = fetch_health()

def _dot(status):
    return f'<span style="color:{"#2dce89" if status=="ok" else "#f5365c"};font-size:0.7rem">●</span>'

if health:
    h_db     = _dot(health.get("db", "error"))
    h_kafka  = _dot(health.get("kafka", "error"))
    h_chroma = _dot(health.get("chromadb", "error"))
    indexed  = health.get("indexed_articles", 0)
    health_html = (
        f'&nbsp;·&nbsp;{h_db} DB'
        f'&nbsp;{h_kafka} Kafka'
        f'&nbsp;{h_chroma} Chroma'
        f'&nbsp;<span style="color:var(--text3)">({indexed:,} vektör)</span>'
    )
else:
    health_html = ""

st.markdown(f"""
<div class="nx-status">
  <span class="nx-dot"></span>
  <span>{L["status_live"]}</span>&nbsp;·&nbsp;
  <span>{len(df)} {L["status_articles"]}</span>&nbsp;·&nbsp;
  <span>{src_count} {L["status_sources"]}</span>
  {health_html}&nbsp;·&nbsp;
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
    <div class="kpi-label">{L["kpi_total"]}</div>
    <div class="kpi-value">{total}</div>
    <div class="kpi-sub">{src_count} {L["kpi_sub_total"]}</div>
  </div>
  <div class="kpi-card pos">
    <div class="kpi-label">{L["kpi_pos"]}</div>
    <div class="kpi-value">{pos_pct}<span class="kpi-unit">%</span></div>
    <div class="kpi-sub">{pos_n} {L["status_articles"]}</div>
  </div>
  <div class="kpi-card neg">
    <div class="kpi-label">{L["kpi_neg"]}</div>
    <div class="kpi-value">{neg_pct}<span class="kpi-unit">%</span></div>
    <div class="kpi-sub">{neg_n} {L["status_articles"]}</div>
  </div>
  <div class="kpi-card neu">
    <div class="kpi-label">{L["kpi_avg"]}</div>
    <div class="kpi-value">{avg_score:+.2f}</div>
    <div class="kpi-sub">{L["kpi_sub_score"]}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── GRAFİKLER ─────────────────────────────────────────────────────────────────
cc1, cc2 = st.columns([1, 2])

with cc1:
    st.markdown(f'<div class="nx-section">{L["chart_pie"]}</div>', unsafe_allow_html=True)
    pie_df    = df["sentiment_label"].value_counts().reset_index()
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
    st.markdown(f'<div class="nx-section">{L["chart_src"]}</div>', unsafe_allow_html=True)

    src_sent = df.groupby(["source", "sentiment_label"]).size().unstack(fill_value=0)
    for col in ["Positive", "Neutral", "Negative"]:
        if col not in src_sent.columns:
            src_sent[col] = 0
    src_sent = src_sent.sort_values("Positive", ascending=True)

    fig_src = go.Figure()
    fig_src.add_trace(go.Bar(
        name=L["legend_pos"], y=src_sent.index, x=src_sent["Positive"],
        orientation="h", marker=dict(color=t["pos"], line=dict(width=0)),
        hovertemplate="<b>%{y}</b><br>" + L["legend_pos"] + ": %{x}<extra></extra>",
    ))
    fig_src.add_trace(go.Bar(
        name=L["legend_neu"], y=src_sent.index, x=src_sent["Neutral"],
        orientation="h", marker=dict(color=t["neu"], line=dict(width=0)),
        hovertemplate="<b>%{y}</b><br>" + L["legend_neu"] + ": %{x}<extra></extra>",
    ))
    fig_src.add_trace(go.Bar(
        name=L["legend_neg"], y=src_sent.index, x=src_sent["Negative"],
        orientation="h", marker=dict(color=t["neg"], line=dict(width=0)),
        hovertemplate="<b>%{y}</b><br>" + L["legend_neg"] + ": %{x}<extra></extra>",
    ))
    fig_src.update_layout(
        barmode="stack",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=5, b=5, l=5, r=15), height=230,
        xaxis=dict(showgrid=True, gridcolor=t["grid"], zeroline=False,
                   tickfont=dict(family="DM Mono", size=9, color=t["text3"])),
        yaxis=dict(showgrid=False, zeroline=False,
                   tickfont=dict(family="DM Mono", size=9, color=t["text2"])),
        legend=dict(
            font=dict(family="DM Mono", size=9, color=t["text2"]),
            bgcolor="rgba(0,0,0,0)", orientation="h",
            yanchor="bottom", y=-0.3, xanchor="center", x=0.5,
        ),
    )
    st.plotly_chart(fig_src, width='stretch')

# ── HABERLER ──────────────────────────────────────────────────────────────────
st.markdown(f'<div class="nx-section">{L["section_news"]}</div>', unsafe_allow_html=True)

if df.empty:
    st.info(L["no_filter"])
else:
    for i, (_, row) in enumerate(df.iterrows()):
        label   = row.get("sentiment_label", "Neutral") or "Neutral"
        score   = float(row.get("sentiment_score") or 0)
        sc      = score_cls(score)
        title   = row.get("title", "—")
        url     = row.get("url", "#")
        summary = (row.get("summary") or row.get("content") or "")[:180]
        source  = row.get("source", "—")
        age_dt  = row.get("published_at") or row.get("created_at", "")
        age     = rel_time(age_dt, st.session_state.lang)

        col_card, col_det = st.columns([11, 1])
        with col_card:
            st.markdown(f"""
<div class="nx-card">
  <div class="nx-score">
    <div class="nx-score-val {sc}">{score:+.1f}</div>
    <div class="nx-score-lbl">{L["score_lbl"]}</div>
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
</div>""", unsafe_allow_html=True)
        with col_det:
            if st.button("›", key=f"d_{i}", help=L["detail_full"]):
                show_detail(row.to_dict())

# ── OTOMATİK YENİLEME ────────────────────────────────────────────────────────
if st.session_state.auto_refresh:
    time.sleep(30)
    st.cache_data.clear()
    st.rerun()
