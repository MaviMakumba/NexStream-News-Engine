# NexStream — İlk Prod Deploy Kılavuzu ($0/ay — v2.0)

Bu dosya, hiçbir VPS/domain yokken ve bütçe **gerçekten $0/ay** iken sıfırdan
canlıya çıkış için adım adım kontrol listesidir. Kod tarafı (`docker-compose.prod.yml`,
nginx, güvenlik guard'ları, Redpanda mesajlaşma) v1.17/v1.18 denetiminden sonra
hazır — eksik olan tamamen altyapı (hesap açma, DNS) adımları.

Tahmini süre: 2-4 saat (Oracle'da "Out of host capacity" ile karşılaşırsanız
birden fazla deneme/gün gerekebilir — bkz. §2). Tahmini maliyet: **$0/ay** —
Oracle Cloud "Always Free" ARM sunucu + DuckDNS ücretsiz subdomain, ikisi de
sonsuza dek bedava (kredi kartı sadece kimlik doğrulama için istenir, ücretlendirme
yok).

---

## 0. Ön koşullar

- Kredi kartı (Oracle hesap doğrulaması için — Always Free kaynaklarda ÜCRETLENDİRME YOK)
- SSH client (Windows 11'de zaten var: `ssh` PowerShell/Terminal'de çalışır)
- Bu repo'nun GitHub'da public/erişilebilir olması (zaten öyle — bkz. v1.17
  denetimindeki `.env` sızıntı notu, güncel `.env` artık repo'da YOK)
- **Önce Faz A'yı (Kafka → Redpanda geçişi) tamamla ve `docker compose up -d` ile
  lokalde doğrula** — bu kılavuz Redpanda'nın çalıştığını varsayar.

---

## 1. DuckDNS — ücretsiz subdomain (domain satın almanın yerine)

1. duckdns.org'a git, GitHub/Google/Reddit ile giriş yap (ücretsiz, ödeme yok)
2. Bir subdomain seç, örn. `nexstream` → `nexstream.duckdns.org`
3. Panelde gösterilen **token**'ı not et (opsiyonel — sadece ileride dinamik IP
   güncelleme cron'u eklemek istersen lazım olur; aşağıdaki statik IP yolunda
   gerekmiyor)
4. IP alanını ŞİMDİ doldurma — önce Oracle'ın statik IP'sine ihtiyacın var (adım 2)

---

## 2. Oracle Cloud "Always Free" ARM instance (domain satın almanın yerine gerçek VPS)

1. cloud.oracle.com'da hesap aç (kart kimlik doğrulama için istenir, ev adresi +
   telefon doğrulaması da var — 15-20 dk ayır)
2. Compute → Instances → Create Instance
3. Image: **Ubuntu 24.04 (aarch64)** — Oracle'ın resmi Canonical imajı, ARM
   shape'ler için ayrıca listelenir
4. Shape: **Ampere → VM.Standard.A1.Flex** — örn. **2 OCPU / 12GB RAM** ayır
   (ücretsiz tavan 4 OCPU/24GB — ileride ikinci bir ücretsiz instance için pay
   bırakmak istersen 2/12 ile başla, istersen tek makinede 4/24'e kadar çıkabilirsin)
5. **⚠️ Bilinen sorun — "Out of host capacity":** A1.Flex ücretsiz kapasitesi
   popüler bölgelerde (özellikle us-ashburn-1, eu-frankfurt-1) sık sık tükeniyor.
   Bu hesabınla ilgili bir bozukluk DEĞİL, çok yaygın bir durum. Çözüm sırası:
   - Instance oluşturma formunda her **Availability Domain**'i dene (bölge içinde
     birden fazla AD olabilir)
   - Hesap açarken (region seçimi sonradan kolayca değiştirilemiyor) daha az
     popüler bir bölge seçmeyi düşün
   - Saatler/günler içinde tekrar dene — kapasite diğer kullanıcıların
     kaynaklarını bırakmasıyla açılır
   - Topluluk retry script'leri var (belirli aralıklarla Create Instance API'sini
     otomatik deneyen araçlar) — bu repo'ya dahil edilmedi (altyapı/hesap aracı,
     uygulama kodu değil), istersen ayrıca araştırılabilir
