from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.infrastructure.config.database import Base
from src.adapters.repositories.news_repository import NewsRepository
from src.adapters.repositories.news_orm import NewsORM
from src.domain.models.article import Article

# Her test için temiz in-memory SQLite DB
def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.drop_all(engine)   
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

def make_article(url="https://bbc.com/test"):
    return Article(
        title="Test Haberi",
        source="BBC",
        url=url,
        content="Test içeriği",
        sentiment_label="Positive",
        sentiment_score=0.8,
        summary="Test özeti"
    )

def test_save_article():
    """Haber kaydediliyor mu?"""
    db = make_session()
    repo = NewsRepository(db)
    article = make_article()

    result = repo.save_article(article)

    assert result is True
    assert db.query(NewsORM).count() == 1

def test_save_duplicate_returns_false():
    """Aynı URL iki kez kaydedilmemeli"""
    db = make_session()
    repo = NewsRepository(db)
    article = make_article()

    repo.save_article(article)
    result = repo.save_article(article)

    assert result is False
    assert db.query(NewsORM).count() == 1

def test_article_exists():
    """URL kontrolü doğru çalışıyor mu?"""
    db = make_session()
    repo = NewsRepository(db)

    assert repo.article_exists("https://bbc.com/test") is False
    repo.save_article(make_article())
    assert repo.article_exists("https://bbc.com/test") is True

def test_get_latest_news():
    """Haberler doğru sırayla geliyor mu?"""
    db = make_session()
    repo = NewsRepository(db)

    repo.save_article(make_article("https://bbc.com/1"))
    repo.save_article(make_article("https://bbc.com/2"))
    repo.save_article(make_article("https://bbc.com/3"))

    articles = repo.get_latest_news(limit=2)

    assert len(articles) == 2
    assert all(isinstance(a, Article) for a in articles)

def test_get_latest_news_sentiment_filter():
    """Sentiment filtresi çalışıyor mu?"""
    db = make_session()
    repo = NewsRepository(db)

    positive = make_article("https://bbc.com/1")
    positive.sentiment_label = "Positive"

    negative = make_article("https://bbc.com/2")
    negative.sentiment_label = "Negative"

    repo.save_article(positive)
    repo.save_article(negative)

    results = repo.get_latest_news(limit=10, sentiment_filter="Positive")
    assert len(results) == 1
    assert results[0].sentiment_label == "Positive"


# ── keyword_search (tokenized) ───────────────────────────────────────────────

def _add(repo, url, title, content="içerik", summary="özet", sentiment="Positive"):
    a = Article(title=title, source="BBC", url=url, content=content,
                sentiment_label=sentiment, sentiment_score=0.5, summary=summary)
    repo.save_article(a)
    return a


# ── get_articles_by_ids (v2.2, saved articles listesini render etmek için) ──

def test_get_articles_by_ids_returns_matching_articles():
    db = make_session()
    repo = NewsRepository(db)
    repo.save_article(make_article("https://bbc.com/1"))
    repo.save_article(make_article("https://bbc.com/2"))
    repo.save_article(make_article("https://bbc.com/3"))
    all_ids = [a.id for a in repo.get_all_articles()]

    results = repo.get_articles_by_ids([all_ids[0], all_ids[2]])

    assert {a.id for a in results} == {all_ids[0], all_ids[2]}


def test_get_articles_by_ids_empty_list_returns_empty():
    db = make_session()
    repo = NewsRepository(db)

    assert repo.get_articles_by_ids([]) == []


def test_keyword_search_returns_any_word_match():
    """Multi-word query'de kelimelerden EN AZ BİRİ eşleşen makaleler dönmeli."""
    db = make_session()
    repo = NewsRepository(db)

    _add(repo, "u1", "Real Madrid yıldız transferi")
    _add(repo, "u2", "Sadece Real burada")
    _add(repo, "u3", "Madrid şehri haberleri")
    _add(repo, "u4", "Liverpool kazandı")

    results = repo.keyword_search("real madrid", limit=10)
    titles = {a.title for a in results}

    assert "Real Madrid yıldız transferi" in titles
    assert "Sadece Real burada" in titles
    assert "Madrid şehri haberleri" in titles
    assert "Liverpool kazandı" not in titles


