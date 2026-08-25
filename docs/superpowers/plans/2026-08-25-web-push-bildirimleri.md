# Web Push Bildirimleri Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kullanıcıların zaten sahip olduğu "anlık (instant) keyword uyarısı" e-posta akışına tarayıcı push bildirimini ikinci bir kanal olarak eklemek.

**Architecture:** Hexagonal — yeni `PushSubscriptionRepositoryPort` (abonelik saklama) ve `WebPushPort` (VAPID imzalı gönderim) port'ları, PostgreSQL + `pywebpush` adaptörleriyle gerçeklenir. `NewsService._send_keyword_alerts` (mevcut email akışı) genişletilir — push, email ile AYNI keyword eşleşmesini paylaşır, ayrı bir tetikleyici yok.

**Tech Stack:** Python/FastAPI/SQLAlchemy (backend), `pywebpush` (VAPID push gönderimi), Next.js/TypeScript + Web Push API (frontend), PostgreSQL (yeni `push_subscriptions` tablosu).

**Spec:** `docs/superpowers/specs/2026-08-25-web-push-bildirimleri-design.md`

## Global Constraints

- Gerçek HTTP/network çağrısı içeren test YASAK — `pywebpush.webpush()` her testte mock'lanır (proje kuralı, bkz. CLAUDE.md KODLAMA KURALLARI).
- Exception'ları yut, logla, fallback dön — `PyWebPushAdapter.send()` hiçbir zaman exception fırlatmaz.
- Yeni isim `WebPushPort` — mevcut `NotificationPort` (`/ws/feed` canlı yayını) ile KARIŞTIRILMAYACAK, isim çakışması bilinçli olarak engellendi.
- Push, email "instant" aboneliğinin AYNI keyword listesini paylaşır — ayrı bir keyword formu/state YOK (YAGNI, spec'te onaylandı).
- Push aboneliği (`POST /account/push-subscription`) giriş yapmış (`get_current_user`) VE Pro+ tier zorunlu — `_assert_instant_allowed` (subscription_router.py) ile AYNI mantık.
- Tüm UI string'leri `frontend/lib/i18n.ts::UI[lang]` sözlüğünde — hardcoded TR/EN metin YASAK (SOLID i18n kuralı).
- VAPID anahtarları ZATEN üretildi ve hem lokal hem prod `.env`'de hazır: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`, `NEXT_PUBLIC_VAPID_PUBLIC_KEY`.

---

### Task 1: Domain katmanı, ORM, migration ve PushSubscriptionRepository

**Files:**
- Create: `src/domain/models/push_subscription.py`
- Create: `src/domain/ports/push_subscription_port.py`
- Create: `src/adapters/repositories/push_subscription_repository.py`
- Modify: `src/adapters/repositories/orm_models.py` (yeni `PushSubscriptionORM` sınıfı ekle — dosyanın sonuna, `SponsorORM`'dan önce/sonra fark etmez, mevcut sınıflardan biri gibi)
- Create: `migrations/v2_5_push_subscriptions.sql`
- Test: `tests/adapters/test_push_subscription_repository.py`

**Interfaces:**
- Produces: `PushSubscription` dataclass (`email: str, endpoint: str, p256dh: str, auth: str, id: Optional[int] = None, created_at: Optional[datetime] = None`), `PushSubscriptionRepositoryPort` (ABC: `save`, `get_by_email`, `delete_by_endpoint`, `delete_by_email`), `PushSubscriptionRepository(db: Session)` — Task 3, 5'te kullanılacak.

- [ ] **Step 1: Domain model oluştur**

`src/domain/models/push_subscription.py`:
```python
"""Tarayıcı push abonelik domain modeli — Web Push protokolü subscription bilgisi (v2.5)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class PushSubscription:
    email: str
    endpoint: str
    p256dh: str
    auth: str
    id: Optional[int] = None
    created_at: Optional[datetime] = None
```

- [ ] **Step 2: Port oluştur**

`src/domain/ports/push_subscription_port.py`:
```python
"""Web push abonelik repository port'u — tarayıcı push subscription'larının
kalıcı saklanması sözleşmesi.

Somut implementasyon: adapters/repositories/push_subscription_repository.py (PostgreSQL).
"""

from abc import ABC, abstractmethod
from typing import List
from src.domain.models.push_subscription import PushSubscription


class PushSubscriptionRepositoryPort(ABC):
    @abstractmethod
    def save(self, subscription: PushSubscription) -> PushSubscription:
        """endpoint UNIQUE — aynı endpoint tekrar gelirse üzerine yazar (upsert)."""

    @abstractmethod
    def get_by_email(self, email: str) -> List[PushSubscription]: ...

    @abstractmethod
    def delete_by_endpoint(self, endpoint: str) -> bool:
        """Silinen satır varsa True, yoksa False döner (idempotent çağrı için)."""

    @abstractmethod
    def delete_by_email(self, email: str) -> None:
        """Hesap silinirken kullanıcının TÜM cihaz aboneliklerini temizler."""
```

- [ ] **Step 3: ORM modeli ekle**

`src/adapters/repositories/orm_models.py` dosyasının sonuna ekle:
```python
class PushSubscriptionORM(Base):
    """Tarayıcı push bildirim aboneliği — v2.5."""

    __tablename__ = "push_subscriptions"
    __table_args__ = (
        Index("ix_push_subscriptions_email", "email"),
    )

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False)
    endpoint = Column(Text, unique=True, nullable=False)
    p256dh = Column(String(255), nullable=False)
    auth = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```
(`Column`, `Integer`, `String`, `Text`, `DateTime`, `Index`, `func` zaten dosyanın en üstünde import edilmiş — yeni import gerekmiyor.)

- [ ] **Step 4: Migration dosyası oluştur**

`migrations/v2_5_push_subscriptions.sql`:
```sql
-- v2.5 — Web push bildirim abonelikleri (roadmap #12)
CREATE TABLE IF NOT EXISTS push_subscriptions (
    id          SERIAL PRIMARY KEY,
    email       VARCHAR(255) NOT NULL,
    endpoint    TEXT UNIQUE NOT NULL,
    p256dh      VARCHAR(255) NOT NULL,
    auth        VARCHAR(255) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_push_subscriptions_email ON push_subscriptions(email);
```

- [ ] **Step 5: Repository testlerini yaz (gerçek in-memory SQLite, mock YOK)**

`tests/adapters/test_push_subscription_repository.py`:
```python
"""PushSubscriptionRepository testleri — gerçek in-memory SQLite (bkz. test_saved_article_repository.py deseni)."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.infrastructure.config.database import Base
from src.domain.models.push_subscription import PushSubscription
from src.adapters.repositories.push_subscription_repository import PushSubscriptionRepository
from src.adapters.repositories.orm_models import PushSubscriptionORM


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _sub(email="me@test.com", endpoint="https://push.example.com/abc"):
    return PushSubscription(email=email, endpoint=endpoint, p256dh="p256dh-key", auth="auth-secret")


def test_save_adds_row():
    db = make_session()
    repo = PushSubscriptionRepository(db)

    result = repo.save(_sub())

    assert result.id is not None
    assert db.query(PushSubscriptionORM).count() == 1


def test_save_same_endpoint_upserts_not_duplicates():
    db = make_session()
    repo = PushSubscriptionRepository(db)
    repo.save(_sub())

    result = repo.save(_sub(endpoint="https://push.example.com/abc"))

    assert db.query(PushSubscriptionORM).count() == 1
    assert result.endpoint == "https://push.example.com/abc"


def test_get_by_email_returns_all_devices():
    db = make_session()
    repo = PushSubscriptionRepository(db)
    repo.save(_sub(endpoint="https://push.example.com/device1"))
    repo.save(_sub(endpoint="https://push.example.com/device2"))
    repo.save(_sub(email="other@test.com", endpoint="https://push.example.com/device3"))

    result = repo.get_by_email("me@test.com")

    assert len(result) == 2
    assert {s.endpoint for s in result} == {
        "https://push.example.com/device1", "https://push.example.com/device2",
    }


def test_get_by_email_returns_empty_list_when_none():
    db = make_session()
    repo = PushSubscriptionRepository(db)

    assert repo.get_by_email("nobody@test.com") == []


def test_delete_by_endpoint_removes_row():
    db = make_session()
    repo = PushSubscriptionRepository(db)
    repo.save(_sub())

    result = repo.delete_by_endpoint("https://push.example.com/abc")

    assert result is True
    assert db.query(PushSubscriptionORM).count() == 0


def test_delete_by_endpoint_returns_false_when_not_found():
    db = make_session()
    repo = PushSubscriptionRepository(db)

    assert repo.delete_by_endpoint("https://push.example.com/missing") is False


def test_delete_by_email_removes_all_devices_for_that_email_only():
    db = make_session()
    repo = PushSubscriptionRepository(db)
    repo.save(_sub(endpoint="https://push.example.com/device1"))
    repo.save(_sub(endpoint="https://push.example.com/device2"))
    repo.save(_sub(email="other@test.com", endpoint="https://push.example.com/device3"))

    repo.delete_by_email("me@test.com")

    assert repo.get_by_email("me@test.com") == []
    assert len(repo.get_by_email("other@test.com")) == 1
```

- [ ] **Step 6: Run testleri doğrula (önce FAIL etmeli — repository henüz yok)**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_push_subscription_repository.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.adapters.repositories.push_subscription_repository'`

- [ ] **Step 7: Repository adaptörünü yaz**

`src/adapters/repositories/push_subscription_repository.py`:
```python
"""Web push abonelik repository'sinin PostgreSQL implementasyonu — v2.5.

`PushSubscriptionRepositoryPort` sözleşmesini gerçekler. `endpoint` üzerinde
UNIQUE index var (bkz. orm_models.py) — `save` bu yüzden upsert: aynı endpoint
tekrar gelirse (tarayıcı subscription'ı yeniledi) üzerine yazar.
"""

import logging
from typing import List

from sqlalchemy.orm import Session

from src.domain.models.push_subscription import PushSubscription
from src.domain.ports.push_subscription_port import PushSubscriptionRepositoryPort
from src.adapters.repositories.orm_models import PushSubscriptionORM

logger = logging.getLogger(__name__)


class PushSubscriptionRepository(PushSubscriptionRepositoryPort):
    def __init__(self, db: Session):
        self.db = db

    def _to_domain(self, orm: PushSubscriptionORM) -> PushSubscription:
        return PushSubscription(
            id=orm.id, email=orm.email, endpoint=orm.endpoint,
            p256dh=orm.p256dh, auth=orm.auth, created_at=orm.created_at,
        )

    def save(self, subscription: PushSubscription) -> PushSubscription:
        existing = self.db.query(PushSubscriptionORM).filter(
            PushSubscriptionORM.endpoint == subscription.endpoint
        ).first()
        if existing:
            existing.email = subscription.email
            existing.p256dh = subscription.p256dh
            existing.auth = subscription.auth
            self.db.commit()
            self.db.refresh(existing)
            return self._to_domain(existing)
        orm = PushSubscriptionORM(
            email=subscription.email, endpoint=subscription.endpoint,
            p256dh=subscription.p256dh, auth=subscription.auth,
        )
        self.db.add(orm)
        self.db.commit()
        self.db.refresh(orm)
        return self._to_domain(orm)

    def get_by_email(self, email: str) -> List[PushSubscription]:
        rows = self.db.query(PushSubscriptionORM).filter(PushSubscriptionORM.email == email).all()
        return [self._to_domain(r) for r in rows]

    def delete_by_endpoint(self, endpoint: str) -> bool:
        orm = self.db.query(PushSubscriptionORM).filter(PushSubscriptionORM.endpoint == endpoint).first()
        if not orm:
            return False
        self.db.delete(orm)
        self.db.commit()
        return True

    def delete_by_email(self, email: str) -> None:
        self.db.query(PushSubscriptionORM).filter(PushSubscriptionORM.email == email).delete()
        self.db.commit()
```

- [ ] **Step 8: Testleri tekrar çalıştır — PASS olmalı**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_push_subscription_repository.py -v`
Expected: 7 passed

- [ ] **Step 9: Commit**

```bash
git add src/domain/models/push_subscription.py src/domain/ports/push_subscription_port.py src/adapters/repositories/push_subscription_repository.py src/adapters/repositories/orm_models.py migrations/v2_5_push_subscriptions.sql tests/adapters/test_push_subscription_repository.py
git commit -m "feat: push subscription domain model, port, ORM, migration, repository (Task 1/7)"
```

---

### Task 2: WebPushPort + PyWebPushAdapter + settings + factory

**Files:**
- Create: `src/domain/ports/web_push_port.py`
- Create: `src/adapters/notifications/pywebpush_adapter.py`
- Create: `src/adapters/notifications/web_push_factory.py`
- Modify: `src/infrastructure/config/settings.py` (yeni `vapid_public_key`/`vapid_private_key`/`vapid_subject` alanları)
- Modify: `requirements.txt` (yeni `pywebpush` satırı)
- Test: `tests/adapters/test_pywebpush_adapter.py`

**Interfaces:**
- Consumes: `PushSubscription` (Task 1).
- Produces: `WebPushPort` (ABC: `send(subscription, title, body, url) -> bool`), `PyWebPushAdapter()`, `build_web_push() -> Optional[WebPushPort]` — Task 3, 4'te kullanılacak.

- [ ] **Step 1: `pywebpush`'ı requirements.txt'e ekle ve lokal venv'e kur**

`requirements.txt`'in sonuna ekle:
```
pywebpush>=2.0.0
```

Run: `venv\Scripts\python.exe -m pip install pywebpush` (zaten kuruluysa no-op geçer).

- [ ] **Step 2: settings.py'e VAPID alanlarını ekle**

`src/infrastructure/config/settings.py`'de `sentry_traces_sample_rate: float = 0.05` satırından hemen sonra ekle:
```python

    # ── Web push bildirimleri (VAPID, v2.5) ─────────────────────────────────
    # Kriptografik anahtar çifti — 3. parti hesap gerektirmez (`npx web-push
    # generate-vapid-keys` ile üretildi). Boşsa build_web_push() None döner,
    # NewsService push adımını tamamen atlar (diğer opsiyonel entegrasyonlarla
    # aynı desen: boş = devre dışı, kod hiç dokunmaz).
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:no-reply@nexstream.news"
```

- [ ] **Step 3: WebPushPort'u oluştur**

`src/domain/ports/web_push_port.py`:
```python
"""Tarayıcı push bildirimi gönderme port'u — VAPID imzalı push mesajı yollama sözleşmesi.

Somut implementasyon: adapters/notifications/pywebpush_adapter.py (pywebpush).

İSİM NOTU: mevcut NotificationPort (domain/ports/notification_port.py) /ws/feed
canlı yayını için — alakasız bir kavram, isim çakışmasın diye bilinçli olarak
WebPushPort adı seçildi.
"""

from abc import ABC, abstractmethod
from src.domain.models.push_subscription import PushSubscription


class WebPushPort(ABC):
    @abstractmethod
    def send(self, subscription: PushSubscription, title: str, body: str, url: str) -> bool:
        """Gönderir; abonelik geçersizse (404/410) veya başka bir hatada False
        döner, hiçbir zaman exception fırlatmaz (fail-open)."""
```

- [ ] **Step 4: Adapter testlerini yaz (pywebpush.webpush() mock'lanır)**

`tests/adapters/test_pywebpush_adapter.py`:
```python
"""PyWebPushAdapter testleri — pywebpush.webpush() mock'lanır, gerçek HTTP çağrısı yok."""

import logging
from unittest.mock import patch, MagicMock

from pywebpush import WebPushException

from src.domain.models.push_subscription import PushSubscription


def _sub():
    return PushSubscription(
        email="me@test.com", endpoint="https://push.example.com/abc",
        p256dh="p256dh-key", auth="auth-secret",
    )


def test_send_success_returns_true():
    from src.adapters.notifications.pywebpush_adapter import PyWebPushAdapter
    adapter = PyWebPushAdapter()
    with patch("src.adapters.notifications.pywebpush_adapter.webpush") as mock_webpush:
        result = adapter.send(_sub(), title="Başlık", body="Gövde", url="https://x.com/1")

    assert result is True
    mock_webpush.assert_called_once()
    call_kwargs = mock_webpush.call_args.kwargs
    assert call_kwargs["subscription_info"]["endpoint"] == "https://push.example.com/abc"
    assert call_kwargs["subscription_info"]["keys"] == {"p256dh": "p256dh-key", "auth": "auth-secret"}


def test_send_expired_subscription_returns_false_without_logging(caplog):
    from src.adapters.notifications.pywebpush_adapter import PyWebPushAdapter
    caplog.set_level(logging.WARNING)
    adapter = PyWebPushAdapter()
    exc = WebPushException("gone", response=MagicMock(status_code=410))
    with patch("src.adapters.notifications.pywebpush_adapter.webpush", side_effect=exc):
        result = adapter.send(_sub(), title="t", body="b", url="https://x.com/1")

    assert result is False
    assert "gönderilemedi" not in caplog.text


def test_send_not_found_subscription_returns_false():
    from src.adapters.notifications.pywebpush_adapter import PyWebPushAdapter
    adapter = PyWebPushAdapter()
    exc = WebPushException("not found", response=MagicMock(status_code=404))
    with patch("src.adapters.notifications.pywebpush_adapter.webpush", side_effect=exc):
        result = adapter.send(_sub(), title="t", body="b", url="https://x.com/1")

    assert result is False


def test_send_server_error_returns_false_and_logs(caplog):
    from src.adapters.notifications.pywebpush_adapter import PyWebPushAdapter
    caplog.set_level(logging.WARNING)
    adapter = PyWebPushAdapter()
    exc = WebPushException("server error", response=MagicMock(status_code=500))
    with patch("src.adapters.notifications.pywebpush_adapter.webpush", side_effect=exc):
        result = adapter.send(_sub(), title="t", body="b", url="https://x.com/1")

    assert result is False
    assert "gönderilemedi" in caplog.text


def test_send_exception_without_response_returns_false():
    from src.adapters.notifications.pywebpush_adapter import PyWebPushAdapter
    adapter = PyWebPushAdapter()
    exc = WebPushException("network error", response=None)
    with patch("src.adapters.notifications.pywebpush_adapter.webpush", side_effect=exc):
        result = adapter.send(_sub(), title="t", body="b", url="https://x.com/1")

    assert result is False
```

- [ ] **Step 5: Run testleri doğrula (FAIL etmeli)**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_pywebpush_adapter.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 6: PyWebPushAdapter'ı yaz**

`src/adapters/notifications/pywebpush_adapter.py`:
```python
"""Web push gönderim adapter'ı — pywebpush + VAPID imzalama (v2.5).

WebPushPort sözleşmesini gerçekler. pywebpush.webpush() hiçbir zaman dışarı
exception sızdırmaz — burada yakalanır, loglanır, False döner (projenin
"exception yut, logla, fallback dön" kuralı).
"""

import json
import logging

from pywebpush import webpush, WebPushException

from src.domain.models.push_subscription import PushSubscription
from src.domain.ports.web_push_port import WebPushPort
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

# 1 saat — "anlık" bildirim niteliğinde, cihaz gün boyu çevrimdışıysa eski bir
# uyarıyı geç teslim etmenin anlamı yok (pywebpush varsayılanı ttl=0, yani
# cihaz o an çevrimdışıysa mesaj hiç saklanmaz — bu bizim için fazla agresif).
_PUSH_TTL_SECONDS = 3600


class PyWebPushAdapter(WebPushPort):
    def send(self, subscription: PushSubscription, title: str, body: str, url: str) -> bool:
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
                },
                data=json.dumps({"title": title, "body": body, "url": url}),
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": settings.vapid_subject},
                ttl=_PUSH_TTL_SECONDS,
            )
            return True
        except WebPushException as e:
            status = e.response.status_code if e.response is not None else None
            if status in (404, 410):
                return False
            logger.warning("Web push gönderilemedi (status=%s): %s", status, e)
            return False
