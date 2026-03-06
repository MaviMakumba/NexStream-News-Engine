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