def test_keyword_search_empty_query_returns_empty():
    db = make_session()
    repo = NewsRepository(db)
    _add(repo, "u1", "haber")

    assert repo.keyword_search("", limit=10) == []
    assert repo.keyword_search("   ", limit=10) == []


def test_keyword_search_filters_short_tokens():
    """Tek karakterli token'ler atlanmalı (gürültü)."""
    db = make_session()
    repo = NewsRepository(db)
    _add(repo, "u1", "Yapay zeka haberi")
    _add(repo, "u2", "I love you")

    # "a" tek karakter atılır, sadece "yapay" aranır
    results = repo.keyword_search("a yapay", limit=10)
    titles = {a.title for a in results}
    assert "Yapay zeka haberi" in titles


def test_keyword_search_source_filter():
    db = make_session()
    repo = NewsRepository(db)
    a1 = Article(title="haber", source="BBC", url="u1", content="x",
                 summary="x", sentiment_label="Positive", sentiment_score=0.5)
    a2 = Article(title="haber", source="TRT", url="u2", content="x",
                 summary="x", sentiment_label="Positive", sentiment_score=0.5)
    repo.save_article(a1)
    repo.save_article(a2)

    results = repo.keyword_search("haber", limit=10, source="BBC")
    assert len(results) == 1
    assert results[0].source == "BBC"


# ── v1.8: get_article_by_id / get_articles_with_entities / min_quality ────────

def test_get_article_by_id_returns_article():
    db = make_session()
    repo = NewsRepository(db)
    repo.save_article(make_article("https://bbc.com/x"))
    saved = repo.get_latest_news(1)[0]

    fetched = repo.get_article_by_id(saved.id)
    assert fetched is not None
    assert fetched.id == saved.id


def test_get_article_by_id_returns_none_when_missing():
    db = make_session()
    repo = NewsRepository(db)
    assert repo.get_article_by_id(999) is None


def test_get_articles_with_entities_returns_entity_bearing_articles():
    db = make_session()
    repo = NewsRepository(db)
    repo.save_article(Article(title="t1", source="BBC", url="u1", content="c",
                              entities={"persons": ["Ali"], "organizations": [], "locations": []}))

    result = repo.get_articles_with_entities(limit=10)
    urls = {a.url for a in result}
    assert "u1" in urls
    assert result[0].entities == {"persons": ["Ali"], "organizations": [], "locations": []}


def test_get_articles_with_entities_exclude_id():
    db = make_session()
    repo = NewsRepository(db)
    repo.save_article(Article(title="t1", source="BBC", url="u1", content="c",
                              entities={"persons": ["Ali"], "organizations": [], "locations": []}))
    saved = repo.get_articles_with_entities(limit=10)[0]

    result = repo.get_articles_with_entities(limit=10, exclude_id=saved.id)
    assert all(a.id != saved.id for a in result)


def test_get_news_paginated_min_quality_filter():
    db = make_session()
    repo = NewsRepository(db)
    repo.save_article(Article(title="hi", source="BBC", url="u1", content="c", quality_score=0.8))
    repo.save_article(Article(title="lo", source="BBC", url="u2", content="c", quality_score=0.2))

    urls = {a.url for a in repo.get_news_paginated(limit=10, min_quality=0.5)}
    assert "u1" in urls
    assert "u2" not in urls


# ── get_articles_for_export (v1.16 — ham veri export) ──────────────────────

def test_get_articles_for_export_date_range_filter():
    db = make_session()
    repo = NewsRepository(db)
    repo.save_article(Article(title="eski", source="BBC", url="u_old", content="c",
                               published_at=datetime(2026, 1, 1, tzinfo=timezone.utc)))
    repo.save_article(Article(title="yeni", source="BBC", url="u_new", content="c",
                               published_at=datetime(2026, 6, 1, tzinfo=timezone.utc)))

    urls = {a.url for a in repo.get_articles_for_export(limit=10, date_from=datetime(2026, 3, 1, tzinfo=timezone.utc))}
    assert "u_new" in urls
    assert "u_old" not in urls