```

- [ ] **Step 7: Factory'yi yaz**

`src/adapters/notifications/web_push_factory.py`:
```python
"""Web push kompozisyon noktası — VAPID key'leri boşsa None döner (v2.5)."""

from typing import Optional

from src.domain.ports.web_push_port import WebPushPort
from src.adapters.notifications.pywebpush_adapter import PyWebPushAdapter
from src.infrastructure.config.settings import settings


def build_web_push() -> Optional[WebPushPort]:
    if not settings.vapid_public_key or not settings.vapid_private_key:
        return None
    return PyWebPushAdapter()
```

- [ ] **Step 8: Testleri tekrar çalıştır — PASS olmalı**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_pywebpush_adapter.py -v`
Expected: 5 passed

- [ ] **Step 9: Commit**

```bash
git add requirements.txt src/infrastructure/config/settings.py src/domain/ports/web_push_port.py src/adapters/notifications/pywebpush_adapter.py src/adapters/notifications/web_push_factory.py tests/adapters/test_pywebpush_adapter.py
git commit -m "feat: WebPushPort + PyWebPushAdapter + VAPID settings + factory (Task 2/7)"
```

---

### Task 3: NewsService entegrasyonu — `_send_keyword_alerts` genişletmesi

**Files:**
- Modify: `src/application/services/news_service.py` (constructor + `_send_keyword_alerts` + yeni `_send_push_alerts` private metodu)
- Modify: `tests/application/test_keyword_alerts.py` (yeni push senaryoları)

