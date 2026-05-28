import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timezone, timedelta
import os

_TZ_TR = timezone(timedelta(hours=3))

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

_SOURCES_FALLBACK = [
    "TRT Haber", "BBC Türkçe", "Hürriyet", "Hürriyet Spor",
    "Sabah", "CNN Türk", "Sözcü", "Habertürk", "HT Spor",
    "Anadolu Ajansı", "AA Ekonomi",
    "BBC Technology", "BBC Sport",
    "Guardian Tech", "TechCrunch", "Hacker News", "The Verge",
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
        "border2": "#2a3f52", "text": "#c8d6e0", "text2": "#6a7a8a",
        "text3": "#3d5060", "accent": "#3b9eff",
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
        "border2": "#3d3b52", "text": "#e2dff0", "text2": "#7e7a9a",
        "text3": "#5a5870", "accent": "#a78bfa",
        "pos": "#34d399", "neg": "#f87171", "neu": "#fbbf24",
        "pos_bg": "#0c2017", "neg_bg": "#2d1515", "neu_bg": "#2a1f08",
        "grid": "#1a1825",
    },
    "Dusk": {
        "bg": "#1e1e2e", "surface": "#27273a", "border": "#393952",
        "border2": "#4a4a68", "text": "#cdd6f4", "text2": "#a6adc8",
        "text3": "#6c7086", "accent": "#cba6f7",
        "pos": "#a6e3a1", "neg": "#f38ba8", "neu": "#f9e2af",
        "pos_bg": "#0a2010", "neg_bg": "#2a0a14", "neu_bg": "#241c08",
        "grid": "#27273a",
    },
    "Ocean": {
        "bg": "#071e35", "surface": "#0d2b47", "border": "#163854",
        "border2": "#1e4a6c", "text": "#b8d4ea", "text2": "#7098b8",
        "text3": "#3a6080", "accent": "#22d3ee",
        "pos": "#34d399", "neg": "#f87171", "neu": "#fbbf24",
        "pos_bg": "#05281a", "neg_bg": "#280a12", "neu_bg": "#221a06",
        "grid": "#0d2b47",
    },
}

LANGS = {
    "TR": {
        "settings":        "⚙ Ayarlar",
        "language":        "Dil",
        "theme":           "Tema",
        "limit_label":     "Haber sayısı",
        "refresh_lbl":     "Yenileme",
        "refresh_off":     "Kapalı",
        "search_ph":       "Anlamsal arama… örn. 'yapay zeka', 'Beşiktaş maç sonucu'",
        "search_btn":      "Ara",
        "search_close":    "× Kapat",
        "search_title":    "Arama Sonuçları",
        "search_none":     "Sonuç bulunamadı.",
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
        "no_news":         "Henüz haber yok — haberler otomatik olarak çekilir.",
        "no_filter":       "Filtre kriterlerine uyan haber bulunamadı.",
        "api_err":         "API'ye bağlanılamadı",
        "score_lbl":       "SKOR",
        "match_lbl":       "EŞLEŞME",
        "detail_full":     "Tam içeriği gör",
        "detail_go":       "🔗 Habere Git",
        "detail_empty":    "İçerik mevcut değil.",
        "topic_lbl":       "Konu",
        "topic_all":       "Hepsi",
        "trending_title":  "TREND",
        "health_vectors":  "vektör",
        "quality_lbl":     "Kalite",
        "quality_all":     "Tüm kalite",
        "quality_med":     "Orta+",
        "quality_high":    "Yüksek",
        "related_title":   "İlgili Haberler",
        "related_none":    "İlgili haber bulunamadı.",
        "q_score_lbl":     "Kalite",
        "cred_score_lbl":  "Güvenilirlik",
        "corrob_lbl":      "kaynak doğrulaması",
        "sentiments": {"Positive": "Pozitif", "Negative": "Negatif", "Neutral": "Nötr"},
        "topics": {
            "Technology": "Teknoloji", "Sports": "Spor", "Economy": "Ekonomi",
            "Politics": "Siyaset", "Health": "Sağlık", "Culture": "Kültür",
            "World": "Dünya", "Other": "Diğer",
        },
    },
    "EN": {
        "settings":        "⚙ Settings",
        "language":        "Language",
        "theme":           "Theme",
        "limit_label":     "Articles",
        "refresh_lbl":     "Refresh",
        "refresh_off":     "Off",
        "search_ph":       "Semantic search… e.g. 'AI developments', 'match result'",
        "search_btn":      "Search",
        "search_close":    "× Close",
        "search_title":    "Search Results",
        "search_none":     "No results found.",
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
        "no_news":         "No articles yet — articles are fetched automatically.",
        "no_filter":       "No articles match the current filters.",
        "api_err":         "Cannot reach API",
        "score_lbl":       "SCORE",
        "match_lbl":       "MATCH",
        "detail_full":     "View full content",
        "detail_go":       "🔗 Open Article",
        "detail_empty":    "No content available.",
        "topic_lbl":       "Topic",
        "topic_all":       "All",
        "trending_title":  "TRENDING",
        "health_vectors":  "vectors",
        "quality_lbl":     "Quality",
        "quality_all":     "All quality",
        "quality_med":     "Medium+",
        "quality_high":    "High",
        "related_title":   "Related Articles",
        "related_none":    "No related articles.",
        "q_score_lbl":     "Quality",
        "cred_score_lbl":  "Credibility",
        "corrob_lbl":      "source corroborations",
        "sentiments": {"Positive": "Positive", "Negative": "Negative", "Neutral": "Neutral"},
        "topics": {
            "Technology": "Technology", "Sports": "Sports", "Economy": "Economy",
            "Politics": "Politics", "Health": "Health", "Culture": "Culture",
            "World": "World", "Other": "Other",
        },
    },
}

