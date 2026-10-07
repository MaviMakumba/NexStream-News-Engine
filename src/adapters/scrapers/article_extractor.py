"""HTML → makale paragrafları. Kaynak başına özel kural YOK: genel bir paragraf-yoğunluğu
sezgisi (`<article>` varsa orası, yoksa en çok metin taşıyan paragraf grubu). Çıkmayan
kaynaklar `nexstream_article_fetch_total{result="too_short"}` ile görünür olur ve gerekirse
kaynak bazlı kural AYRI bir işte eklenir (spec: kapsam dışı).
"""

from bs4 import BeautifulSoup

_NOISE_TAGS = ["script", "style", "noscript", "nav", "aside", "footer", "header", "form", "iframe", "figure", "svg"]
_MIN_PARAGRAPH_CHARS = 40
_MIN_ARTICLE_SCOPE_CHARS = 200


def _clean(tag) -> str:
    return " ".join(tag.get_text(" ", strip=True).split())


def extract_article_text(html) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(_NOISE_TAGS):
        tag.decompose()

    # Birden çok <article> olabilir (ilgili haber kartları): en çok paragraf metni taşıyanı seç.
    scopes = [[t for t in (_clean(p) for p in a.find_all("p")) if len(t) >= _MIN_PARAGRAPH_CHARS] for a in soup.find_all("article")]
    best_scope = max(scopes, key=lambda texts: sum(len(t) for t in texts), default=[])
    if sum(len(t) for t in best_scope) >= _MIN_ARTICLE_SCOPE_CHARS:
        # Şablonlar gövdeyi reklam alanları etrafında birkaç <div>'e böler: article içinde
        # ebeveyne göre gruplama doktor açıklaması gibi parçaları kaçırırdı, hepsini al.
        return "\n\n".join(best_scope)

    paragraphs = soup.find_all("p")

    groups: dict[int, list[str]] = {}
    for p in paragraphs:
        text = _clean(p)
        if len(text) < _MIN_PARAGRAPH_CHARS:
            continue
        groups.setdefault(id(p.parent), []).append(text)
    if not groups:
        return ""
    best = max(groups.values(), key=lambda texts: sum(len(t) for t in texts))
    return "\n\n".join(best)
