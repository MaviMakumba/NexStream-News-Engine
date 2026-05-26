import logging
from datetime import timezone
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from src.application.services.news_service import NewsService
from src.dependencies import get_news_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Feed"])


def _aware(dt):
    if dt is None:
        from datetime import datetime
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@router.get("/feed.xml", response_class=Response)
def get_rss_feed(service: NewsService = Depends(get_news_service)):
    """
    RSS 2.0 feed — analiz edilmiş haberler, sentiment ve topic tag'leri dahil.
    Feed okuyucularınızda veya IFTTT/Zapier entegrasyonlarında kullanabilirsiniz.
    """
    try:
        from feedgen.feed import FeedGenerator
    except ImportError:
        return Response(
            content="<error>feedgen kütüphanesi yüklü değil</error>",
            media_type="application/xml",
            status_code=500,
        )

    fg = FeedGenerator()
    fg.id("https://nexstream.news/feed.xml")
    fg.title("NexStream News Engine")
    fg.link(href="https://nexstream.news/feed.xml", rel="self")
    fg.link(href="https://nexstream.news/", rel="alternate")
    fg.language("tr")
    fg.description("AI destekli haber motoru — sentiment, NER ve topic analizi")

    articles = service.list_news(50)
    for article in articles:
        try:
            fe = fg.add_entry(order="append")
            fe.id(article.url or str(article.id))
            fe.title(article.title)
            if article.url:
                fe.link(href=article.url)
            pub = _aware(article.published_at or article.created_at)
            fe.published(pub)
            fe.updated(pub)
            parts = [article.summary or ""]
            if article.sentiment_label:
                parts.append(f"Sentiment: {article.sentiment_label}")
            if article.topic:
                parts.append(f"Topic: {article.topic}")
            fe.description(" | ".join(p for p in parts if p))
            if article.source:
                fe.category({"term": article.source})
        except Exception as e:
            logger.warning("RSS entry oluşturma hatası (id=%s): %s", article.id, e)

    return Response(
        content=fg.rss_str(pretty=True),
        media_type="application/rss+xml; charset=utf-8",
    )