# ── SESSION STATE ─────────────────────────────────────────────────────────────
for k, v in [
    ("theme", "Midnight"), ("lang", "TR"), ("limit", 50),
    ("search_results", None), ("search_error", None),
    ("search_history", []), ("pending_query", None), ("pending_n", 10),
    ("quality", "all"),
]:
    if k not in st.session_state:
        st.session_state[k] = v

# Kalite filtre eşikleri — segmented control label'i bu anahtarlara map'lenir
_QUALITY_THRESHOLDS = {"all": 0.0, "med": 0.4, "high": 0.6}

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

def do_search(query, n):
    try:
        r = requests.post(f"{API_BASE}/news/search", json={"query": query, "n_results": n}, timeout=15)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return [], "API'ye bağlanılamadı"
    except Exception as e:
        return [], str(e)

@st.cache_data(ttl=300)
def fetch_trending(hours=6, limit=8):
    try:
        r = requests.get(f"{API_BASE}/news/trending", params={"hours": hours, "limit": limit}, timeout=10)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)

@st.cache_data(ttl=120)
def fetch_related(article_id, limit=5):
    try:
        r = requests.get(f"{API_BASE}/news/{article_id}/related", params={"limit": limit}, timeout=8)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)

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
    summary = article.get("summary") or ""
    content = article.get("content") or ""
    created = article.get("published_at") or article.get("created_at", "")
    topic   = article.get("topic") or ""
    entities = article.get("entities") or {}
    quality = article.get("quality_score")
    cred    = article.get("credibility_score")
    corrob  = article.get("corroboration_count") or 0
    sc      = score_cls(score)

    label_display = L["sentiments"].get(label, label)
    topic_display = L["topics"].get(topic, topic) if topic else ""
    topic_html = f'<span class="nx-source" style="margin-left:0.25rem">{topic_display}</span>' if topic_display else ""

    _chip = "display:inline-block;padding:0.12rem 0.5rem;border-radius:5px;background:var(--border);color:var(--text2);font-size:0.55rem;font-weight:500"
    quality_chip = f'<span style="{_chip}">{L["q_score_lbl"]} {quality:.0%}</span>' if quality is not None else ""
    cred_chip    = f'<span style="{_chip}">{L["cred_score_lbl"]} {cred:.0%}</span>' if cred is not None else ""
    corrob_chip  = f'<span style="{_chip}">+{corrob} {L["corrob_lbl"]}</span>' if corrob else ""

    entity_chips = ""
    for etype in ("persons", "organizations", "locations"):
        for name in (entities.get(etype) or []):
            entity_chips += f'<span style="display:inline-block;padding:0.1rem 0.45rem;border-radius:4px;background:var(--border);color:var(--text2);font-size:0.55rem;margin:0.15rem 0.15rem 0 0">{name}</span>'

    st.markdown(f"""
<div style="margin-bottom:1.2rem">
  <div style="font-family:'Syne',sans-serif;font-size:1.05rem;font-weight:700;
              color:var(--text);line-height:1.5;margin-bottom:0.75rem">{title}</div>
  <div style="display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap;font-size:0.65rem">
    <span class="nx-source">{source}</span>{topic_html}
    <span class="nx-badge-inner badge-{label}">{label_display}</span>
    <span class="nx-score-val {sc}" style="font-size:0.85rem">{score:+.2f}</span>
    <span style="color:var(--text3)">{rel_time(created, st.session_state.lang)}</span>
    {quality_chip}{cred_chip}{corrob_chip}
  </div>
  {f'<div style="margin-top:0.6rem">{entity_chips}</div>' if entity_chips else ""}
</div>
<hr style="border:none;border-top:1px solid var(--border);margin:0.75rem 0"/>
""", unsafe_allow_html=True)

    if summary and content:
        st.markdown(f'<div style="font-size:0.82rem;color:var(--text);line-height:1.85;margin-bottom:0.5rem;font-weight:500">{summary}</div>', unsafe_allow_html=True)
        with st.expander(L["detail_full"]):
            st.markdown(f'<div style="font-size:0.75rem;color:var(--text2);line-height:1.85;white-space:pre-wrap">{content}</div>', unsafe_allow_html=True)
    elif summary:
        st.markdown(f'<div style="font-size:0.82rem;color:var(--text);line-height:1.85;margin-bottom:0.5rem;font-weight:500">{summary}</div>', unsafe_allow_html=True)
    elif content:
        st.markdown(f'<div style="font-size:0.78rem;color:var(--text2);line-height:1.85;white-space:pre-wrap">{content}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="font-size:0.78rem;color:var(--text2)">{L["detail_empty"]}</div>', unsafe_allow_html=True)

    # ── İlgili Haberler (v1.8) ──
    art_id = article.get("id")
    rid = None
    if art_id is not None:
        try:
            rid = int(art_id)
        except (ValueError, TypeError):
            rid = None
    if rid is not None:
        rel_data, _ = fetch_related(rid, 5)
        related = (rel_data or {}).get("related", [])
        if related:
            st.markdown(f'<div class="nx-section" style="margin-top:1.2rem">{L["related_title"]}</div>', unsafe_allow_html=True)
            _rchip = "display:inline-block;padding:0.08rem 0.4rem;border-radius:4px;background:var(--border);color:var(--text2);font-size:0.5rem;margin-right:0.2rem"
            rel_html = ""
            for rel in related:
                r_title = rel.get("title", "—")
                r_url   = rel.get("url") or "#"
                r_src   = rel.get("source", "—")
                r_topic = rel.get("topic") or ""
                r_topic_disp = L["topics"].get(r_topic, r_topic) if r_topic else ""
                r_topic_html = f'<span class="nx-source" style="font-size:0.5rem">{r_topic_disp}</span>' if r_topic_disp else ""
                r_overlap = rel.get("overlap", 0)
                shared_html = "".join(f'<span style="{_rchip}">{s}</span>' for s in (rel.get("shared_entities") or [])[:4])
                rel_html += f"""
<div style="background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:0.55rem 0.75rem;margin-bottom:0.4rem">
  <a href="{r_url}" target="_blank" style="text-decoration:none;color:var(--text);font-family:'Syne',sans-serif;font-size:0.76rem;font-weight:600;line-height:1.4">{r_title}</a>
  <div style="display:flex;align-items:center;gap:0.45rem;flex-wrap:wrap;margin-top:0.35rem;font-size:0.52rem;color:var(--text3)">
    <span class="nx-source" style="font-size:0.5rem">{r_src}</span>
    {r_topic_html}
    <span style="color:var(--accent);font-weight:700">⊕ {r_overlap}</span>
    {shared_html}
  </div>
</div>"""
            st.markdown(rel_html, unsafe_allow_html=True)

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
[data-testid="stAppViewContainer"],
[data-testid="stApp"],
[data-testid="stMain"],
.stApp, .main {{
    background-color:var(--bg) !important;
}}
[data-testid="stExpander"] {{
    background-color:var(--surface) !important;
    border-color:var(--border) !important;
}}
[data-testid="stPopover"] > div {{
    background-color:var(--surface) !important;
    border-color:var(--border) !important;
}}
div[data-modal-container="true"] > div {{
    background-color:var(--bg) !important;
}}
[data-baseweb="tag"] {{
    background-color:var(--border) !important;
    color:var(--text) !important;
}}
[data-baseweb="tag"] span {{
    color:var(--text) !important;
}}
label, .stSelectbox label, .stMultiSelect label {{
    color:var(--text2) !important;
}}
[data-testid="stMarkdownContainer"] p {{
    color:var(--text) !important;
}}
div[role="tablist"] button {{
    color:var(--text2) !important;
}}
div[role="tablist"] button[aria-selected="true"] {{
    color:var(--accent) !important;
}}
.stSelectbox > div > div {{
    background-color:var(--surface) !important;
    color:var(--text) !important;
    border-color:var(--border) !important;
}}
[data-baseweb="select"] > div {{
    background-color:var(--surface) !important;
    color:var(--text) !important;
}}
[data-baseweb="popover"] > div {{
    background-color:var(--surface) !important;
    border-color:var(--border) !important;
}}
[data-baseweb="menu"] {{
    background-color:var(--surface) !important;
}}
[data-baseweb="menu"] li {{
    background-color:var(--surface) !important;
    color:var(--text) !important;
}}
[data-baseweb="menu"] li:hover {{
    background-color:var(--border) !important;
}}
</style>
""", unsafe_allow_html=True)

# Dil kısayolu — her render'da güncel
L = LANGS[st.session_state.lang]
_SENT_DISPLAY = L["sentiments"]
_SENT_REVERSE = {v: k for k, v in _SENT_DISPLAY.items()}
_TOPIC_DISPLAY = L["topics"]
_TOPIC_REVERSE = {v: k for k, v in _TOPIC_DISPLAY.items()}

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
        # key'li segmented_control tek tıkla geçiş yapar. Seçili öğeye tekrar tıklayınca
        # Streamlit None döndürür (deselect). Widget'tan ÖNCE son geçerli değere sabitleyerek
        # hem 10'a düşmeyi hem boş-seçim titremesini (kırmızı kutu) hem de 2-tık gecikmesini önlüyoruz.
        if st.session_state.limit in (25, 50, 100, 200):
            st.session_state._limit_ok = st.session_state.limit
        else:
            st.session_state.limit = st.session_state.get("_limit_ok", 50)
        st.segmented_control(L["limit_label"], [25, 50, 100, 200], key="limit")

        _Q_LABELS = {"all": L["quality_all"], "med": L["quality_med"], "high": L["quality_high"]}
        _q_reverse = {v: k for k, v in _Q_LABELS.items()}
        # Aynı mantık: deselect (None) veya dil değişiminde geçerli label'a geri sabitle.
        if st.session_state.get("quality_sel") not in _Q_LABELS.values():
            st.session_state.quality_sel = _Q_LABELS.get(st.session_state.quality, L["quality_all"])
        st.segmented_control(L["quality_lbl"], list(_Q_LABELS.values()), key="quality_sel")
        st.session_state.quality = _q_reverse.get(st.session_state.quality_sel, "all")


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

# Form: hem "Ara" butonu hem de kutuda Enter submit eder (form_submit_button davranışı).
with st.form("search_form", clear_on_submit=False, border=False):
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
        search_btn = st.form_submit_button(L["search_btn"], width='stretch')

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
    _hist_labels = [h["query"] for h in st.session_state.search_history[:6]]
    _hist_sel = st.pills("history", _hist_labels, default=None, label_visibility="collapsed")
    if _hist_sel:
        _hist_match = next((h for h in st.session_state.search_history if h["query"] == _hist_sel), None)
        if _hist_match:
            st.session_state.pending_query = _hist_match["query"]
            st.session_state.pending_n = _hist_match["n"]
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
    st.stop()

# ── TRENDING ─────────────────────────────────────────────────────────────────
_trending_data, _trending_err = fetch_trending()
if _trending_data and _trending_data.get("entities"):
    _tent = _trending_data["entities"]
    _trend_labels = [f"{e['name']} ({e['count']})" for e in _tent]
    _trend_name_map = {f"{e['name']} ({e['count']})": e["name"] for e in _tent}
    st.markdown(
        f'<div style="font-family:\'Syne\',sans-serif;font-size:0.6rem;font-weight:700;'
        f'color:var(--accent);letter-spacing:0.1em;margin-bottom:-0.6rem">{L["trending_title"]}</div>',
        unsafe_allow_html=True,
    )
    _trend_sel = st.pills("trending", _trend_labels, default=None, label_visibility="collapsed")
    if _trend_sel:
        st.session_state.pending_query = _trend_name_map[_trend_sel]
        st.session_state.pending_n = 10
        st.rerun()

# ── FİLTRELER ────────────────────────────────────────────────────────────────
_SENT_OPTIONS = [L["sent_all"]] + list(_SENT_DISPLAY.values())
_TOPIC_OPTIONS = [L["topic_all"]] + list(_TOPIC_DISPLAY.values())

f1, f2, f3, f4 = st.columns([2, 2.5, 3, 2])
with f1:
    sentiment = st.pills(
        L["sentiment_lbl"],
        _SENT_OPTIONS,
        default=L["sent_all"], label_visibility="collapsed",
    )
with f2:
    topic_filter = st.pills(
        L["topic_lbl"],
        _TOPIC_OPTIONS,
        default=L["topic_all"], label_visibility="collapsed",
    )
with f3:
    selected_sources = st.multiselect(
        L["sources_ph"], fetch_sources(),
        placeholder=L["sources_ph"],
        label_visibility="collapsed",
    )
with f4:
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
    db_sentiment = _SENT_REVERSE.get(sentiment, sentiment)
    df = df[df["sentiment_label"] == db_sentiment]
topic_filter = topic_filter or L["topic_all"]
if topic_filter != L["topic_all"] and "topic" in df.columns:
    db_topic = _TOPIC_REVERSE.get(topic_filter, topic_filter)
    df = df[df["topic"] == db_topic]
if selected_sources:
    df = df[df["source"].isin(selected_sources)]
_q_threshold = _QUALITY_THRESHOLDS.get(st.session_state.quality, 0.0)
if _q_threshold > 0 and "quality_score" in df.columns:
    df = df[df["quality_score"].fillna(0) >= _q_threshold]

sort_by = sort_by or L["sort_new"]
if sort_by == L["sort_high"]:
    df = df.sort_values("sentiment_score", ascending=False)
elif sort_by == L["sort_low"]:
    df = df.sort_values("sentiment_score", ascending=True)
else:
    df = df.sort_values("created_at_dt", ascending=False)

now_str   = datetime.now(_TZ_TR).strftime("%H:%M")
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
        f'&nbsp;<span style="color:var(--text3)">({indexed:,} {L["health_vectors"]})</span>'
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
    pie_df["label_display"] = pie_df["label"].map(lambda x: _SENT_DISPLAY.get(x, x))
    color_map = {"Positive": t["pos"], "Negative": t["neg"], "Neutral": t["neu"]}

    fig_pie = go.Figure(go.Pie(
        labels=pie_df["label_display"], values=pie_df["count"], hole=0.65,
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
        label_display = _SENT_DISPLAY.get(label, label)
        score   = float(row.get("sentiment_score") or 0)
        sc      = score_cls(score)
        title   = row.get("title", "—")
        url     = row.get("url", "#")
        summary = (row.get("summary") or row.get("content") or "")[:180]
        source  = row.get("source", "—")
        topic   = row.get("topic") or ""
        topic_display = _TOPIC_DISPLAY.get(topic, topic) if topic else ""
        age_dt  = row.get("published_at") or row.get("created_at", "")
        age     = rel_time(age_dt, st.session_state.lang)
        topic_span = f'<span class="nx-source" style="font-size:0.52rem">{topic_display}</span>' if topic_display else ""

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
      {topic_span}
      <span>{age}</span>
    </div>
  </div>
  <div class="nx-badge">
    <div class="nx-badge-inner badge-{label}">{label_display}</div>
  </div>
</div>""", unsafe_allow_html=True)
        with col_det:
            if st.button("›", key=f"d_{i}", help=L["detail_full"]):
                show_detail(row.to_dict())

# Not: Eski `time.sleep(60)+cache_data.clear()+rerun` bloklayan otomatik yenileme kaldırıldı —
# script thread'ini bloklayıp tıklamaları geciktiriyor, her döngüde tüm cache'i silip sayıları
# zıplatıyordu. Veri tazeliği artık cache TTL'leriyle sağlanıyor (fetch_news ttl=30sn): herhangi
# bir etkileşimde otomatik tazelenir. Süreli canlı yenileme istenirse st.fragment(run_every=...) eklenir.
