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