6. SSH key ekle (yoksa: `ssh-keygen -t ed25519 -C "nexstream-deploy"` host'ta
   çalıştır, public key'i instance oluşturma formuna yapıştır — parola ile SSH
   girişini KAPALI tut, sadece key-based)
7. **Ücretsiz statik public IPv4'ü reserve et**: Networking → IP Management →
   Reserved Public IPs → oluştur, sonra instance'ın VNIC'ine bağla. Bunu MUTLAKA
   yap — varsayılan gelen *ephemeral* IP instance durup kalkınca değişir,
   DuckDNS'in işaret edeceği IP reserved (statik) olan olmalı.

---

## 3. DNS — DuckDNS'i reserved IP'ye yönlendir (tek seferlik, cron gerekmez)

DuckDNS panelinde subdomain'in "current ip" alanına Oracle'ın reserved IP'sini
gir. IP statik olduğu için bu tek seferlik bir işlem — dinamik güncelleme
cron job'una gerek YOK (o sadece IP değişebilecekse gerekir, burada değişmeyecek).
Propagasyon genelde neredeyse anlık.

---

## 4. ⚠️ Oracle'a özgü güvenlik duvarı tuzağı (VCN Security List/NSG)

**Bu, Oracle'da ilk deploy'da en sık karşılaşılan tıkanma noktası — `ufw`
adımından ÖNCE oku, yoksa saatlerce yanlış yerde debug yaparsın.**

Oracle'ın **bulut-seviyesi** güvenlik duvarı (VCN Security List veya Network
Security Group) işletim sistemi seviyesindeki `ufw`'den **AYRI ve ONA EK**.
`ufw allow 80/443/22` YETERLİ DEĞİL — VCN Security List'te de aynı portlara
ingress kuralı olmazsa instance dışarıdan erişilemez kalır, `ufw` doğru olsa bile.

