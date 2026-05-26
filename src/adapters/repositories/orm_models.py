from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, Index, text
from sqlalchemy.dialects.postgresql import JSON, JSONB
from sqlalchemy.sql import func
from src.infrastructure.config.database import Base

class NewsORM(Base):
    __tablename__ = "news_articles"
    __table_args__ = (
        Index("ix_news_source", "source"),
        Index("ix_news_sentiment_label", "sentiment_label"),
        Index("ix_news_created_at", "created_at"),
        Index("ix_news_topic", "topic"),
    )

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(50), nullable=False)
    url = Column(String, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    published_at = Column(DateTime(timezone=True), nullable=True)
    summary = Column(Text, nullable=True)
    sentiment_score = Column(Float, nullable=True)
    sentiment_label = Column(String(20), nullable=True)
    entities = Column(JSON, nullable=True)
    topic = Column(String(30), nullable=True)
    is_duplicate = Column(Boolean, nullable=False, server_default="false")


class SubscriberORM(Base):
    __tablename__ = "subscribers"
    __table_args__ = (
        Index("ix_subscribers_active", "is_active"),
    )

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    keywords = Column(JSON, nullable=False, server_default=text("'[]'"))
    preferred_sources = Column(JSON, nullable=False, server_default=text("'[]'"))
    preferred_topics = Column(JSON, nullable=False, server_default=text("'[]'"))
    language = Column(String(10), nullable=False, server_default=text("'TR'"))
    frequency = Column(String(20), nullable=False, server_default=text("'daily'"))
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())