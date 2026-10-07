#!/bin/bash
# Prod deploy: CI'da build edilip GHCR'a push edilmiş imajları ÇEKER, yalnız içeriği
# değişen servisleri yeniden yaratır. EC2'DE BUILD YOK (7 Eki 2026: EC2'de
# `up --build` t3.small'ı ~30 dk kilitlemişti — bkz. docs/CHANGELOG.md).
#
# Kullanım (repo kökünde):
#   IMAGE_TAG=<commit-sha> [GHCR_TOKEN=...] bash infra/scripts/deploy_images.sh
# Geri alma: IMAGE_TAG=<eski-sha> ile aynı komut (CI son 3 sha etiketini host'ta tutar).
#
# Neden `IMAGE_TAG` sha ama imajlar yeniden yaratılmıyor: CI derlemeleri deterministik
# (SOURCE_DATE_EPOCH + rewrite-timestamp), içeriği değişmeyen servis AYNI digest'e sahip
# olur; compose imaj ID'sini karşılaştırır, etiketi değil → yalnız gerçekten değişenler
# recreate edilir (özellikle RAM-ağır embedder boşuna yeniden başlamaz).
set -uo pipefail

: "${IMAGE_TAG:?IMAGE_TAG gerekli (commit sha, ya da geri alma icin eski sha)}"
export IMAGE_TAG
COMPOSE="docker compose -f docker-compose.prod.yml"
SERVICES="app worker embedder scheduler frontend backup"
REGISTRY_PREFIX="ghcr.io/mavimakumba/nexstream-"
KEEP_TAGS=3
DEPLOY_LOG=".deployed_image_tags"   # .gitignore'da; git reset --hard silmez

if [ -n "${GHCR_TOKEN:-}" ]; then
  echo "$GHCR_TOKEN" | docker login ghcr.io -u "${GHCR_USER:-github-actions}" --password-stdin >/dev/null \
    || { echo "GHCR login basarisiz"; exit 1; }
fi
trap 'docker logout ghcr.io >/dev/null 2>&1 || true' EXIT

# 1) ÖNCE çek: indirme başarısızsa çalışan yığına HİÇ dokunulmaz.
if ! $COMPOSE pull $SERVICES; then
  echo "imaj cekme basarisiz — calisan servisler degistirilmedi"
  exit 1
fi

# 2) Yalnız imajı değişenleri recreate et (build YOK).
$COMPOSE up -d --no-build || exit 1

# nginx upstream'leri yalnız açılışta DNS çözer (bkz. CLAUDE.md nginx notu): recreate
# edilen servislerin yeni IP'sini görmesi için her deploy'da tazele.
$COMPOSE restart nginx

bash infra/scripts/wait_for_health.sh
HEALTH_EXIT=$?

# 3) Disk: başarılı deploy'ların etiketini kaydet, son KEEP_TAGS'ı tut, gerisini sil.
# Sıralama imaj `Created` zamanına DAYANMAZ (deterministik build'de hepsi sabit);
# kullanımdaki imajı docker zaten silmez. Başarısız deploy kaydedilmez (geri alma
# hedefi hep sağlıklı bir sürüm olsun). Temizlik hatası deploy sonucunu etkilemez.
if [ "$HEALTH_EXIT" -eq 0 ]; then
  echo "$IMAGE_TAG" >> "$DEPLOY_LOG"
  KEEP=$(tac "$DEPLOY_LOG" | awk '!seen[$0]++' | head -n "$KEEP_TAGS")
  docker image ls --format '{{.Repository}} {{.Tag}}' | grep "^${REGISTRY_PREFIX}"     | while read -r repo tag; do
        case "$tag" in main|"<none>") continue ;; esac
        echo "$KEEP" | grep -qx "$tag" || docker rmi "$repo:$tag" >/dev/null 2>&1 || true
      done
  docker image prune -f >/dev/null 2>&1 || true
fi

exit $HEALTH_EXIT
