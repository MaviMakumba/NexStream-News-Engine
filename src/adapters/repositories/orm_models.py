"""SQLAlchemy ORM modelleri — DB tablolarının tek tanım noktası.

Domain dataclass'larıyla birebir eşleşir; dönüşümler repository'lerdedir.
Dev'de create_all tabloları otomatik kurar, prod'da migrations/ esastır.
"""

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
        Index("ix_news_quality_score", "quality_score"),
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
    quality_score = Column(Float, nullable=True)
    credibility_score = Column(Float, nullable=True)
    corroboration_count = Column(Integer, nullable=False, server_default="0")


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


class UserORM(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False, server_default=text("''"))
    tier = Column(String(20), nullable=False, server_default=text("'free'"))
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    # v1.13: yetki hiyerarşisi (user/moderator/admin) — paylaşımlı API_KEY yerine
    # kullanıcı bazlı yetki. v1.11'deki boolean is_admin kolonunun yerini aldı.
    role = Column(String(20), nullable=False, server_default=text("'user'"))
    # v1.11: kullanıcıya özel public API anahtarı (X-User-Key ile kullanılır)
    api_key = Column(String(64), unique=True, nullable=True, index=True)
    stripe_customer_id = Column(String(255), nullable=True)
    # v1.15: e-posta doğrulama — Free tier'da erişimi kısıtlamaz (yumuşak
    # gating), sadece ücretli kademeye yükseltme bunu ister (billing_router).
    email_verified = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserSessionORM(Base):
    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("ix_sessions_token", "token"),
        Index("ix_sessions_user_id", "user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    token = Column(String(128), unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PasswordResetTokenORM(Base):
    __tablename__ = "password_reset_tokens"
    __table_args__ = (
        Index("ix_reset_tokens_user_id", "user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    token = Column(String(128), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EmailVerificationTokenORM(Base):
    __tablename__ = "email_verification_tokens"
    __table_args__ = (
        Index("ix_email_verify_tokens_user_id", "user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    token = Column(String(128), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UsageLogORM(Base):
    __tablename__ = "usage_logs"
    __table_args__ = (
        Index("ix_usage_user_id", "user_id"),
        Index("ix_usage_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)
    response_ms = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SavedArticleORM(Base):
    """Kaydedilen haber (bookmark / sonra oku) — v2.2."""

    __tablename__ = "saved_articles"
    __table_args__ = (
        Index("ix_saved_articles_user_id", "user_id"),
        Index("ix_saved_articles_user_article", "user_id", "article_id", unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    article_id = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SponsorORM(Base):
    __tablename__ = "sponsors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    url = Column(String(512), nullable=False)
    message = Column(Text, nullable=False)
    active_from = Column(DateTime(timezone=True), nullable=False)
    active_until = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())