Adımlar: Networking → Virtual Cloud Networks → (VCN'in) → Security Lists →
Default Security List → Add Ingress Rules:
- Source CIDR `0.0.0.0/0`, TCP, Destination Port **22** (genelde varsayılan gelir, kontrol et)
- Source CIDR `0.0.0.0/0`, TCP, Destination Port **80**
- Source CIDR `0.0.0.0/0`, TCP, Destination Port **443**

Her iki katman (VCN Security List VE `ufw`) aynı anda izin vermeden hiçbir port
dışarıdan erişilebilir olmaz.

---

## 5. Sunucu hazırlığı (SSH ile)

```bash
ssh ubuntu@<ORACLE_RESERVED_IP>

sudo apt update && sudo apt upgrade -y

# Docker + Compose plugin — resmi script arm64/aarch64'ü native destekler
curl -fsSL https://get.docker.com | sh

# Firewall — SADECE gerekli portlar (VCN Security List adım 4'te AYRICA açılmalı)
sudo apt install -y ufw
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# Oracle'ın Ubuntu imajı 'ubuntu' kullanıcısını sudo + (Docker kurulduktan sonra)
# docker grubuna eklemeni gerektirebilir:
sudo usermod -aG docker ubuntu
# Değişikliğin etkili olması için SSH oturumunu kapatıp tekrar aç.
```

Not: Oracle'ın Ubuntu cloud image'ı bazı sürümlerde kendi `iptables` kurallarıyla
gelir — `ufw enable` etkisiz görünüyorsa `sudo iptables -L` ile kontrol et ve
çakışan bir kural varsa kaldır.

---

## 6. Repo'yu çek

```bash
git clone https://github.com/MaviMakumba/NexStream-News-Engine.git
cd NexStream-News-Engine
```

---

## 7. Production `.env` oluştur

`docker-compose.prod.yml`'in okuduğu TÜM env var'lar (bkz. `.env.example` —
zaten güncel). Kritik olanlar ve nereden geleceği:

| Değişken | Değer | Not |
|---|---|---|
| `ENVIRONMENT` | `production` | compose zaten set eder, .env'e eklemenize gerek yok |
| `DB_USER`/`DB_PASSWORD`/`DB_NAME` | kendi seçtiğiniz güçlü değerler | `openssl rand -hex 16` |
| `GROQ_API_KEY` | console.groq.com'dan alın | ücretsiz tier yeterli |
| `API_KEY` | `openssl rand -hex 32` | **`change-me-in-production` KALMAMALI** — guard bunu reddeder |
| `CORS_ORIGINS` | `https://nexstream.duckdns.org` | **asla `*`** — guard reddeder |
| `FRONTEND_URL` | `https://nexstream.duckdns.org` | şifre sıfırlama/e-posta doğrulama linkleri için |
| `SESSION_COOKIE_SECURE` | compose zaten `true` set ediyor | dokunmayın |
| `BILLING_DEV_MODE` | compose zaten `false` set ediyor | dokunmayın, PROD'DA AÇMAYIN |
| `GRAFANA_PASSWORD` | `openssl rand -hex 16` | `:?` zorunlu, boşsa deploy durur |
| `GRAFANA_USER` | örn. `admin` | |
| `ADMIN_EMAILS` | kendi e-postanız | ilk admin bootstrap, DB'ye dokunmadan |
| `RESEND_API_KEY` / `EMAIL_FROM` | resend.com'dan (ücretsiz tier yeterli) | **domain doğrulaması yapmadıysanız SADECE kendi e-postanıza mail gider** (bkz. BİLİNEN NOTLAR) |
| `STRIPE_*` | boş bırakılabilir | `/billing/*` 503 döner ama site çalışır; gerçek ödeme sonraki faz |
| `BACKUP_GPG_PASSPHRASE` | `openssl rand -hex 24` | yedekleri şifreler (v1.18, opt-in ama ÖNERİLİR) |
| `RCLONE_REMOTE` | boş bırakılabilir | offsite yedek istersen `infra/backup/rclone.conf.example`'a bakın |

```bash
cp .env.example .env
nano .env   # yukarıdaki tabloyu doldurun
```

**Sık yapılan hata:** `docker-compose.prod.yml` `env_file` yerine `${VAR}`
interpolasyonu kullanıyor — yani `.env` dosyası `docker compose` komutunu
çalıştırdığınız dizinde olmalı (repo kökü), başka yerde değil.

---

## 8. Self-signed sertifika (ilk açılış için — nginx boş sertifika ile başlamaz)

```bash
mkdir -p infra/nginx/ssl
openssl req -x509 -nodes -days 1 -newkey rsa:2048 \
  -keyout infra/nginx/ssl/privkey.pem \
  -out infra/nginx/ssl/fullchain.pem \
  -subj "/CN=nexstream.duckdns.org"
```

## 9. Offsite yedek (opsiyonel ama BACKUP_GPG_PASSPHRASE girdiyseniz devam edin)

```bash
cp infra/backup/rclone.conf.example infra/backup/rclone.conf
# RCLONE_REMOTE kullanacaksanız rclone.conf'u gerçek key'lerle doldurun
# (bkz. dosya içindeki B2/S3 örneği). Kullanmayacaksanız dosyayı boş bırakın,
# mount zararsızdır.
```

## 10. Stack'i ayağa kaldır

```bash
docker compose -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.prod.yml ps    # hepsi "healthy"/"running" olmalı, redpanda dahil
```

`ENVIRONMENT=production` iken `.env`'de zayıf bir değer varsa (`API_KEY`
varsayılan, `CORS_ORIGINS=*`, vb.) `app` container'ı **kasıtlı olarak**
açılmayı reddedip loglayacak — bu bir bug değil, v1.17 güvenlik guard'ı.

**⚠️ `app`/`worker` "unhealthy" kalıp `/health` hiç 200 dönmüyorsa (SentenceTransformer indirmesi takılmış olabilir):** 23 Temmuz 2026'da lokalde bulundu — `hf-xet` paketi (Hugging Face'in yeni "Xet" depolama backend'i) bazı ağlarda ilk model indirmesini birkaç KB'da tıkayıp kalıyor (`docker exec <container> sh -c "du -sh ~/.cache/huggingface/hub/models--*"` ile kontrol edilebilir — ilerlemesiz, deterministik takılma). `docker-compose.prod.yml`'de `app`+`worker`'a zaten `HF_HUB_DISABLE_XET=1` eklendi (klasik HTTPS indirmeye zorluyor), bu yüzden prod'da normalde sorun çıkmamalı — ama Oracle'ın ağı/ISP'si farklı davranırsa ve yine de takılırsa, bu env var'ın ikisinde de olduğunu doğrula, sonra `docker compose -f docker-compose.prod.yml restart app worker` ile tekrar dene.

