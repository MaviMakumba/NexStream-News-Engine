# Web Push Bildirimleri — Tasarım Spec'i

**Tarih:** 25 Ağustos 2026
**Roadmap maddesi:** #12
**Durum:** Onaylandı, implementasyon planına geçilecek

## Amaç

Kullanıcıların zaten sahip olduğu "anlık (instant) keyword uyarısı" e-posta
akışına (bkz. `subscribers` tablosu, `frequency="instant"`, Pro+ tier gating,
`NewsService._send_keyword_alerts`) tarayıcı push bildirimini **ikinci bir
kanal** olarak eklemek. Yeni bir "breaking news" kavramı icat edilmiyor —
mevcut keyword eşleşmesi tetikleyici olarak aynen kullanılıyor.

## Kapsam dışı (YAGNI)

- Editöryel/skor tabanlı "önemli haber" kavramı yok — sadece keyword eşleşmesi.
- Anonim/giriş yapmamış kullanıcı push'u yok — oturum zorunlu.
- Push için ayrı bir keyword listesi yok — email "instant" aboneliğiyle paylaşılıyor.
- Frontend'de aktif cihaz listesi/yönetimi yok (v1) — sadece tek "bu tarayıcıda
  bildirimleri aç/kapat" toggle'ı.

## Mimari & Bileşenler

Hexagonal desene uyularak:

- **Domain modeli:** `src/domain/models/push_subscription.py` → `PushSubscription`
  dataclass (`email: str`, `endpoint: str`, `p256dh: str`, `auth: str`,
  `id: Optional[int]`, `created_at: Optional[datetime]`)
- **Port:** `src/domain/ports/push_subscription_port.py` →
  `PushSubscriptionRepositoryPort` (ABC) — `save`, `get_by_email`,
  `get_by_endpoint`, `delete_by_endpoint`, `delete_by_email`. Stil:
  `src/domain/ports/subscriber_port.py` ile birebir aynı.
- **Port:** `src/domain/ports/web_push_port.py` → `WebPushPort` (ABC) —
  `send(subscription: PushSubscription, title: str, body: str, url: str) -> bool`.
  **İsim bilinçli olarak `NotificationPort` DEĞİL** — mevcut
  `NotificationPort` (`src/domain/ports/notification_port.py`) `/ws/feed`
  canlı yayını için, alakasız bir kavram; isim çakışması karışıklık yaratırdı.
- **Adapter:** `src/adapters/notifications/pywebpush_adapter.py` →
  `PyWebPushAdapter(WebPushPort)` — `pywebpush` kütüphanesi, VAPID
  private key + subject ile imzalar. `requirements.txt`'e `pywebpush` eklenir.
- **Repository adapter:** `src/adapters/repositories/push_subscription_repository.py`
  (PostgreSQL) — `src/adapters/repositories/subscriber_repository.py` ile aynı stil.
