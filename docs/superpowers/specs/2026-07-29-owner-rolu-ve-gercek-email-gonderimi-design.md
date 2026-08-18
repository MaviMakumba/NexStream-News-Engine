# Owner rolü, kademeli rol yönetimi ve gerçek e-posta gönderimi — Tasarım

**Tarih:** 29 Temmuz 2026
**Dal:** `optimize/t3-small-ram` (canlı sürüm)
**Durum:** Tasarım onaylandı, uygulama bekliyor

---

## Problem

Site canlıya çıktıktan sonra üç somut sorun ortaya çıktı:

1. **Sahip hesabı "Ücretsiz" görünüyor.** `erenk897@gmail.com` `ADMIN_EMAILS`
   bootstrap'i sayesinde admin yetkisine sahip ama DB'de `role=user`,
   `tier=free`. Rol ve tier birbirinden bağımsız eksenler olduğu için "admin
   ama ücretsiz kullanıcı" hali doğuyor: günlük kota 100 istek, Pro+ özellikler
   (WebSocket akış, ilişkili haberler, ham veri export) kapalı.

2. **E-posta doğrulama banner'ı sahibe de gösteriliyor** ve doğrulama
   yapılamıyor, çünkü:

3. **Canlıda hiçbir e-posta gönderilmiyor.** Prod `.env`'de `RESEND_API_KEY`
   boş; `get_email_adapter()` bu durumda sessizce `ConsoleEmailAdapter`'a
   düşüyor ve mailler yalnızca log'a yazılıyor. Bu sadece doğrulama mailini
   değil şifre sıfırlama, günlük digest ve keyword alert'lerin **tamamını**
   etkiliyor. Hiçbir yerde uyarı yok — v2.0'daki "worker'ın interneti yoktu"
   vakasıyla aynı sessiz işlevsizlik deseni.

Ek olarak yetkilendirme tarafında bir boşluk var: `PATCH /admin/users/{id}/role`
`require_admin` istiyor, yani **herhangi bir admin herhangi bir başka adminin
rolünü düşürebiliyor**. Tek koruma "kendi rolünü düşüremezsin" guard'ı.

---

## Çözüm Özeti

Dört parça:

1. Rol hiyerarşisine `owner` seviyesi eklenir (env ile bootstrap edilir).
2. Owner, `tier` alanına dokunmadan her yerde Enterprise+ muamelesi görür.
3. Rol değiştirme kademeli hale gelir: herkes yalnızca kendinden düşük
   roldekilere karışabilir.
4. `SmtpEmailAdapter` eklenir; e-posta gerçekten gönderilir ve konsol
   adapter'ına düşüş prod'da sessiz olmaktan çıkar.

---

## 1. `owner` rolü

### Domain (`src/domain/models/user.py`)

`UserRole` enum'una `OWNER = "owner"` eklenir, `_ROLE_RANK` dördüncü seviyeyi
alır:

```
user (0) < moderator (1) < admin (2) < owner (3)
```

`role_at_least` olduğu gibi çalışmaya devam eder. DB migration **gerekmez** —
`users.role` kolonu zaten `VARCHAR`, yeni değer ek şema değişikliği istemez.

### Bootstrap (`src/infrastructure/config/settings.py`)