## 11. Gerçek Let's Encrypt sertifikası

```bash
docker compose -f docker-compose.prod.yml exec certbot certbot certonly \
  --webroot -w /var/www/certbot -d nexstream.duckdns.org

docker compose -f docker-compose.prod.yml restart nginx
```

Not: sadece TEK `-d` — `www.nexstream.duckdns.org` YOK, DuckDNS bir alt-alan
adı için `www` desteği vermiyor. Let's Encrypt'in rate limitleri (haftada
domain başına 50 sertifika vb.) DuckDNS subdomain'lerinde satın alınmış bir
domain gibi aynen çalışır, özel bir ayar gerekmez.

Certbot container zaten 12 saatte bir otomatik `renew` deniyor (bkz.
`docker-compose.prod.yml` entrypoint) — manuel yenileme gerekmez.

## 12. Doğrulama

```bash
curl -I https://nexstream.duckdns.org                     # frontend
curl https://nexstream.duckdns.org/api/api/v1/news         # bkz. bilinen /api prefix garipliği
```

Tarayıcıdan: landing sayfası, `/dashboard`, kayıt ol → e-posta doğrulama
maili (Resend sandbox kısıtına dikkat), `/grafana/` (Grafana login), ve
mobilde "Ana ekrana ekle" ile PWA kurulumu (bkz. Faz C).

---

## `infra/nginx/nginx.conf` — değişiklik GEREKMİYOR

Doğrulandı: `server_name _;` (catch-all) hem HTTP-redirect hem HTTPS blokunda,
hiçbir yerde domain string'i hardcode edilmemiş — `*.duckdns.org` için sıfır
düzenleme ile çalışır. `settings.py`'nin `_reject_unsafe_production_config`
guard'ı da sadece `cors_origins == "*"` mi diye bakıyor, spesifik değeri değil.

---

## Deploy sonrası (ilk hafta içinde)

- [ ] Migration'ları kontrol et — dev'de `create_all` otomatik ama prod'da
      bazı `migrations/*.sql` dosyaları manuel çalıştırılmalı olabilir
      (mevcut CLAUDE.md notlarına bakın: v1.8/v1.9/v1.11/v1.13/v1.15 migration'ları)
- [ ] `docker exec nexstream_backup /usr/local/bin/backup.sh` ile ilk yedeği
      manuel tetikleyip `backup_data` volume'unda + (varsa) offsite'ta
      dosyanın gerçekten oluştuğunu doğrulayın
- [ ] UptimeRobot (ücretsiz) ile `/health`'i izlemeye alın
- [ ] Resend'de domain doğrulaması yapın (yapmazsanız hesap sahibi dışında
      kimse mail almaz — bkz. BİLİNEN NOTLAR)
- [ ] Oracle'da instance'ı stop/start etmemeye özen gösterin (reserved IP
      kalıcı ama instance kapanıp açılınca yine de kısa bir kesinti olur;
      Always Free kaynaklar "idle" nedeniyle otomatik geri alınmaz ama
      hesabınızın "Always Free" limitlerini aşmadığından emin olun)
- [ ] Gerçek Stripe hesabı + `STRIPE_*` + `BILLING_DEV_MODE=false` (zaten
      false) — kod tarafı hazır, sadece hesap/anahtar eksik (ödeme almaya
      karar verirsen)

## Kapsam dışı bırakılanlar (bilinçli, roadmap'te not edilmiş)

`/docs` prod'da açık kalıyor (ürün kararı), public `/news/search` kota
atlatma (landing demosu için bilinçli), token'lar DB'de düz metin, mobil
tarafta App Store/Play Store yok (sadece PWA — bkz. Faz C, ikisi de gerçekten
ücretsiz değil: iOS'ta yıllık $99 Apple Developer zorunlu, Android'de Play
Store tek seferlik $25).
