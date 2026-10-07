import threading
import time

from src.application.services.evidence_enricher import EvidenceEnricher
from src.domain.models.article import Article
from src.domain.ports.article_text_port import ArticleTextPort
from src.domain.ports.embedding_port import EmbeddingPort

INJURY = "Kulüp doktoru oyuncunun sakatlığının ciddi olduğunu ve üç hafta sahalardan uzak kalacağını söyledi."
FILLER = "Stadyumun çevresindeki otopark düzenlemeleri ve bilet satış noktaları hakkında genel bilgilendirme yapıldı."


def _article(i, url="auto"):
    a = Article(title=f"T{i}", source="S", url=f"https://s.example/{i}" if url == "auto" else url, content="teaser")
    a.id = i
    return a


class FakeFetcher(ArticleTextPort):
    def __init__(self, texts):
        self.texts, self.calls = texts, []

    def fetch(self, url):
        self.calls.append(url)
        return self.texts.get(url)


class KeywordEmbedder(EmbeddingPort):
    """'sakat' geçen metin [1,0], geçmeyen [0,1] — deterministik."""
    def embed_text(self, text):
        return [1.0, 0.0] if "sakat" in text.lower() else [0.0, 1.0]

    def embed_batch(self, texts):
        return [self.embed_text(t) for t in texts]


class BrokenEmbedder(KeywordEmbedder):
    def embed_batch(self, texts):
        raise RuntimeError("embedder down")


def _enricher(fetcher, embedder=None, **kw):
    kw.setdefault("top_n", 2)
    kw.setdefault("passage_token_budget", 450)
    kw.setdefault("total_timeout_seconds", 5.0)
    return EvidenceEnricher(fetcher, embedder or KeywordEmbedder(), **kw)


def test_selects_question_relevant_passage_from_full_text():
    text = f"{FILLER}\n\n{INJURY}\n\n{FILLER} Ek bilgi."
    out = _enricher(FakeFetcher({"https://s.example/1": text}), passage_token_budget=40).enrich(
        "Oyuncu sakatlıktan ne zaman döner?", [_article(1)]
    )
    assert "üç hafta" in out[1]
    assert "otopark" not in out[1]


def test_only_top_n_articles_are_fetched():
    fetcher = FakeFetcher({f"https://s.example/{i}": INJURY for i in (1, 2, 3)})
    out = _enricher(fetcher, top_n=2).enrich("sakatlık?", [_article(1), _article(2), _article(3)])
    assert sorted(out) == [1, 2]
    assert sorted(fetcher.calls) == ["https://s.example/1", "https://s.example/2"]


def test_failed_fetch_and_missing_url_are_omitted_not_errors():
    fetcher = FakeFetcher({"https://s.example/2": INJURY})
    out = _enricher(fetcher).enrich("sakatlık?", [_article(1), _article(2), _article(3, url="")])
    assert list(out) == [2]


def test_embedder_failure_falls_back_to_no_enrichment():
    fetcher = FakeFetcher({"https://s.example/1": INJURY})
    assert _enricher(fetcher, BrokenEmbedder()).enrich("sakatlık?", [_article(1)]) == {}


def test_disabled_enricher_does_nothing():
    fetcher = FakeFetcher({"https://s.example/1": INJURY})
    assert _enricher(fetcher, enabled=False).enrich("sakatlık?", [_article(1)]) == {}
    assert fetcher.calls == []


def test_quotes_and_newlines_are_flattened_for_the_prompt():
    nasty = 'Doktor "üç hafta" dedi ve sakatlığın ciddiyeti hakkında ayrıntılı bilgi verdi.\nSakatlık durumu hakkında daha fazla bilgi "yakında" verilecek diye eklendi.'
    out = _enricher(FakeFetcher({"https://s.example/1": nasty})).enrich("sakatlık?", [_article(1)])
    assert '"' not in out[1] and "\n" not in out[1]
    assert "üç hafta" in out[1]


def test_articles_are_fetched_in_parallel():
    barrier = threading.Barrier(2, timeout=2.0)

    class BarrierFetcher(ArticleTextPort):
        def fetch(self, url):
            barrier.wait()  # iki çağrı AYNI ANDA içerideyse geçer; seri çalışırsa BrokenBarrierError
            return INJURY

    out = _enricher(BarrierFetcher()).enrich("sakatlık?", [_article(1), _article(2)])
    assert sorted(out) == [1, 2]


def test_total_timeout_returns_what_is_ready_without_waiting_for_slow_fetch():
    release = threading.Event()

    class SlowFetcher(ArticleTextPort):
        def fetch(self, url):
            if url.endswith("/1"):
                return INJURY
            release.wait(timeout=5.0)
            return INJURY

    started = time.monotonic()
    out = _enricher(SlowFetcher(), total_timeout_seconds=0.3).enrich("sakatlık?", [_article(1), _article(2)])
    elapsed = time.monotonic() - started
    release.set()
    assert list(out) == [1]
    assert elapsed < 2.0