def test_get_articles_for_export_falls_back_to_created_at_when_published_at_null():
    """published_at NULL (v1.4 öncesi scrape) — effective tarih created_at'e düşmeli."""
    db = make_session()
    repo = NewsRepository(db)
    repo.save_article(Article(title="published_at yok", source="BBC", url="u_null_pub", content="c"))

    included = {a.url for a in repo.get_articles_for_export(limit=10, date_from=datetime(2000, 1, 1, tzinfo=timezone.utc))}
    assert "u_null_pub" in included

    excluded = {a.url for a in repo.get_articles_for_export(limit=10, date_from=datetime(2099, 1, 1, tzinfo=timezone.utc))}
    assert "u_null_pub" not in excluded


def test_get_articles_for_export_respects_limit():
    db = make_session()
    repo = NewsRepository(db)
    for i in range(5):
        repo.save_article(Article(title=f"h{i}", source="BBC", url=f"u{i}", content="c"))

    assert len(repo.get_articles_for_export(limit=2)) == 2


def test_get_articles_for_export_topic_and_sentiment_filters():
    db = make_session()
    repo = NewsRepository(db)
    repo.save_article(Article(title="a", source="BBC", url="u_tech", content="c",
                               topic="Technology", sentiment_label="Positive"))
    repo.save_article(Article(title="b", source="BBC", url="u_sport", content="c",
                               topic="Sports", sentiment_label="Negative"))

    urls = {a.url for a in repo.get_articles_for_export(limit=10, topic="Technology", sentiment="Positive")}
    assert urls == {"u_tech"}


# ── save_article id propagation (regression: ChromaDB indexleme bug'ı) ────────

def test_save_article_sets_id_on_domain_object():
    """save_article sonrası article.id set edilmeli — yoksa ChromaDB indexleme
    hiç tetiklenmez (NewsService.update_news_from_source `article.id` şartına bakıyor)."""
    db = make_session()
    repo = NewsRepository(db)
    article = make_article()

    assert article.id is None
    result = repo.save_article(article)

    assert result is True
    assert article.id is not None
    saved = db.query(NewsORM).filter(NewsORM.url == article.url).first()
    assert article.id == saved.id


# ── Retention: get_articles_created_after / delete_articles_before ───────────

def _set_created_at(db, article, when):
    db.query(NewsORM).filter(NewsORM.id == article.id).update({"created_at": when})
    db.commit()


def test_get_articles_created_after_excludes_older_rows():
    db = make_session()
    repo = NewsRepository(db)
    old = make_article("https://bbc.com/old")
    new = make_article("https://bbc.com/new")
    repo.save_article(old)
    repo.save_article(new)
    _set_created_at(db, old, datetime.now(timezone.utc) - timedelta(days=10))

    cutoff = datetime.now(timezone.utc) - timedelta(days=1)
    urls = {a.url for a in repo.get_articles_created_after(cutoff)}

    assert "https://bbc.com/new" in urls
    assert "https://bbc.com/old" not in urls


def test_delete_articles_before_removes_only_old_rows():
    db = make_session()
    repo = NewsRepository(db)
    old = make_article("https://bbc.com/old2")
    new = make_article("https://bbc.com/new2")
    repo.save_article(old)
    repo.save_article(new)
    _set_created_at(db, old, datetime.now(timezone.utc) - timedelta(days=10))

    cutoff = datetime.now(timezone.utc) - timedelta(days=1)
    deleted = repo.delete_articles_before(cutoff)

    assert deleted == 1
    remaining_urls = {a.url for a in repo.get_all_articles()}
    assert "https://bbc.com/new2" in remaining_urls
    assert "https://bbc.com/old2" not in remaining_urls


def test_save_persists_quality_credibility_corroboration():
    db = make_session()
    repo = NewsRepository(db)
    repo.save_article(Article(title="t", source="BBC", url="u1", content="c",
                              quality_score=0.7, credibility_score=0.85, corroboration_count=3))

    fetched = repo.get_latest_news(1)[0]
    assert fetched.quality_score == 0.7
    assert fetched.credibility_score == 0.85
    assert fetched.corroboration_count == 3