**Interfaces:**
- Consumes: `PushSubscriptionRepositoryPort.get_by_email`, `PushSubscriptionRepositoryPort.delete_by_endpoint` (Task 1), `WebPushPort.send` (Task 2).
- Produces: `NewsService(..., push_repository: Optional[PushSubscriptionRepositoryPort] = None, web_push: Optional[WebPushPort] = None)` — Task 4'te worker DI'ında kullanılacak.

- [ ] **Step 1: Yeni test senaryolarını `test_keyword_alerts.py`'ye ekle**

Dosyanın en üstündeki import bloğunu güncelle (mevcut `from src.domain.models.subscriber import Subscriber` satırının altına ekle):
```python
from src.domain.models.push_subscription import PushSubscription
```

Dosyanın sonuna ekle:
```python
def _push_sub(email="fan@test.com", endpoint="https://push.example.com/1"):
    return PushSubscription(email=email, endpoint=endpoint, p256dh="k", auth="a")


def _make_service_with_push(subscribers=None, push_subs=None, push_ok=True, web_push=True):
    mock_repo = MagicMock()
    mock_analyzer = MagicMock()
    mock_sub_repo = MagicMock()
    mock_sub_repo.get_active_subscribers.return_value = subscribers or []
    mock_email = MagicMock()
    mock_email.send_alert.return_value = True
    mock_push_repo = MagicMock()
    mock_push_repo.get_by_email.return_value = push_subs or []
    mock_web_push = MagicMock() if web_push else None
    if mock_web_push:
        mock_web_push.send.return_value = push_ok
    service = NewsService(
        repository=mock_repo, analyzer=mock_analyzer,
        subscriber_repository=mock_sub_repo, email_port=mock_email,
        push_repository=mock_push_repo, web_push=mock_web_push,
    )
    return service, mock_email, mock_push_repo, mock_web_push


def test_push_sent_alongside_email_when_keyword_matches():
    sub = _instant_subscriber(["beşiktaş"])
    service, mock_email, mock_push_repo, mock_web_push = _make_service_with_push(
        [sub], push_subs=[_push_sub()]
    )
    service._send_keyword_alerts(_article("Beşiktaş şampiyon oldu"))

    mock_email.send_alert.assert_called_once()
    mock_web_push.send.assert_called_once()
    call_kwargs = mock_web_push.send.call_args.kwargs
    assert call_kwargs["title"] == "Beşiktaş şampiyon oldu"
    assert "beşiktaş" in call_kwargs["body"]


def test_push_skipped_when_web_push_is_none_email_still_sent():
    sub = _instant_subscriber(["beşiktaş"])
    service, mock_email, mock_push_repo, _ = _make_service_with_push(
        [sub], push_subs=[_push_sub()], web_push=False
    )
    service._send_keyword_alerts(_article("Beşiktaş şampiyon oldu"))

    mock_email.send_alert.assert_called_once()
    mock_push_repo.get_by_email.assert_not_called()


def test_push_skipped_when_push_repository_is_none_email_still_sent():
    sub = _instant_subscriber(["beşiktaş"])
    mock_repo = MagicMock()
    mock_analyzer = MagicMock()
    mock_sub_repo = MagicMock()
    mock_sub_repo.get_active_subscribers.return_value = [sub]
    mock_email = MagicMock()
    mock_email.send_alert.return_value = True
    mock_web_push = MagicMock()
    service = NewsService(
        repository=mock_repo, analyzer=mock_analyzer,
        subscriber_repository=mock_sub_repo, email_port=mock_email,
        push_repository=None, web_push=mock_web_push,
    )
    service._send_keyword_alerts(_article("Beşiktaş şampiyon oldu"))

    mock_email.send_alert.assert_called_once()
    mock_web_push.send.assert_not_called()


def test_push_subscription_deleted_when_send_fails():
    sub = _instant_subscriber(["beşiktaş"])
    push_sub = _push_sub()
    service, _, mock_push_repo, _ = _make_service_with_push(
        [sub], push_subs=[push_sub], push_ok=False
    )
    service._send_keyword_alerts(_article("Beşiktaş şampiyon oldu"))

    mock_push_repo.delete_by_endpoint.assert_called_once_with(push_sub.endpoint)


def test_push_subscription_not_deleted_when_send_succeeds():
    sub = _instant_subscriber(["beşiktaş"])
    service, _, mock_push_repo, _ = _make_service_with_push(
        [sub], push_subs=[_push_sub()], push_ok=True
    )
    service._send_keyword_alerts(_article("Beşiktaş şampiyon oldu"))

    mock_push_repo.delete_by_endpoint.assert_not_called()


def test_push_failure_does_not_prevent_email():
    sub = _instant_subscriber(["beşiktaş"])
    service, mock_email, _, _ = _make_service_with_push(
        [sub], push_subs=[_push_sub()], push_ok=False
    )
    service._send_keyword_alerts(_article("Beşiktaş şampiyon oldu"))

    mock_email.send_alert.assert_called_once()


def test_push_unexpected_exception_does_not_prevent_email():
    """web_push.send() beklenmedik bir exception fırlatırsa bile email etkilenmemeli."""
    sub = _instant_subscriber(["beşiktaş"])
    service, mock_email, _, mock_web_push = _make_service_with_push(
        [sub], push_subs=[_push_sub()]
    )
    mock_web_push.send.side_effect = RuntimeError("boom")
    service._send_keyword_alerts(_article("Beşiktaş şampiyon oldu"))

    mock_email.send_alert.assert_called_once()


def test_multiple_push_subscriptions_for_same_subscriber_all_attempted():
    sub = _instant_subscriber(["beşiktaş"])
    push_subs = [
        _push_sub(endpoint="https://push.example.com/1"),
        _push_sub(endpoint="https://push.example.com/2"),
    ]
    service, _, _, mock_web_push = _make_service_with_push([sub], push_subs=push_subs)
    service._send_keyword_alerts(_article("Beşiktaş şampiyon oldu"))

    assert mock_web_push.send.call_count == 2
```

