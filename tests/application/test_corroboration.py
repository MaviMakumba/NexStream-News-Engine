from unittest.mock import MagicMock
from src.application.services.news_service import NewsService
from src.domain.models.article import Article


def _service():
    repo = MagicMock()
    return NewsService(repository=repo, analyzer=MagicMock()), repo


def _art(source, entities, article_id=1):
    return Article(id=article_id, title="t", source=source, url=f"u{source}{article_id}",
                   content="c", entities=entities)


_TWO = {"persons": ["Erdogan"], "organizations": ["NATO"], "locations": []}


def test_corroboration_counts_distinct_other_sources():
    service, repo = _service()
    repo.get_recent_articles_with_entities.return_value = [
        _art("CNN", _TWO, 2),
        _art("TRT", _TWO, 3),
        _art("CNN", _TWO, 4),  # second CNN — same source, not double counted
    ]
    assert service._count_corroboration(_art("BBC", _TWO)) == 2


def test_corroboration_excludes_same_source():
    service, repo = _service()
    repo.get_recent_articles_with_entities.return_value = [_art("BBC", _TWO, 2)]
    assert service._count_corroboration(_art("BBC", _TWO)) == 0


def test_corroboration_requires_two_shared_entities():
    service, repo = _service()
    repo.get_recent_articles_with_entities.return_value = [
        _art("CNN", {"persons": ["Erdogan"], "organizations": [], "locations": []}, 2),  # only 1 shared
    ]
    assert service._count_corroboration(_art("BBC", _TWO)) == 0


def test_corroboration_zero_when_target_under_two_entities():
    service, repo = _service()
    one_entity = _art("BBC", {"persons": ["Erdogan"], "organizations": [], "locations": []})
    assert service._count_corroboration(one_entity) == 0
    repo.get_recent_articles_with_entities.assert_not_called()


# ── Jenerik entity filtresi (24 Ağu 2026'da canlıda bulundu) ─────────────────
# "Türkiye" gibi ülke adları neredeyse HER Türkçe haberde geçer — tek başına
# (başka bir şehir adıyla birlikte) iki haberi "aynı olay" saymak için yetersiz
# bir sinyal. Canlıda "Türkiye'nin en samimi şehri İstanbul" haberi, sadece bu
# iki jenerik lokasyonu paylaştığı için alakasız bir Fenerbahçe maçı anlatımıyla
# skor=1.0 eşleşmişti.

_GENERIC = {"persons": [], "organizations": [], "locations": ["Türkiye", "İstanbul"]}


def test_corroboration_ignores_matches_when_only_generic_entities_shared():
    """4+ farklı kaynakta geçen entity'ler 'jenerik' sayılır — hedefin TÜM
    entity'leri jenerikse (sadece ülke/şehir adı), paylaşım corroboration SAYILMAZ."""
    service, repo = _service()
    repo.get_recent_articles_with_entities.return_value = [
        _art("TRT", _GENERIC, 10),
        _art("CNN", _GENERIC, 11),
        _art("Sabah", _GENERIC, 12),
        _art("Sözcü", _GENERIC, 13),  # eskiden bu 4'ü de "kaynak" sayılırdı
    ]
    assert service._count_corroboration(_art("BBC", _GENERIC, 1)) == 0


def test_corroboration_still_counts_when_a_specific_entity_is_also_shared():
    """Jenerik entity'lerin YANINDA en az bir ayırt edici (nadir) entity de
    paylaşılıyorsa eşleşme geçerli kalır — filtre sadece SAF jenerik örtüşmeyi eler."""
    service, repo = _service()
    mixed = {"persons": ["Livakovic"], "organizations": [], "locations": ["Türkiye", "İstanbul"]}
    repo.get_recent_articles_with_entities.return_value = [
        _art("TRT", _GENERIC, 10),
        _art("CNN", _GENERIC, 11),
        _art("Sabah", _GENERIC, 12),
        _art("Sözcü", mixed, 13),  # gerçek eşleşme: "Livakovic" da ortak
    ]
    target = {"persons": ["Livakovic"], "organizations": [], "locations": ["Türkiye", "İstanbul"]}
    assert service._count_corroboration(_art("BBC", target, 1)) == 1


def test_enrich_metadata_sets_quality_credibility_corroboration():
    service, repo = _service()
    repo.get_recent_articles_with_entities.return_value = []
    art = Article(
        title="A reasonably descriptive news title", source="BBC Technology",
        url="u", content="x" * 400,
        summary="A meaningful summary of the article content here.",
        entities={"persons": ["Ali", "Veli"], "organizations": ["Acme"], "locations": []},
    )

    service._enrich_metadata(art)

    assert 0.0 < art.quality_score <= 1.0
    assert art.corroboration_count == 0
    assert art.credibility_score == 0.90  # BBC Technology base, no corroboration