- **Migration:** `migrations/v2_5_push_subscriptions.sql`:
  ```sql
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
- **`NewsService`** yeni opsiyonel bağımlılıklar alır: `push_repository:
  Optional[PushSubscriptionRepositoryPort]`, `web_push: Optional[WebPushPort]`
  — mevcut `subscriber_repository`/`email_port` None-safe deseniyle aynı.
- **Backend endpoint'ler** (`account_router.py`'e eklenir, mevcut
  `saved_articles`/`api-key` endpoint'leriyle aynı dosya/stil):
  - `POST /account/push-subscription` — `current_user: User = Depends(get_current_user)`
    zorunlu. Body: `{endpoint: str, keys: {p256dh: str, auth: str}}`. Pro+
    kontrolü `_assert_instant_allowed`'daki `tier_at_least(user_effective_tier(...),
    UserTier.PRO)` ile aynı mantık — Free ise 403. `email=current_user.email`
    ile upsert (`endpoint` UNIQUE çakışmasında güncelle).
  - `DELETE /account/push-subscription` — body: `{endpoint: str}`, o satırı siler.
- **`delete_account`** (`account_router.py`) genişletilir: mevcut
  `SubscriberRepository(db).delete_by_email(...)` satırının yanına
  `PushSubscriptionRepository(db).delete_by_email(...)` eklenir.
- **Frontend:**
  - `frontend/lib/webpush.ts` — `subscribeToPush()` / `unsubscribeFromPush()`
    yardımcıları (Notification.requestPermission → serviceWorker.ready →
    pushManager.subscribe/unsubscribe → backend'e POST/DELETE).
  - `/account` sayfasında mevcut "Anlık Uyarılar" (instant) bölümünün yanına
    bir toggle bileşeni (`PushNotificationToggle` component'i) — mevcut
    `i18n.ts::UI[lang]` sözlüğüne yeni string'ler eklenir (SOLID i18n kuralı).
  - `frontend/public/sw.js`'e `push` ve `notificationclick` event handler'ları
    eklenir (mevcut install/activate/fetch handler'larına ek, mevcut yapı
    bozulmaz).
- **Yeni env var'lar:**
  - Backend: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`
    (25 Ağu 2026'da zaten üretildi, hem lokal hem prod `.env`'de hazır).
  - Frontend build-time: `NEXT_PUBLIC_VAPID_PUBLIC_KEY` (`NEXT_PUBLIC_POSTHOG_KEY`
    ile aynı desen — `frontend/Dockerfile` ARG + `docker-compose.prod.yml`
    frontend build args'a eklenir).

## Veri Akışı

**Abone olma:**
1. Kullanıcı `/account`'ta zaten `frequency="instant"` + keyword seçmiş olmalı
   (Pro+ gating oradan geçiyor, bkz. `subscription_router.py::_assert_instant_allowed`).
2. Toggle'a basar → `Notification.requestPermission()` → izin verilirse
   `navigator.serviceWorker.ready` → `pushManager.subscribe({userVisibleOnly:
   true, applicationServerKey: <VAPID public key>})`.
3. Dönen `PushSubscription` (`endpoint`, `keys.p256dh`, `keys.auth`)
   `POST /account/push-subscription`'a gider. Backend Pro+ doğrular,
   `email=current_user.email` ile satırı upsert eder.

**Gönderim** (worker, ingestion sırasında — `_send_keyword_alerts` genişletilir):
```
_send_keyword_alerts(article):
  for sub in subscriber_repository.get_active_subscribers():
      if sub.frequency != "instant" or not sub.keywords: continue
      kw = matched_keyword(article, sub.keywords)
      if kw is None: continue
      email_port.send_alert(...)                                  # mevcut
      if push_repository and web_push:                             # YENİ
          for push_sub in push_repository.get_by_email(sub.email):
              ok = web_push.send(push_sub, title=article.title,
                                  body=f"Takip ettiğin '{kw}' ile eşleşti",
                                  url=article.url)
              if not ok:
                  push_repository.delete_by_endpoint(push_sub.endpoint)
```
Email ve push aynı döngüde, aynı eşleşmede tetikleniyor — ayrı bir tetikleyici yok.

**Abonelikten çıkma:** Toggle kapatılınca `pushManager.getSubscription()` →
`.unsubscribe()` (tarayıcı) + `DELETE /account/push-subscription` (backend).
Hesap silinirken otomatik temizlenir (yukarıya bakın).

**Bildirime tıklama:** `sw.js::notificationclick` → `event.notification.data.url`'i
açar/mevcut sekmeye focus eder.

## Hata Yönetimi

- `PyWebPushAdapter.send()` **hiçbir zaman exception fırlatmaz**:
  - HTTP 404/410 → `False`, loglamaz (rutin — abonelik ölmüş).
  - Diğer hatalar (429, 5xx, network) → `logger.warning(...)` + `False`,
    satır SİLİNMEZ (geçici olabilir, bir sonrakinde tekrar denenir).
- Push döngüsü **fail-open**: email adımından SONRA, ayrı try/except —
  push başarısızlığı email'i asla engellemez, bir push subscription'ın
  hatası diğerlerini engellemez.
- `VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY` boşsa → DI'da `web_push=None`,
  `NewsService` push adımını tamamen atlar (diğer opsiyonel entegrasyonlarla
  — Redis/HuggingFace/Sentry/PostHog — aynı "key yoksa no-op" deseni).
- Frontend'de `Notification`/`serviceWorker`/`PushManager` yoksa toggle
  sessizce gizlenir/disabled olur, hata gösterilmez.
- `POST /account/push-subscription` Pro+ değilse 403 — `_assert_instant_allowed`
  ile birebir aynı hata mesajı deseni.

## Test Planı

TDD, gerçek HTTP çağrısı yok (proje kuralı):

- **`PyWebPushAdapter`:** `pywebpush.webpush()` mock — başarı → `True`;
  `WebPushException` + 404/410 → `False`, log yok; diğer status → `False` +
  `logger.warning` çağrıldığı doğrulanır; VAPID key constructor'a doğru geçiyor.
- **`PushSubscriptionRepository`:** save/get_by_email/delete_by_endpoint/
  delete_by_email, UNIQUE endpoint çakışmasında upsert.
- **`NewsService._send_keyword_alerts`:** email+push birlikte tetikleniyor;
  `web_push=None` iken push atlanıyor (email yine gidiyor); push `False`
  dönünce subscription siliniyor; bir push'un hatası diğerlerini/email'i
  engellemiyor (fail-open).
- **`POST /account/push-subscription`:** Free 403, Pro+ 201 + doğru email
  ile yazılıyor, tekrar gönderilince upsert (satır çoğalmıyor).
- **`DELETE /account/push-subscription`** + **`delete_account`** genişlemesi:
  hesap silinince push subscription'ları da temizleniyor.
- **Frontend:** birim test yok (browser push API'lerini mock'lamak YAGNI,
  proje TTS özelliğinde de aynı yaklaşımı kullandı) — `tsc --noEmit` +
  `npm run build` + canlı/manuel doğrulama yeterli.

## Açık noktalar / sonraki adım

Yok — tüm bölümler kullanıcı tarafından onaylandı. Sıradaki adım
`superpowers:writing-plans` ile implementasyon planı yazmak.
