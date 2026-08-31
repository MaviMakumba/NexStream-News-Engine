from src.domain.models.article import Article
from datetime import datetime

def test_article_creation():
    """Article doğru oluşturuluyor mu?"""
    article = Article(
        title="Test Haberi",
        source="BBC",
        url="https://bbc.com/test",
        content="Test içeriği"
    )
    assert article.title == "Test Haberi"
    assert article.source == "BBC"
    assert article.sentiment_label is None
    assert article.sentiment_score is None

def test_article_with_sentiment():
    """Sentiment alanları doğru atanıyor mu?"""
    article = Article(
        title="İyi Haber",
        source="BBC",
        url="https://bbc.com/good",
        content="Harika bir gün",
        sentiment_label="Positive",
        sentiment_score=0.8
    )
    assert article.sentiment_label == "Positive"
    assert article.sentiment_score == 0.8

def test_article_default_date():
    """created_at otomatik dolduruluyor mu?"""
    article = Article(
        title="Test",
        source="BBC",
        url="https://bbc.com/x",
        content="içerik"
    )
    assert isinstance(article.created_at, datetime)


def test_article_trust_score_property():
    article = Article(
        title="T", source="BBC", url="u", content="c",
        quality_score=1.0, credibility_score=1.0, corroboration_count=10,
    )
    assert article.trust_score == 100


def test_article_trust_score_defaults_when_unscored():
    article = Article(title="T", source="BBC", url="u", content="c")
    assert article.trust_score == 40  # None/None/0 -> nötr varsayılanlar