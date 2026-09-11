#!/bin/bash
# Deploy sonrasi localhost uzerinden (Cloudflare BYPASS ederek) health-check.
#
# 10 Eylul 2026'da CI'daki "Health check" adimi ayni deploy icin defalarca
# yanlis-pozitif basarisiz raporladi. Ilk teshis (PR #117, ayni gun) "3dk'lik
# pencere cok kisa" oldugunu varsayip 30 denemeye (7.5dk) cikardi — ama bu da
# 403'u COZMEDI, cunku gercek sebep sure degildi: GitHub Actions runner'inin
# (Azure datacenter) IP'si nexstreamnews.com'un onundeki Cloudflare tarafindan
# Managed Challenge ile karsilaniyordu (`cf-mitigated: challenge` header'i,
# User-Agent'tan tamamen bagimsiz, saf IP-reputation bazli — hem curl'un
# varsayilan UA'siyla hem gercekci bir Chrome UA'siyla ayni sonuc, canli
# GitHub Actions probe'uyla dogrulandi). curl JS calistiramadigi icin
# challenge'i hic gecemiyor, deploy GERCEKTE basarili olsa bile CI hep 403
# aliyordu.
#
# Bu script CI'in disaridan (nexstreamnews.com uzerinden, Cloudflare'in
# arkasindan) sormasi yerine, zaten ayni SSM oturumunda calisan bu sunucunun
# KENDI icinden nginx'e localhost uzerinden sorar — istek hic internete
# cikmadigi icin Cloudflare'e hic ugramaz. `-k` sart: sertifikanin CN/SAN'i
# "localhost" degil "nexstreamnews.com" (gercek Let's Encrypt sertifikasi),
# burada amac TLS kimlik dogrulamasi degil sadece "app ayakta mi" sorusu.
set -uo pipefail

HEALTHY=0
for i in $(seq 1 30); do
  if curl -fsSk https://localhost/api/health >/dev/null 2>&1; then
    echo "Healthy (localhost, deneme $i)"
    HEALTHY=1
    break
  fi
  echo "Health retry $i..."
  sleep 15
done

if [ "$HEALTHY" != "1" ]; then
  echo "Health check localhost uzerinden basarisiz oldu (30 deneme, ~7.5dk)"
  exit 1
fi
