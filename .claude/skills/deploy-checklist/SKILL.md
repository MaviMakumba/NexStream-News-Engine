---
name: deploy-checklist
description: NexStream production deployment adımları — ilk VPS kurulumu, gözlemlenebilirlik (Grafana/Prometheus/Loki) erişimi, backup tetikleme. Sadece gerçekten deploy/backup/monitoring erişimi gerektiğinde kullan.
---

# Production Deployment Notları (v1.6+)

## İlk deployment adımları
1. VPS'e (DigitalOcean/Hetzner/Oracle Free) Docker + Docker Compose kurulur
2. `.env` dosyası production değerlerle oluşturulur (`API_KEY`, `GRAFANA_PASSWORD` güçlü değerler)
3. SSL sertifikası: `infra/nginx/ssl/` dizinine self-signed cert koy, sonra certbot ile değiştir
4. `docker-compose -f docker-compose.prod.yml up -d`
5. Certbot ilk çalıştırma: `docker-compose -f docker-compose.prod.yml exec certbot certbot certonly --webroot -w /var/www/certbot -d your-domain.com`

## Gözlemlenebilirlik
- Grafana: `https://your-domain/grafana/` (admin/nexstream varsayılan)
- Pre-provisioned datasources: Prometheus + Loki
- NexStream dashboard: request latency, articles/min, Groq latency/rate limits, search latency
- Worker logları: Grafana → Explore → Loki → `{service="worker"}`

## Backup
- Günlük 03:00 UTC: PostgreSQL pg_dump + ChromaDB tar
- `/backups` volume'unda 7 gün retention
- Manuel tetikleme: `docker exec nexstream_backup /usr/local/bin/backup.sh`

Not: Güncel deploy akışı (main'e merge → otomatik SSM redeploy) için CLAUDE.md'deki
"MEVCUT DURUM" bölümündeki "Branch" notuna bak — bu dosya sadece ilk kurulum/
gözlemlenebilirlik/backup referansı, güncel CI/CD akışını tekrar etmiyor.