- [ ] **Step 2: Testleri çalıştır — FAIL etmeli (constructor push_repository/web_push kabul etmiyor)**

Run: `venv\Scripts\python.exe -m pytest tests/application/test_keyword_alerts.py -v`
Expected: FAIL — `TypeError: NewsService.__init__() got an unexpected keyword argument 'push_repository'`

- [ ] **Step 3: `news_service.py`'yi genişlet**

`TYPE_CHECKING` bloğunu güncelle (satır 29-32 civarı):
```python
if TYPE_CHECKING:
    from src.domain.ports.email_port import EmailPort
    from src.domain.ports.subscriber_port import SubscriberRepositoryPort
    from src.domain.ports.query_expansion_port import QueryExpansionPort
    from src.domain.ports.push_subscription_port import PushSubscriptionRepositoryPort
    from src.domain.ports.web_push_port import WebPushPort
```

Constructor'ı güncelle (mevcut `def __init__` — satır 92-106 civarı):
```python
    def __init__(
        self,
        repository: NewsRepositoryPort,
        analyzer: AnalysisPort,
        search_repository=None,
        subscriber_repository: Optional["SubscriberRepositoryPort"] = None,
        email_port: Optional["EmailPort"] = None,
        query_expander: Optional["QueryExpansionPort"] = None,
        push_repository: Optional["PushSubscriptionRepositoryPort"] = None,
        web_push: Optional["WebPushPort"] = None,
    ):
        self.repository = repository
        self.analyzer = analyzer
        self.search_repository = search_repository
        self.subscriber_repository = subscriber_repository
        self.email_port = email_port
        self.query_expander = query_expander
        self.push_repository = push_repository
        self.web_push = web_push
```

