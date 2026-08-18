# NexStream — İlk Prod Deploy Kılavuzu ($0/ay — v2.0)

> **✅ 29 Temmuz 2026: BU KILAVUZ BAŞTAN SONA UYGULANDI, SİTE CANLI.**
> **https://nexstreamnewsengine.duckdns.org** — gerçek Let's Encrypt sertifikası
> (27 Ekim 2026'ya kadar, otomatik yenileniyor), 16 servis ayakta, boru hattı
> uçtan uca çalışıyor. Aşağıdaki adımlar bundan sonraki kurulumlar (Oracle'a
> taşıma, sıfırdan yeniden kurulum) için geçerliliğini koruyor ve canlı
> deploy'da öğrenilenlerle güncellendi.
>
> **⚠️ Fiili deploy AWS'te, Oracle'da DEĞİL.**
> Oracle'ın A1.Flex kapasitesi günlerce "Out of host capacity" verdi (bkz. §2) ve
> beklemek yerine **AWS Free Plan ($100 kredi, 28 Ocak 2027'ye kadar) köprü olarak**
> seçildi. Aşağıdaki §1, §3, §6-§12 adımları **aynen geçerli**; yalnızca sunucunun
> nereden geldiği değişiyor — bunun için §2 yerine **§2-AWS**'yi izle.
> AWS'te kredi bitince kart çekilmez, hesap kapanır (doğrulandı).

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

## 2-AWS. AWS EC2 köprü sunucusu (Oracle kapasitesi yoksa bunu kullan)

28 Temmuz 2026'da fiilen kurulan yol. Kurulmuş kaynak: instance
`i-0608c897a3d8ca3f3`, Elastic IP `63.178.59.10`, domain
`nexstreamnewsengine.duckdns.org`, bölge `eu-central-1a`.

Sıfırdan kuracaksan dört tuzağı önceden bil:

1. **ARM (`t4g.*`) seçme.** `t4g.micro`/`t4g.small` için `eu-central-1`'de
   `InsufficientInstanceCapacity` alındı — birden çok denemede. x86 **`t3.small`**
   (2 vCPU / 2GB) sorunsuz açıldı. Bu, ARM'ın Oracle'daki kapasite sorununun
   AWS'teki karşılığı; ısrar etmeye değmiyor.
2. **SSH (port 22) çalışmayabilir.** Hem geliştirme ortamından hem kullanıcının
   kendi bağlantısından ISP seviyesinde kapalıydı. Çözüm:
   **AWS Console → EC2 → Instances → Connect → EC2 Instance Connect**
   (tarayıcı terminali, 443 üzerinden çalışır). Vakit kaybetmeden buna geç.
3. **EBS'i 30GB'ta bırakma — 80GB yap.** `app` ve `worker` AYNI Dockerfile'ı
   kullanıyor ve BuildKit ikisini paralel export ediyor; 30GB'ta build
   `exporting to image` aşamasında BOŞ bir hatayla patlıyordu. İmzası:
   `journald: No space left on device`. (v2.0 optimizasyonundan sonra backend
   image'ları 1.55GB → 516MB'a indi, yani baskı çok azaldı — ama monitoring
   yığını + model cache hâlâ yer istiyor.)
4. **Elastic IP ayır.** Aksi halde instance her stop/start'ta public IP değişir
   ve DuckDNS kaydın bozulur.

**Maliyeti durdurma:** çalışmadığı sürede instance'ı durdur (compute faturası
durur; EBS + Elastic IP devam eder, ~$10/ay).

```bash
aws ec2 describe-instances --instance-ids i-0608c897a3d8ca3f3 --region eu-central-1 \
  --query "Reservations[0].Instances[0].State.Name" --output text
aws ec2 start-instances --instance-ids i-0608c897a3d8ca3f3 --region eu-central-1
aws ec2 stop-instances  --instance-ids i-0608c897a3d8ca3f3 --region eu-central-1
```

AWS'te §4'teki Oracle VCN Security List'in karşılığı **Security Group**'tur:
80 ve 443 inbound açık olmalı. Yine `ufw`'den AYRI ve ONA EK — ikisi de
açılmadan port dışarıdan erişilemez.

### SSH çalışmıyorsa: SSM Session Manager (kurulu ve çalışıyor)

Port 22 bu kurulumda hem geliştirme ortamından hem kullanıcının ISP'sinden
kapalı. Kalıcı çözüm 29 Tem 2026'da kuruldu: **AWS Systems Manager**, 443
üzerinden çalışır, SSH gerektirmez, tarayıcı terminaline de gerek bırakmaz.

Kurulu olanlar (tekrar kurmaya gerek yok): IAM rolü `NexStreamSSMRole`
(`AmazonSSMManagedInstanceCore` politikası) + instance profile
`NexStreamSSMProfile`, instance'a bağlı.

```bash
# Kayıtlı mı?
aws ssm describe-instance-information --region eu-central-1 \
  --query "InstanceInformationList[*].{Id:InstanceId,Ping:PingStatus}"

# Komut çalıştır
aws ssm send-command --instance-ids i-0608c897a3d8ca3f3 --region eu-central-1 \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["export HOME=/root","cd /home/ubuntu/NexStream-News-Engine","docker compose -f docker-compose.prod.yml ps"]' \
  --query "Command.CommandId" --output text

# Çıktıyı al
aws ssm get-command-invocation --command-id <ID> \
  --instance-id i-0608c897a3d8ca3f3 --region eu-central-1 \
  --query "StandardOutputContent" --output text
```

**İki tuzak:**
1. Instance profile ÇALIŞAN bir instance'a eklendiğinde SSM agent kimlik
   bilgisini almaz ve kaydolmaz. `aws ec2 reboot-instances` sonrası 30 saniyede
   Online oldu. Sıfırdan kurarken profili instance'ı başlatmadan önce ekle.
2. SSM komutları **root olarak ve `$HOME` SET EDİLMEDEN** koşar — git komutları
   `fatal: $HOME not set` verir. Her komut bloğunun başına `export HOME=/root`
   koy. Ayrıca repo `ubuntu` kullanıcısının olduğu için bir kez
   `git config --global --add safe.directory /home/ubuntu/NexStream-News-Engine`
   gerekir (yapıldı).

Alternatif (AWS hesabına dokunmak istemezsen): **EC2 Console → Instances →
Connect → EC2 Instance Connect** tarayıcı terminali.

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

### 5-B. Swap dosyası — `t3.small` (2GB) için ZORUNLU

Optimizasyon sonrası yığın 2GB'a sığıyor ama tamponu dar. Swap, tepe anlarında
(image build, ilk model indirmesi, eşzamanlı scrape) OOM killer'ın rastgele bir
container'ı öldürmesi yerine sistemin yavaşlayarak devam etmesini sağlar. Bu bir
performans ayarı değil, **çökme sigortası**:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab   # reboot'ta kalıcı

# Swap'a erken kaçmasın — sadece gerçekten sıkışınca kullansın
sudo sysctl vm.swappiness=10
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf

free -h    # Swap satırı 2.0Gi görünmeli
```

Oracle A1.Flex'e (24GB RAM) geçilirse bu adım gereksizdir.

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

### `embedder` servisi — model image'a GÖMÜLÜ, indirme YOK

v2.0'dan itibaren SentenceTransformer modeli `app`/`worker` içinde DEĞİL, ayrı
bir **`embedder`** servisinde tek kopya duruyor (RAM'de ~600MB tasarruf). `app` ve
`worker` ona `depends_on: service_healthy` ile bağlı, yani **embedder healthy
olana kadar ikisi de hiç başlamaz.**

**Model `Dockerfile.embedder` içinde BUILD ANINDA image'a gömülüyor** — runtime'da
hiçbir indirme olmaz. Bu bir hız optimizasyonu değil, ZORUNLULUK: embedder yalnızca
`backend` ağında ve o ağ `internal: true`, yani interneti YOK (bkz. aşağıdaki
"egress" notu). Modeli çalışma anında indirmesi imkânsız.

Pratik sonuçları:
- Embedder ~30-60 saniyede healthy olur (sadece diskten yükleme). `start_period: 180s`.
- `HF_HUB_OFFLINE=1` set — eksik bir dosya olursa sessizce internete uzanıp asılmak
  yerine hemen ve net hata verir.
- Model cache volume'ü YOK, gerek kalmadı. Embedder image'ı bu yüzden ~2.9GB.
- Daha önce not düşülen `hf-xet` tıkanma riski tamamen ortadan kalktı (indirme
  artık build makinesinde, bir kez oluyor).

```bash
docker logs nexstream_embedder --tail 20     # "Application startup complete" bekle
```

### ⚠️ `internal: true` ağ tuzağı — SESSİZ işlevsizlik

`backend` ağı `internal: true` (v1.6 ağ izolasyonu). O ağdaki bir container
**dışarıya hiç çıkamaz, DNS bile çözemez**. 29 Tem 2026'da bunun bedeli ödendi:
`worker` yalnızca `backend`'deydi, yani 17 RSS kaynağına da Groq API'sine de hiç
ulaşamıyordu.

Sinsi tarafı şu: yığın **tamamen sağlıklı görünüyordu** — tüm container'lar
healthy, `/health` yeşil, nginx/TLS çalışıyor, arayüz açılıyor. Ama veritabanı
sonsuza kadar boş kalıyordu, çünkü scraper exception'ı yutup `[]` dönüyor
(bilinçli tasarım) ve hiçbir yerde alarm çalmıyor.

Çözüm compose'da: dışarıya çıkması gereken servisler (`worker`, `backup`) ayrıca
**`egress`** ağına da bağlı. `app` zaten `frontend` ağında (internal değil).

**Bu yüzden deploy'u `/health` yeşil mi diye değil, İŞ ÇIKTISIYLA doğrula:**

```bash
docker exec nexstream_worker python -c "import socket; print(socket.gethostbyname('api.groq.com'))"
docker compose -f docker-compose.prod.yml exec -T db \
  psql -U "$DB_USER" -d "$DB_NAME" -tAc "select count(*) from news_articles"
```

İkincisi birkaç dakika sonra hâlâ `0` ise scrape akışı çalışmıyor demektir.

## 11. Gerçek Let's Encrypt sertifikası

**Adım 11a — sertifikayı al.** `exec` DEĞİL `run --rm` kullan: certbot
container'ının entrypoint'i sonsuz bir `renew` döngüsü, `exec` ile araya
girmek yerine tek seferlik bir container çalıştırmak daha temiz.

```bash
docker compose -f docker-compose.prod.yml run --rm --entrypoint certbot certbot certonly \
  --webroot -w /var/www/certbot \
  -d nexstreamnewsengine.duckdns.org \
  --email SENIN@EPOSTAN --agree-tos --no-eff-email --non-interactive
```

Not: sadece TEK `-d` — `www.` YOK, DuckDNS bir alt-alan adı için `www` desteği
vermiyor. Let's Encrypt'in rate limitleri DuckDNS subdomain'lerinde satın alınmış
bir domain gibi aynen çalışır.

**Adım 11b — sertifikayı nginx'in baktığı yere bağla (ATLAMA).**
nginx `/etc/nginx/ssl/fullchain.pem` ve `privkey.pem` dosyalarını **kökte**
arıyor; certbot ise `live/<domain>/` altına yazıyor. Bu adım yapılmazsa
**hiçbir hata görmezsin** — nginx sessizce eski self-signed sertifikayı sunmaya
devam eder ve tarayıcı "güvenli değil" demeye devam eder.

Domain'i `nginx.conf`'a hardcode ETMEMEK için symlink kullanılıyor (certbot
yenileme yaptığında `live/` altındaki hedefler güncellenir, bu linkler geçerli
kalır):

```bash
cd infra/nginx/ssl
mv fullchain.pem self-signed-fullchain.pem.bak
mv privkey.pem   self-signed-privkey.pem.bak
ln -sfn live/nexstreamnewsengine.duckdns.org/fullchain.pem fullchain.pem
ln -sfn live/nexstreamnewsengine.duckdns.org/privkey.pem  privkey.pem
cd ../../..

docker compose -f docker-compose.prod.yml exec nginx nginx -t   # "test is successful"
docker compose -f docker-compose.prod.yml restart nginx
```

Doğrula — `-k` OLMADAN çalışmalı (yani sertifika gerçekten güvenilir):

```bash
curl -s https://nexstreamnewsengine.duckdns.org/api/health
echo | openssl s_client -connect nexstreamnewsengine.duckdns.org:443 \
  -servername nexstreamnewsengine.duckdns.org 2>/dev/null \
  | openssl x509 -noout -issuer -dates
```

Certbot container zaten 12 saatte bir otomatik `renew` deniyor (bkz.
`docker-compose.prod.yml` entrypoint) — manuel yenileme gerekmez.

## 12. Doğrulama

```bash
curl -I https://nexstream.duckdns.org                     # frontend
curl https://nexstream.duckdns.org/api/health              # embedder DAHİL tüm bağımlılıklar
curl https://nexstream.duckdns.org/api/api/v1/news         # bkz. bilinen /api prefix garipliği
```

`/api/health` şunu döndürmeli — **`embedder` alanı da `ok` olmalı**, aksi halde
arama sonuçları sessizce keyword aramasına düşer (uygulama çalışmaya devam eder,
ama semantik arama devre dışıdır):

```json
{"status":"ok","db":"ok","kafka":"ok","chromadb":"ok","embedder":"ok","indexed_articles":5190}
```

Bellek durumunu da bir kez kontrol et (t3.small'da tampon dar):

```bash
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}"
free -h    # swap kullanımı sürekli artıyorsa yığın sığmıyor demektir
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
