import httpx

from src.adapters.api.metrics import article_fetch_total
from src.adapters.scrapers.article_text_fetcher import HttpArticleTextFetcher
from src.adapters.scrapers.http_identity import BROWSER_USER_AGENT
from src.adapters.scrapers.url_safety import UnsafeUrlError

P1 = "Kulüp doktoru oyuncunun sağ ayak bileğindeki sakatlığın ciddi olduğunu açıkladı bugün."
P2 = "Yıldız oyuncunun yaklaşık üç hafta sahalardan uzak kalması bekleniyor, tedavi sürüyor."
P3 = "Teknik direktör, takımın hafta sonu oynanacak derbiye eksik gireceğini söyledi."
PAGE = f"<html><head><meta charset='utf-8'></head><body><article><p>{P1}</p><p>{P2}</p><p>{P3}</p></article></body></html>"
HTML = {"content-type": "text/html; charset=utf-8"}


def _fetcher(handler, **kw):
    kw.setdefault("timeout_seconds", 4.0)
    kw.setdefault("max_bytes", 1_500_000)
    kw.setdefault("guard", lambda url: None)
    return HttpArticleTextFetcher(transport=httpx.MockTransport(handler), **kw)


def _count(result):
    return article_fetch_total.labels(result=result)._value.get()


def test_fetch_returns_article_text_and_sends_browser_user_agent():
    seen = {}

    def handler(request):
        seen["ua"] = request.headers["user-agent"]
        return httpx.Response(200, headers=HTML, content=PAGE.encode("utf-8"))

    before = _count("fetched")
    text = _fetcher(handler).fetch("https://site.example/haber")
    assert P2 in text and P1 in text
    assert seen["ua"] == BROWSER_USER_AGENT
    assert _count("fetched") == before + 1


def test_non_html_content_type_returns_none():
    before = _count("failed")
    f = _fetcher(lambda r: httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF-1.7"))
    assert f.fetch("https://site.example/x.pdf") is None
    assert _count("failed") == before + 1


def test_source_refusal_counts_as_blocked():
    before = _count("blocked")
    f = _fetcher(lambda r: httpx.Response(403, headers=HTML, content=b"denied"))
    assert f.fetch("https://waf.example/x") is None
    assert _count("blocked") == before + 1


def test_server_error_counts_as_failed():
    before = _count("failed")
    assert _fetcher(lambda r: httpx.Response(500, headers=HTML)).fetch("https://site.example/x") is None
    assert _count("failed") == before + 1


def test_network_error_returns_none():
    def handler(request):
        raise httpx.ConnectError("boom")

    assert _fetcher(handler).fetch("https://down.example/x") is None


def test_too_short_text_returns_none():
    before = _count("too_short")
    html = "<html><body><article><p>Çok kısa ama kırk karakteri aşan tek bir paragraf burada.</p></article></body></html>"
    assert _fetcher(lambda r: httpx.Response(200, headers=HTML, content=html.encode())).fetch("https://s.example/x") is None
    assert _count("too_short") == before + 1


def test_follows_redirects_and_guards_every_hop():
    guarded = []

    def handler(request):
        if request.url.path == "/start":
            return httpx.Response(302, headers={"location": "https://other.example/final"})
        return httpx.Response(200, headers=HTML, content=PAGE.encode("utf-8"))

    f = _fetcher(handler, guard=guarded.append)
    assert P1 in f.fetch("https://site.example/start")
    assert guarded == ["https://site.example/start", "https://other.example/final"]


def test_redirect_to_unsafe_target_is_blocked():
    def guard(url):
        if "internal" in url:
            raise UnsafeUrlError("özel adres")

    def handler(request):
        return httpx.Response(302, headers={"location": "http://internal.local/admin"})

    before = _count("blocked")
    assert _fetcher(handler, guard=guard).fetch("https://site.example/start") is None
    assert _count("blocked") == before + 1


def test_too_many_redirects_returns_none():
    def handler(request):
        return httpx.Response(302, headers={"location": "https://site.example/again"})

    assert _fetcher(handler).fetch("https://site.example/start") is None


def test_body_is_capped_at_max_bytes():
    filler = "<p>" + ("z" * 100) + "</p>"
    html = f"<html><body><article><p>{P1}</p><p>{P2}</p>{filler * 5}<p>SONRAKI_BOLUM_BURADA_BASLIYOR_ve_cok_uzun_devam_ediyor</p></article></body></html>"
    f = _fetcher(lambda r: httpx.Response(200, headers=HTML, content=html.encode("utf-8")), max_bytes=400)
    text = f.fetch("https://site.example/x")
    assert text is not None and "SONRAKI_BOLUM" not in text


class _Chunks(httpx.SyncByteStream):
    def __init__(self, chunks):
        self._chunks = chunks

    def __iter__(self):
        yield from self._chunks


def test_slow_body_is_cut_at_deadline():
    first = f"<html><body><article><p>{P1}</p><p>{P2}</p><p>{P3}</p>".encode("utf-8")
    second = "<p>IKINCI_PARCA_ASLA_OKUNMAMALI_cunku_sure_doldu_tamam_mi_peki</p></article></body></html>".encode("utf-8")
    ticks = {"t": 0.0}

    def clock():
        ticks["t"] += 3.0
        return ticks["t"]

    f = _fetcher(lambda r: httpx.Response(200, headers=HTML, stream=_Chunks([first, second])),
                 timeout_seconds=4.0, clock=clock)
    text = f.fetch("https://slow.example/x")
    assert text is not None and P1 in text and "IKINCI_PARCA" not in text


def test_deadline_is_checked_before_every_hop():
    requests = []

    def handler(request):
        requests.append(str(request.url))
        return httpx.Response(302, headers={"location": "https://site.example/second"})

    ticks = {"t": 0.0}

    def clock():
        ticks["t"] += 3.0
        return ticks["t"]

    f = _fetcher(handler, timeout_seconds=4.0, clock=clock)
    assert f.fetch("https://site.example/first") is None
    assert requests == ["https://site.example/first"]  # süre dolunca ikinci atlama HİÇ denenmez


def test_per_hop_timeout_is_the_remaining_time_not_the_full_budget():
    seen = []

    def handler(request):
        seen.append(request.extensions["timeout"]["read"])
        return httpx.Response(200, headers=HTML, content=PAGE.encode("utf-8"))

    ticks = {"t": 0.0}

    def clock():
        ticks["t"] += 1.0
        return ticks["t"]

    _fetcher(handler, timeout_seconds=4.0, clock=clock).fetch("https://site.example/x")
    assert 0 < seen[0] < 4.0


def test_compressed_responses_are_refused_and_identity_is_requested():
    import gzip
    seen = {}

    def handler(request):
        seen["ae"] = request.headers.get("accept-encoding")
        return httpx.Response(
            200,
            headers={**HTML, "content-encoding": "gzip"},
            content=gzip.compress(PAGE.encode("utf-8")),
        )

    before = _count("failed")
    assert _fetcher(handler).fetch("https://site.example/bomb") is None
    assert seen["ae"] == "identity"
    assert _count("failed") == before + 1