`_send_keyword_alerts`'i güncelle (mevcut metod — satır 729-738 civarı):
```python
    def _send_keyword_alerts(self, article: Article) -> None:
        """'instant' frekanslı abonelere keyword eşleşmesinde anında e-posta
        (+varsa tarayıcı push) yollar. Push, email'in AYNI eşleşmesini paylaşır
        — ayrı bir tetikleyici/keyword listesi yok (bkz. 2026-08-25 spec)."""
        if self.subscriber_repository is None or self.email_port is None:
            return
        for sub in self.subscriber_repository.get_active_subscribers():
            if sub.frequency != "instant" or not sub.keywords:
                continue
            kw = matched_keyword(article, sub.keywords)
            if kw is None:
                continue
            self.email_port.send_alert(sub.email, article, kw, sub.language)
            self._send_push_alerts(sub.email, article, kw)

    def _send_push_alerts(self, email: str, article: Article, keyword: str) -> None:
        """Email'den AYRI, fail-open bir adım — push hatası email'i asla
        etkilemez, tek bir push subscription'ın hatası diğerlerini engellemez."""
        if self.push_repository is None or self.web_push is None:
            return
        try:
            for push_sub in self.push_repository.get_by_email(email):
                ok = self.web_push.send(
                    push_sub, title=article.title,
                    body=f"Takip ettiğin '{keyword}' ile eşleşti", url=article.url,
                )
                if not ok:
                    self.push_repository.delete_by_endpoint(push_sub.endpoint)
        except Exception as e:
            logger.error("Push bildirimi gönderilirken hata (email alert etkilenmedi): %s", e)
```

- [ ] **Step 4: Testleri tekrar çalıştır — hepsi PASS olmalı**

Run: `venv\Scripts\python.exe -m pytest tests/application/test_keyword_alerts.py -v`
Expected: 15 passed (6 mevcut + 9 yeni)

- [ ] **Step 5: Tam regresyon — bu dosyayı değiştirmek başka testi kırmamalı**