`owner_emails: str = ""` ayarı (`OWNER_EMAILS` env) + `owner_email_set`
property — mevcut `admin_emails` / `admin_email_set` deseninin birebir kopyası.
Owner rolü **API üzerinden hiçbir zaman atanamaz**; tek kaynak bu env değişkeni
(veya DB'ye elle yazılan `role='owner'`).

### Yetki çözümü (`src/adapters/api/auth_utils.py`)

- `has_owner_role(user)` → `role == OWNER` **veya** e-posta `owner_email_set`'te
- `has_admin_role` owner'ı da kapsar (owner ⊃ admin ⊃ moderator)
- `effective_role(user)` owner'ı `"owner"` olarak yansıtır
- Yeni `require_owner` dependency (401/403 ayrımı `require_admin` ile aynı)

`ADMIN_EMAILS` desteği aynen korunur — geriye dönük uyumluluk.

---

## 2. Owner = sınırsız erişim, `tier` alanına dokunmadan

### Saf domain fonksiyonu

Owner tespiti env'e (`OWNER_EMAILS`) bakmayı gerektirir; domain katmanı
`settings`'i import edemez (hexagonal kural). Bu yüzden iş ikiye ayrılır:

- `src/domain/models/user.py` → `effective_tier(tier: UserTier, is_owner: bool)
  -> UserTier` — saf fonksiyon, owner ise `ENTERPRISE` döner
- `src/adapters/api/auth_utils.py` → `user_effective_tier(user) -> UserTier` —
  `has_owner_role(user)` ile owner'ı çözüp saf fonksiyonu çağıran sarmalayıcı

Çağrı noktaları her zaman sarmalayıcıyı kullanır.

### Değiştirilecek çağrı noktaları

Hepsi `user.tier` yerine `user_effective_tier(user)` okur:

| Dosya | Satır bağlamı | Etki |
|---|---|---|
| `auth_utils.py::check_tier_limit` | `TIER_DAILY_LIMITS.get(user.tier)` | Günlük kota sınırsız |
| `account_router.py::usage` | `TIER_DAILY_LIMITS.get(current_user.tier)` | Panel "sınırsız" gösterir |
| `v1/news_router_v1.py::search` | `TIER_SEARCH_RESULT_CAP[user.tier]` | 200 sonuç tavanı |
| `v1/news_router_v1.py::export` | `user.tier != ENTERPRISE` | Export açılır |
| `v1/news_router_v1.py::related` | `tier_at_least(user.tier, PRO)` | Açılır |
| `news_router.py::related` (legacy) | `tier_at_least(user.tier, PRO)` | Açılır |
| `websocket_router.py` | `tier_at_least(user.tier, PRO)` | Canlı akış açılır |
| `subscription_router.py::_assert_instant_allowed` | `tier_at_least(user.tier, PRO)` | Instant alert açılır |

Public `/news/search` **değişmez** — o her zaman Free tavanını uygular (landing
demosu, kimlikten bağımsız).

`billing_router.py::create_checkout` owner için 400 döner: owner'ın satın
alacağı bir şey yok, dev-mode tier oynaması istatistikleri kirletmesin.

### Arayüz

`/auth/me` yanıtına iki alan eklenir: `is_owner: bool` ve
`effective_tier: str`. Frontend (`lib/types.ts`, `TierBadge`, `account`,
`NavbarImpl`) rozeti `effective_tier`'dan okur; `is_owner` ise:

- Rozet metni "Kurucu" / "Owner" (`lib/i18n.ts`'e yeni anahtar — hardcoded
  metin yasak, mevcut kural)
- Hesap sayfasındaki yükseltme/fiyatlandırma kartı owner'a hiç render edilmez
- `EmailVerifyBanner` owner'a gösterilmez

DB'deki `tier` alanı `free` kalır → admin panelindeki `is_paying` /
"gerçekten ödeyen müşteri" ayrımı kirlenmez.

---

## 3. Kademeli rol yönetimi

`PATCH /admin/users/{id}/role` kuralları:

1. İstek sahibi **moderator veya üstü** olmalı (router zaten `require_moderator`)
2. **Hedefin mevcut rolü < istek sahibinin rolü** — kendi seviyendekine ve
   üstüne dokunamazsın
3. **Atanacak yeni rol ≤ istek sahibinin rolü** — kendi seviyene kadar terfi
   verebilirsin
4. `owner` rolü **asla** atanamaz (400) — tek kaynak `OWNER_EMAILS`
5. Kimse kendi rolünü değiştiremez (400)

Sonuçlar: moderatör kullanıcıları moderatörlüğe terfi ettirebilir ama
moderatöre/admin'e dokunamaz. Admin moderatör ve kullanıcıları yönetebilir,
yeni admin üretebilir, ama mevcut bir adminin rolünü **düşüremez**. Owner
herkesi yönetir, kendisine kimse dokunamaz.

İhlallerde 403 (`"Bu kullanıcının rolünü değiştirme yetkiniz yok"`).

Rol değişimi her zaman **gerçek kullanıcı oturumu** ister — route
`get_current_user` kullandığı için paylaşımlı `X-API-Key` tek başına yetmez
(mevcut davranış, korunuyor).

Frontend `admin/users` sayfası: rol `<select>`'i yalnızca kural 2+3'ün izin
verdiği satırlarda etkin, izin verilmeyen satırlarda salt-okunur rozet. Seçenek
listesi istek sahibinin rolüyle sınırlanır (`owner` hiç listelenmez).

---

## 4. Gerçek e-posta gönderimi

### `SmtpEmailAdapter`

`EmailPort`'un üçüncü implementasyonu, `smtplib` + STARTTLS ile. Gmail app
password ile çalışır: günlük ~500 mail, domain doğrulaması gerekmez, **tüm**
alıcılara ulaşır (Resend'in sandbox kısıtı: doğrulanmış domain olmadan yalnızca
hesap sahibinin adresine gönderilebilir).

**DRY:** `ResendEmailAdapter`'ın beş `send_*` metodu HTML kurucularını çağırıp
tek bir `_post`'a veriyor. Bu ortak gövde `_HtmlEmailAdapter` ara sınıfına
taşınır: beş `send_*` metodunu bir kez tanımlar, soyut
`_deliver(to, subject, html) -> bool` çağırır. `ResendEmailAdapter` ve
`SmtpEmailAdapter` yalnızca `_deliver`'ı implemente eder. `ConsoleEmailAdapter`
olduğu gibi kalır (log formatı farklı).

Yeni ayarlar: `SMTP_HOST`, `SMTP_PORT` (587), `SMTP_USER`, `SMTP_PASSWORD`,
`SMTP_FROM` (boşsa `EMAIL_FROM`), `SMTP_STARTTLS` (true).

### Adapter seçimi

`EMAIL_PROVIDER` ayarı: `auto` (varsayılan) | `smtp` | `resend` | `console`.
`auto` sırası: SMTP kimlikleri doluysa SMTP → `RESEND_API_KEY` doluysa Resend →
Console. Açık değerler test ve hata ayıklama için zorlama sağlar.

### Sessiz kırılmanın kapatılması

Bugünkü sorunun kök nedeni Console'a düşüşün hiçbir iz bırakmaması. İki katman:

1. **Açılışta:** `ENVIRONMENT=production` iken seçilen adapter Console ise
   `logger.error` ile net uyarı (uygulama **durdurulmaz** — mail altyapısı
   çökünce site de çökmemeli, mevcut fail-open felsefesiyle tutarlı).
2. **`/health`:** yanıta `email` alanı eklenir (`"smtp"` / `"resend"` /
   `"console (mail gönderilmiyor)"`). Böylece durum tek bakışta görünür.

Bu, "deploy'u `/health` yeşil mi diye değil iş çıktısıyla doğrula" dersinin
karşılığı: e-posta yolunun gerçekten çalışıp çalışmadığı artık gözlemlenebilir.

### Owner ve doğrulama

Owner `email_verified` şartından muaf (banner + checkout gate). Diğer adminler
muaf **değil** — muafiyet tek kişiye özgü kalır. `email_verified` alanı
gerçeğe sadık kalır (owner için `true` yalanı yazılmaz); muafiyet gösterim ve
gate katmanında uygulanır.

---

## Test Planı

Backend (mevcut 553'ün üstüne):

- `owner` rol hiyerarşisi: `role_at_least`, `has_owner_role`, `effective_role`,
  `require_owner` (401/403/geçiş)
- `ADMIN_EMAILS` geriye dönük uyumluluğu bozulmadı
- `effective_tier`: owner → Enterprise; normal kullanıcı → kendi tier'ı
- Kota/gating: owner için `check_tier_limit` sınırsız, export/related/WS/instant
  açık; **Free kullanıcı için hepsinin hâlâ kapalı** olduğu (regresyon)
- Rol matrisi: moderator→user (izin), moderator→moderator hedefi (403),
  admin→moderator (izin), admin→admin hedefi (403), owner→admin (izin),
  herkes→`owner` ataması (400), kendi rolü (400)
- `SmtpEmailAdapter`: `smtplib.SMTP` mock'lu — STARTTLS + login çağrıldı mı,
  gövde UTF-8 mi, hata durumunda `False` dönüyor mu (exception sızmıyor)
- `get_email_adapter()` seçim matrisi (auto/smtp/resend/console)
- Prod'da Console seçilirse uyarı loglanıyor; `/health` `email` alanı

Frontend: `npx tsc --noEmit` (frontend container çalışırken host'ta
`npm run build` **çalıştırılmaz** — `.next` çakışması).

Canlı doğrulama (deploy sonrası, **iş çıktısıyla**):

1. Sahip hesabıyla giriş → rozet "Kurucu", banner yok, export/WS açık
2. `boeingb747.800@gmail.com` gibi ikinci bir adrese gerçek kayıt → doğrulama
   maili **gerçekten kutuya düştü mü**
3. Linke tıkla → `email_verified=true`
4. Admin panelinde rol matrisinin beklendiği gibi kısıtlandığı

---

## Deploy

Prod `.env`'e eklenecek: `OWNER_EMAILS`, `EMAIL_PROVIDER=smtp`, `SMTP_HOST`,
`SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`. Ardından
`docker compose -f docker-compose.prod.yml up -d app worker scheduler`
(**`restart` yetmez** — env yeniden okunmaz). `docker-compose.prod.yml` ve
`docker-compose.yml`'de yeni değişkenler `${VAR:-default}` deseniyle app,
worker ve scheduler servislerine geçirilir (mail gönderen üç servis de bunlar).

Kullanıcı tarafında gereken tek manuel adım: Gmail'de 2 adımlı doğrulama açıp
16 haneli uygulama şifresi üretmek.

---

## Kapsam Dışı (bilinçli)

- Resend domain doğrulaması (DuckDNS tek TXT kaydı tutar; SPF+DKIM için yeterli
  değil). Resend adapter'ı yedek olarak kodda kalır.
- Owner rolünün admin panelinden atanabilmesi — güvenlik gereği env'e sabit.
- E-posta gönderim kuyruğu/retry altyapısı — mevcut best-effort fail-open
  davranışı korunur.