Run: `venv\Scripts\python.exe -m pytest tests/application/test_news_service.py -v`
Expected: mevcut tüm testler PASS (constructor'a yeni opsiyonel parametre eklendi, mevcut çağrılar etkilenmemeli)

- [ ] **Step 6: Commit**

```bash
git add src/application/services/news_service.py tests/application/test_keyword_alerts.py
git commit -m "feat: NewsService._send_keyword_alerts push kanalıyla genişletildi (Task 3/7)"
```

---

### Task 4: Worker DI wiring (kafka_consumer.py) + prod compose env

**Files:**
- Modify: `src/adapters/messaging/kafka_consumer.py` (`_process` fonksiyonu)
- Modify: `docker-compose.prod.yml` (worker servisi environment bloğu)

**Interfaces:**
- Consumes: `PushSubscriptionRepository` (Task 1), `build_web_push()` (Task 2), `NewsService(push_repository=..., web_push=...)` (Task 3).
- Produces: yok — bu görev bağlama/deployment, kendi başına test edilebilir bir davranış üretmiyor (proje kalıbı: kafka_consumer.py'nin kendi test dosyası yok, wiring `python -c` ile içe aktarma kontrolüyle doğrulanır).

- [ ] **Step 1: `kafka_consumer.py`'yi güncelle**

Import bloğuna ekle (mevcut `from src.adapters.repositories.subscriber_repository import SubscriberRepository` satırının altına):
```python
from src.adapters.repositories.push_subscription_repository import PushSubscriptionRepository
from src.adapters.notifications.web_push_factory import build_web_push
```

`_process` fonksiyonunu güncelle (mevcut hali — satır 49-66 civarı):
```python
async def _process(scraper):
    db = SessionLocal()
    try:
        repo = NewsRepository(db)
        analyzer = build_analyzer()
        sub_repo = SubscriberRepository(db)
        push_repo = PushSubscriptionRepository(db)
        service = NewsService(
            repository=repo,
            analyzer=analyzer,
            search_repository=_get_search_repo(),
            subscriber_repository=sub_repo,
            email_port=_get_email_adapter(),
            push_repository=push_repo,
            web_push=build_web_push(),
        )
        await service.update_news_from_source(scraper)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, service.reanalyze_missed, 3)
    finally:
        db.close()
```

- [ ] **Step 2: Modülün hâlâ sorunsuz import edildiğini doğrula**

Run: `venv\Scripts\python.exe -c "import src.adapters.messaging.kafka_consumer"`
Expected: hata yok, sessizce çıkar (exit code 0)

- [ ] **Step 3: `docker-compose.prod.yml`'de worker servisine VAPID env var'larını ekle**

`worker` servisinin `environment:` bloğuna (Sentry satırlarının hemen altına) ekle:
```yaml
      # v2.5: web push bildirimleri — boşsa build_web_push() None döner,
      # NewsService push adımını tamamen atlar (diğer opsiyonel entegrasyonlarla aynı desen).
      - VAPID_PUBLIC_KEY=${VAPID_PUBLIC_KEY:-}
      - VAPID_PRIVATE_KEY=${VAPID_PRIVATE_KEY:-}
      - VAPID_SUBJECT=${VAPID_SUBJECT:-mailto:no-reply@nexstream.news}
```

- [ ] **Step 4: Tam backend regresyonu**

Run: `venv\Scripts\python.exe -m pytest tests/ -v`
Expected: 775 passed (754 mevcut + 7 Task 1 repository + 5 Task 2 adapter + 9 Task 3 keyword_alerts), hiç FAIL yok

- [ ] **Step 5: Commit**

```bash
git add src/adapters/messaging/kafka_consumer.py docker-compose.prod.yml
git commit -m "feat: worker DI wiring — push_repository + web_push (Task 4/7)"
```

---

### Task 5: Backend endpoint'leri — `POST`/`DELETE /account/push-subscription`

**Files:**
- Modify: `src/adapters/api/routers/account_router.py`
- Modify: `tests/adapters/test_account_router.py`

**Interfaces:**
- Consumes: `PushSubscriptionRepository` (Task 1), `PushSubscription` (Task 1), `get_current_user`/`user_effective_tier` (mevcut `auth_utils`), `UserTier`/`tier_at_least` (mevcut `domain/models/user.py`).
- Produces: yok (uç nokta — Task 6'da frontend tarafından çağrılacak).

- [ ] **Step 1: Yeni testleri `test_account_router.py`'ye ekle**

Dosyanın importlarını güncelle — `from src.domain.models.user import User, UserTier, UserRole` satırının (üstte, `_make_user` tanımının hemen yanında) `UserTier` zaten import ediliyorsa dokunma, değilse ekle. `Push` testleri için dosyanın sonuna ekle:
```python
# ── /account/push-subscription ──────────────────────────────────────────────

def test_create_push_subscription_requires_auth(app_client):
    resp = app_client.post("/account/push-subscription", json={
        "endpoint": "https://push.example.com/1", "keys": {"p256dh": "k", "auth": "a"},
    })
    assert resp.status_code == 401


def test_create_push_subscription_blocks_free_tier(app_client):
    _override(app_client, _make_user(UserTier.FREE))
    try:
        resp = app_client.post("/account/push-subscription", json={
            "endpoint": "https://push.example.com/1", "keys": {"p256dh": "k", "auth": "a"},
        })
    finally:
        _clear(app_client)

    assert resp.status_code == 403


def test_create_push_subscription_saves_with_current_user_email(app_client):
    _override(app_client, _make_user(UserTier.PRO))
    try:
        with patch("src.adapters.api.routers.account_router.PushSubscriptionRepository") as MockRepo:
            repo = MagicMock()
            MockRepo.return_value = repo
            resp = app_client.post("/account/push-subscription", json={
                "endpoint": "https://push.example.com/1", "keys": {"p256dh": "k", "auth": "a"},
            })
    finally:
        _clear(app_client)

    assert resp.status_code == 201
    saved_sub = repo.save.call_args[0][0]
    assert saved_sub.email == "me@test.com"
    assert saved_sub.endpoint == "https://push.example.com/1"
    assert saved_sub.p256dh == "k"
    assert saved_sub.auth == "a"


def test_delete_push_subscription_requires_auth(app_client):
    resp = app_client.request("DELETE", "/account/push-subscription", json={"endpoint": "x"})
    assert resp.status_code == 401


def test_delete_push_subscription_removes_by_endpoint(app_client):
    _override(app_client, _make_user(UserTier.PRO))
    try:
        with patch("src.adapters.api.routers.account_router.PushSubscriptionRepository") as MockRepo:
            repo = MagicMock()
            MockRepo.return_value = repo
            resp = app_client.request(
                "DELETE", "/account/push-subscription",
                json={"endpoint": "https://push.example.com/1"},
            )
    finally:
        _clear(app_client)

    assert resp.status_code == 200
    repo.delete_by_endpoint.assert_called_once_with("https://push.example.com/1")
```

Mevcut `test_delete_account_success_deletes_user_and_subscription_and_clears_cookie` testini GÜNCELLE (yeni push repository patch'i + assertion ekle):
```python
def test_delete_account_success_deletes_user_and_subscription_and_clears_cookie(app_client):
    _override(app_client, _make_user(uid=42))
    try:
        with patch("src.adapters.api.routers.account_router.verify_password", return_value=True), \
             patch("src.adapters.api.routers.account_router.UserRepository") as MockUserRepo, \
             patch("src.adapters.api.routers.account_router.SubscriberRepository") as MockSubRepo, \
             patch("src.adapters.api.routers.account_router.PushSubscriptionRepository") as MockPushRepo:
            user_repo = MagicMock()
            user_repo.delete_user.return_value = True
            MockUserRepo.return_value = user_repo
            sub_repo = MagicMock()
            MockSubRepo.return_value = sub_repo
            push_repo = MagicMock()
            MockPushRepo.return_value = push_repo
            resp = app_client.request("DELETE", "/account", json={"password": "correct"})
    finally:
        _clear(app_client)

    assert resp.status_code == 200
    user_repo.delete_user.assert_called_once_with(42)
    sub_repo.delete_by_email.assert_called_once_with("me@test.com")
    push_repo.delete_by_email.assert_called_once_with("me@test.com")
    assert "nxs_session" in resp.headers.get("set-cookie", "")
```

**Not:** `test_delete_account_cancels_active_stripe_subscription` ve `test_delete_account_skips_stripe_cancel_when_no_customer_id` testleri de `patch("src.adapters.api.routers.account_router.SubscriberRepository")` kullanıyor — `PushSubscriptionRepository` artık gerçek (mock'lanmamış) haliyle çağrılacağından bu iki testte de `patch("src.adapters.api.routers.account_router.PushSubscriptionRepository")` eklenmeli (aksi halde gerçek DB'ye bağlanmaya çalışıp hata verir). Her ikisinde de `SubscriberRepository` patch'inin yanına aynı şekilde `PushSubscriptionRepository` patch'i ekle (mock nesnesini kullanmasan bile context manager'a dahil et).

- [ ] **Step 2: Testleri çalıştır — yeni push testleri FAIL etmeli, delete_account testi FAIL etmeli**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_account_router.py -v`
Expected: yeni 5 test FAIL (404 — route yok) + `test_delete_account_success...` FAIL (`PushSubscriptionRepository` account_router'da tanımlı değil)

- [ ] **Step 3: `account_router.py`'yi güncelle**

Import bloğuna ekle (mevcut `from src.adapters.repositories.subscriber_repository import SubscriberRepository` satırının altına):
```python
from src.adapters.repositories.push_subscription_repository import PushSubscriptionRepository
from src.domain.models.push_subscription import PushSubscription
from src.domain.models.user import User, TIER_DAILY_LIMITS, UserTier, tier_at_least
```
(`User, TIER_DAILY_LIMITS` zaten importluydu — satırı `UserTier, tier_at_least` ekleyerek GÜNCELLE, ikinci bir import satırı AÇMA.)

`DeleteAccountRequest` sınıfının hemen ÜSTÜNE (yani `# ── Hesap silme (v2.1.2)` bölümünden ÖNCE, `/account/saved` bloğunun sonuna) yeni bölümü ekle:
```python
# ── Web push bildirimleri (v2.5) ────────────────────────────────────────────
# Mevcut "Anlık Uyarılar" (instant) e-posta aboneliğinin AYNI keyword listesini
# paylaşır — ayrı bir keyword formu yok (bkz. 2026-08-25 spec). Pro+ gating
# _assert_instant_allowed (subscription_router.py) ile AYNI mantık.

class PushKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionRequest(BaseModel):
    endpoint: str
    keys: PushKeys


class PushUnsubscribeRequest(BaseModel):
    endpoint: str


@router.post("/push-subscription", status_code=201)
@limiter.limit("10/minute")
def create_push_subscription(
    request: Request,
    req: PushSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not tier_at_least(user_effective_tier(current_user), UserTier.PRO):
        raise HTTPException(
            status_code=403,
            detail="Tarayıcı bildirimleri Pro plan gerektirir. / Push notifications require a Pro plan.",
        )
    sub = PushSubscription(
        email=current_user.email, endpoint=req.endpoint,
        p256dh=req.keys.p256dh, auth=req.keys.auth,
    )
    PushSubscriptionRepository(db).save(sub)
    logger.info("Push aboneliği kaydedildi: user_id=%s", current_user.id)
    return {"subscribed": True}


@router.delete("/push-subscription")
@limiter.limit("10/minute")
def delete_push_subscription(
    request: Request,
    req: PushUnsubscribeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    PushSubscriptionRepository(db).delete_by_endpoint(req.endpoint)
    return {"subscribed": False}
```

`delete_account` fonksiyonunun içindeki `SubscriberRepository(db).delete_by_email(current_user.email)` satırının hemen altına ekle:
```python
    PushSubscriptionRepository(db).delete_by_email(current_user.email)
```

- [ ] **Step 4: Testleri tekrar çalıştır — hepsi PASS olmalı**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_account_router.py -v`
Expected: hepsi PASS

- [ ] **Step 5: Commit**

```bash
git add src/adapters/api/routers/account_router.py tests/adapters/test_account_router.py
git commit -m "feat: POST/DELETE /account/push-subscription + delete_account genişletmesi (Task 5/7)"
```

---

### Task 6: Frontend — abonelik toggle'ı, service worker, i18n

**Files:**
- Modify: `frontend/lib/api.ts` (yeni `subscribeToPushApi`/`unsubscribeFromPushApi`)
- Create: `frontend/lib/webpush.ts`
- Create: `frontend/components/PushNotificationToggle.tsx`
- Modify: `frontend/lib/i18n.ts` (yeni push string'leri, TR + EN)
- Modify: `frontend/app/account/page.tsx` (toggle'ı bülten kartına ekle)
- Modify: `frontend/public/sw.js` (`push` + `notificationclick` event handler'ları)
- Modify: `frontend/Dockerfile` (`NEXT_PUBLIC_VAPID_PUBLIC_KEY` build ARG)
- Modify: `docker-compose.prod.yml` (frontend build args'a `NEXT_PUBLIC_VAPID_PUBLIC_KEY` ekle)

**Interfaces:**
- Consumes: `POST/DELETE /account/push-subscription` (Task 5).
- Produces: yok — proje kararı gereği frontend'de browser-push API'lerini mock'layan birim test YOK (spec'te onaylandı, TTS özelliğiyle aynı emsal), `tsc --noEmit` + `npm run build` ile doğrulanır.

- [ ] **Step 1: `lib/api.ts`'e backend çağrılarını ekle**

Dosyanın `// ── Bülten aboneliği` bölümünden hemen ÖNCE (yani `unsaveArticleApi`'nin altına) ekle:
```typescript
// ── Web push bildirimleri (v2.5) ────────────────────────────────────────────

export async function subscribeToPushApi(endpoint: string, p256dh: string, auth: string): Promise<void> {
  await req(`${BASE}/account/push-subscription`, {
    method: "POST",
    body: JSON.stringify({ endpoint, keys: { p256dh, auth } }),
  });
}

export async function unsubscribeFromPushApi(endpoint: string): Promise<void> {
  await req(`${BASE}/account/push-subscription`, {
    method: "DELETE",
    body: JSON.stringify({ endpoint }),
  });
}
```

- [ ] **Step 2: `lib/webpush.ts`'i oluştur**

```typescript
// Tarayıcı push abonelik yardımcıları — Notification permission + Service
// Worker PushManager (v2.5). Tarayıcı desteklemiyorsa (Notification/
// serviceWorker/PushManager yok) sessizce false döner, hata FIRLATMAZ —
// çağıran taraf (PushNotificationToggle) buna göre kendini gizler.

import { subscribeToPushApi, unsubscribeFromPushApi } from "./api";

export function isPushSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    "Notification" in window &&
    "serviceWorker" in navigator &&
    "PushManager" in window
  );
}

function urlBase64ToUint8Array(base64: string): Uint8Array {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const base64Safe = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64Safe);
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}

export async function isPushSubscribed(): Promise<boolean> {
  if (!isPushSupported()) return false;
  const reg = await navigator.serviceWorker.ready;
  const sub = await reg.pushManager.getSubscription();
  return sub !== null;
}

export async function subscribeToPush(vapidPublicKey: string): Promise<void> {
  const permission = await Notification.requestPermission();
  if (permission !== "granted") throw new Error("Bildirim izni verilmedi.");

  const reg = await navigator.serviceWorker.ready;
  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
  });
  const json = sub.toJSON();
  try {
    await subscribeToPushApi(json.endpoint!, json.keys!.p256dh, json.keys!.auth);
  } catch (err) {
    await sub.unsubscribe();
    throw err;
  }
}

export async function unsubscribeFromPush(): Promise<void> {
  if (!isPushSupported()) return;
  const reg = await navigator.serviceWorker.ready;
  const sub = await reg.pushManager.getSubscription();
  if (!sub) return;
  const endpoint = sub.endpoint;
  await sub.unsubscribe();
  await unsubscribeFromPushApi(endpoint);
}
```

- [ ] **Step 3: `i18n.ts`'e string'leri ekle**

TR bloğunda `newsletterUnsubscribe: "Aboneliği İptal Et",` satırının hemen altına ekle:
```typescript
    pushLabel: "Bu tarayıcıda bildirimleri aç", pushSubscribedLabel: "Bu tarayıcıda bildirimler açık",
    pushErrorLabel: "Bildirim izni alınamadı, tekrar dener misin?",
    pushLockedReason: "Önce yukarıdan 'Anlık uyarı' seçip kaydetmelisin.",
```

EN bloğunda `newsletterUnsubscribe: "Unsubscribe",` satırının hemen altına ekle:
```typescript
    pushLabel: "Enable notifications in this browser", pushSubscribedLabel: "Notifications are on in this browser",
    pushErrorLabel: "Couldn't get notification permission, try again?",
    pushLockedReason: "First select 'Instant alerts' above and save.",
```

- [ ] **Step 4: `PushNotificationToggle.tsx` bileşenini oluştur**

```tsx
"use client";

// Tarayıcı push bildirimi aç/kapat toggle'ı (v2.5). Mevcut "Anlık Uyarılar"
// (instant) e-posta aboneliğinin AYNI keyword listesini paylaşır — `enabled`
// prop'u o abonelik aktif değilse (Free tier veya frequency !== "instant")
// false gelir, toggle disabled + tooltip'li gösterilir. Tarayıcı push API'lerini
// desteklemiyorsa (canSpeak/TTS'teki client-detection deseniyle aynı) bileşen
// hiç render edilmez.

import { useEffect, useState } from "react";
import { isPushSupported, isPushSubscribed, subscribeToPush, unsubscribeFromPush } from "@/lib/webpush";

interface Props {
  vapidPublicKey: string;
  enabled: boolean;
  lockedReason: string;
  label: string;
  subscribedLabel: string;
  errorLabel: string;
}

export function PushNotificationToggle({
  vapidPublicKey, enabled, lockedReason, label, subscribedLabel, errorLabel,
}: Props) {
  const [supported, setSupported] = useState(false);
  const [subscribed, setSubscribed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    const ok = isPushSupported();
    setSupported(ok);
    if (ok) isPushSubscribed().then(setSubscribed).catch(() => {});
  }, []);

  if (!supported || !vapidPublicKey) return null;

  async function toggle() {
    setBusy(true);
    setError(false);
    try {
      if (subscribed) {
        await unsubscribeFromPush();
        setSubscribed(false);
      } else {
        await subscribeToPush(vapidPublicKey);
        setSubscribed(true);
      }
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ marginTop: 12 }}>
      <label
        style={{ display: "flex", alignItems: "center", gap: 8, opacity: enabled ? 1 : 0.5, cursor: enabled ? "pointer" : "not-allowed" }}
        title={!enabled ? lockedReason : undefined}
      >
        <input type="checkbox" checked={subscribed} disabled={!enabled || busy} onChange={toggle} />
        {subscribed ? subscribedLabel : label}
      </label>
      {error && <p style={{ color: "var(--danger, #e5484d)", fontSize: "0.85rem", marginTop: 4 }}>{errorLabel}</p>}
    </div>
  );
}
```

- [ ] **Step 5: `account/page.tsx`'e toggle'ı entegre et**

Dosyanın en üstündeki import bloğuna ekle (`import { NewsCard } from "@/components/NewsCard";` satırının altına):
```typescript
import { PushNotificationToggle } from "@/components/PushNotificationToggle";
```

`NEWSLETTER_TOPICS` sabitinin hemen altına ekle:
```typescript
const VAPID_PUBLIC_KEY = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY ?? "";
```

Bülten kartındaki buton satırının kapanışından (`</div>` — mevcut satır 527) hemen SONRA, kartın kapanışından (`</div>` — mevcut satır 528) ÖNCE ekle:
```tsx
          <PushNotificationToggle
            vapidPublicKey={VAPID_PUBLIC_KEY}
            enabled={nlFrequency === "instant" && (user.effective_tier ?? user.tier) !== "free"}
            lockedReason={t.pushLockedReason}
            label={t.pushLabel}
            subscribedLabel={t.pushSubscribedLabel}
            errorLabel={t.pushErrorLabel}
          />
```

- [ ] **Step 6: `sw.js`'e push event handler'larını ekle**

`frontend/public/sw.js` dosyasının SONUNA (mevcut `fetch` event listener'ının altına) ekle:
```javascript
self.addEventListener("push", (event) => {
  if (!event.data) return;
  let payload;
  try {
    payload = event.data.json();
  } catch {
    return;
  }
  const { title, body, url } = payload;
  event.waitUntil(
    self.registration.showNotification(title || "NexStream", {
      body: body || "",
      icon: "/icons/icon-192.png",
      data: { url: url || "/" },
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = event.notification.data?.url || "/";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clientsList) => {
      for (const client of clientsList) {
        if (client.url === targetUrl && "focus" in client) return client.focus();
      }
      if (self.clients.openWindow) return self.clients.openWindow(targetUrl);
    })
  );
});
```

- [ ] **Step 7: `Dockerfile`'a build ARG ekle**

`frontend/Dockerfile`'da `ARG NEXT_PUBLIC_POSTHOG_HOST="https://us.i.posthog.com"` / `ENV NEXT_PUBLIC_POSTHOG_HOST=$NEXT_PUBLIC_POSTHOG_HOST` satırlarının hemen altına, `RUN npm run build`'den ÖNCE ekle:
```dockerfile
# Web push (v2.5) — boşsa toggle bileşeni hiç render edilmez (vapidPublicKey boş kontrolü).
ARG NEXT_PUBLIC_VAPID_PUBLIC_KEY=""
ENV NEXT_PUBLIC_VAPID_PUBLIC_KEY=$NEXT_PUBLIC_VAPID_PUBLIC_KEY
```

- [ ] **Step 8: `docker-compose.prod.yml`'de frontend build args'a ekle**

`frontend` servisinin `build.args` bloğuna (`NEXT_PUBLIC_POSTHOG_HOST` satırının altına) ekle:
```yaml
        NEXT_PUBLIC_VAPID_PUBLIC_KEY: ${NEXT_PUBLIC_VAPID_PUBLIC_KEY:-}
```

- [ ] **Step 9: Tip kontrolü + prod build doğrulaması**

Run: `cd frontend; npx tsc --noEmit`
Expected: hata yok

Run: `cd frontend; npm run build`
Expected: build başarılı (frontend container ÇALIŞMIYORSA host'ta çalıştır — bkz. CLAUDE.md "npm run build'i frontend container ÇALIŞIRKEN host'ta ÇALIŞTIRMA" gotcha'sı, container'ı önce durdur veya sadece `tsc --noEmit` ile yetin)

- [ ] **Step 10: Commit**

```bash
git add frontend/lib/api.ts frontend/lib/webpush.ts frontend/components/PushNotificationToggle.tsx frontend/lib/i18n.ts frontend/app/account/page.tsx frontend/public/sw.js frontend/Dockerfile docker-compose.prod.yml
git commit -m "feat: frontend push toggle'ı + service worker handler'ları + i18n (Task 6/7)"
```

---

### Task 7: Final regresyon, CLAUDE.md güncellemesi, PR

**Files:**
- Modify: `CLAUDE.md` (roadmap #12 kapat, mimari listesine `push_subscriptions` ekle, env var listesine VAPID_* ekle)

**Interfaces:**
- Consumes: tüm önceki task'ların birleşik hali.
- Produces: yok — kapanış görevi.

- [ ] **Step 1: Tam backend regresyonu**

Run: `venv\Scripts\python.exe -m pytest tests/ -v`
Expected: 780 passed (775'ten Task 4 sonrası + 5 Task 5 account_router testi — `test_delete_account_success...` testi YENİ eklenmedi, sadece genişletildi, sayıya dahil değil), hiç FAIL yok

- [ ] **Step 2: Frontend tip kontrolü + build (tekrar, tüm değişikliklerle birlikte)**

Run: `cd frontend; npx tsc --noEmit`
Expected: hata yok

- [ ] **Step 3: `CLAUDE.md`'yi güncelle**

- YOL HARİTASI madde 12'yi `~~Web Push bildirimleri (breaking news)~~ — ✅ tamamlandı` olarak işaretle, kısa özet ekle (mevcut kaynak paylaşım kararı, WebPushPort isim çakışması notu).
- MİMARİ bölümündeki `adapters/notifications/` listesine `pywebpush_adapter.py` + `web_push_factory.py` ekle, `domain/ports/` listesine `push_subscription_port.py` + `web_push_port.py` ekle.
- `migrations/` listesine `v2_5_push_subscriptions.sql` ekle.
- BİLİNEN NOTLAR'daki env var listesine `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`, `NEXT_PUBLIC_VAPID_PUBLIC_KEY` ekle.
- **Prod deploy notu ekle:** `migrations/v2_5_push_subscriptions.sql` prod'da ELLE çalıştırılmalı (dev'de `create_all` otomatik ekler, prod'da migrations/ esastır — mevcut proje kuralı).

- [ ] **Step 4: Commit + PR**

```bash
git add CLAUDE.md
git commit -m "docs: web push bildirimleri (roadmap #12) tamamlandı"
git push -u origin <branch-adı>
gh pr create --title "feat: web push bildirimleri (roadmap #12)" --body "Spec: docs/superpowers/specs/2026-08-25-web-push-bildirimleri-design.md"
```

- [ ] **Step 5: CI yeşil olunca merge et, prod'a otomatik deploy'u bekle**

`main`'e merge sonrası GitHub Actions `deploy` job'ı otomatik SSM üzerinden redeploy tetikler (roadmap #19 otomasyonu). Redeploy sonrası **prod'da migration'ı elle çalıştır** (SSM):
```bash
docker exec -i nexstream_db psql -U nexstream -d nexstream < migrations/v2_5_push_subscriptions.sql
```
Ardından `/api/health` ile doğrula, bir test hesabıyla `/account`'ta "Anlık uyarı" seçip toggle'ı açarak uçtan uca doğrula (gerçek push almak için gerçek bir tarayıcı gerekir — Playwright ile bildirim izni simülasyonu mümkün ama gerçek push teslimatı test edilemez, sadece abonelik kaydı doğrulanabilir).
