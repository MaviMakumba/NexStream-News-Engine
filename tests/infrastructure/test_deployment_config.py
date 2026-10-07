"""Docker Compose deployment config regression testleri.

10 Eylül 2026'da keşfedildi: `docker-compose.prod.yml`'deki scheduler
servisinin `SCRAPE_SOURCES` env var'ı hardcoded ve 6 kaynak eksikti
(Anadolu Ajansı, AA Ekonomi, Guardian Tech, TechCrunch, Hacker News,
The Verge) — bu kaynaklar prod'da scheduler tarafından HİÇ tetiklenmiyordu.
Bu test, prod compose'daki kaynak listesinin `settings.py`'deki kanonik
17-kaynak varsayılanıyla (dev compose'un da kullandığı) senkron kalmasını
garanti eder — gelecekte yeni bir kaynak eklenip sadece dev'e/settings.py'a
yazılıp prod compose'un unutulması durumunu yakalar.
"""

import re
import yaml
from src.infrastructure.config.settings import Settings

import pytest as _pytest_drift

pytestmark = _pytest_drift.mark.drift


def _scrape_sources_from_compose(path: str) -> set[str]:
    with open(path, "r", encoding="utf-8") as f:
        compose = yaml.safe_load(f)
    env_list = compose["services"]["scheduler"]["environment"]
    for entry in env_list:
        match = re.match(r"^\s*SCRAPE_SOURCES=(.*)$", entry)
        if match:
            return {s.strip() for s in match.group(1).split(",") if s.strip()}
    raise AssertionError(f"{path}: scheduler servisinde SCRAPE_SOURCES bulunamadı")


def _canonical_sources() -> set[str]:
    default = Settings.model_fields["scrape_sources"].default
    return {s.strip() for s in default.split(",") if s.strip()}


def test_prod_compose_scrape_sources_matches_settings_default():
    assert _scrape_sources_from_compose("docker-compose.prod.yml") == _canonical_sources()


def test_dev_compose_scrape_sources_matches_settings_default():
    assert _scrape_sources_from_compose("docker-compose.yml") == _canonical_sources()


# ── Sahip e-postası repo'da düz metin olmamalı (12 Eylül 2026 güvenlik turu) ──
# "Güvenlik araştırmacısı" kullanıcının kişisel Gmail adresine mail attı; adres
# public repo'daki 267 commit'in author alanında VE bu dosyalarda düz metin
# duruyordu. Grafana contact point'i artık env'den (GRAFANA_ALERT_EMAIL) okur.

_OWNER_EMAIL_FRAGMENT = "erenk897"


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def test_grafana_contact_point_reads_email_from_env_not_literal():
    conf = _read("infra/grafana/provisioning/alerting/contactpoints.yml")
    assert _OWNER_EMAIL_FRAGMENT not in conf
    assert "${GRAFANA_ALERT_EMAIL}" in conf


def test_prod_compose_passes_grafana_alert_email():
    with open("docker-compose.prod.yml", "r", encoding="utf-8") as f:
        compose = yaml.safe_load(f)
    env = compose["services"]["grafana"]["environment"]
    assert any(str(e).startswith("GRAFANA_ALERT_EMAIL=") for e in env)


def test_owner_email_not_in_tracked_docs():
    for path in (
        "docs/superpowers/plans/2026-07-31-owner-rolu-ve-gercek-email-gonderimi.md",
        "docs/superpowers/specs/2026-07-29-owner-rolu-ve-gercek-email-gonderimi-design.md",
    ):
        assert _OWNER_EMAIL_FRAGMENT not in _read(path), path


# ── Grafana kök URL'i gerçek domain'den gelmeli (13 Eylül 2026) ──────────────
# `%(domain)s` yer tutucusu GF_SERVER_DOMAIN set edilmediği için "localhost"a
# çözülüyordu: https://nexstreamnews.com/grafana/ → 301 http://localhost/grafana/
# (kullanıcı "boş ekran" gördü). FRONTEND_URL zaten .env'de gerçek domain.

def test_prod_grafana_root_url_uses_frontend_url_not_domain_placeholder():
    with open("docker-compose.prod.yml", "r", encoding="utf-8") as f:
        compose = yaml.safe_load(f)
    env = [str(e) for e in compose["services"]["grafana"]["environment"]]
    root = next(e for e in env if e.startswith("GF_SERVER_ROOT_URL="))
    assert "%(domain)s" not in root
    assert "${FRONTEND_URL" in root and root.endswith("/grafana/")


# ── 28 Eylül 2026 prod taraması ────────────────────────────────────────────────


def _compose(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _volume_targets(service: dict) -> dict[str, str]:
    """'named:/target[:ro]' kısa sözdizimini {target: source} sözlüğüne çevirir."""
    out = {}
    for entry in service.get("volumes", []):
        parts = entry.split(":")
        out[parts[1]] = parts[0]
    return out


def test_chromadb_named_volume_mounted_at_chroma_1x_data_dir():
    """chromadb/chroma 1.x imajı veriyi /data'ya yazar (eski 0.x: /chroma/chroma).
    Prod compose named volume'u eski yola bağlıyordu — 27k vektör anonim bir
    volume'da duruyordu (`compose down` ile kaybolurdu) ve yedek boş tar'dı."""
    for path in ("docker-compose.prod.yml", "docker-compose.yml"):
        targets = _volume_targets(_compose(path)["services"]["chromadb"])
        assert targets.get("/data") == "chroma_data", path
        assert "/chroma/chroma" not in targets, path


def test_backup_crontab_baked_into_image_not_bind_mounted():
    """busybox crond root'a ait OLMAYAN crontab dosyalarını sessizce yok sayar.
    Host'tan bind-mount edilen dosya uid 1000'e aitti — 28 Tem'den beri tek bir
    zamanlanmış yedek alınmadı. Crontab imaja (root sahipliğiyle) kopyalanmalı."""
    backup = _compose("docker-compose.prod.yml")["services"]["backup"]
    assert not any("crontab" in v for v in backup.get("volumes", []))
    dockerfile = _read("infra/backup/Dockerfile")
    assert re.search(r"^COPY\s+crontab\s+/etc/crontabs/root", dockerfile, re.M)


def test_backup_cron_output_goes_to_container_logs():
    """Yedek çıktısı container içi bir dosyaya gidince `docker logs`'ta hiçbir iz
    kalmıyordu — hiç çalışmadığı 2 ay boyunca fark edilmedi."""
    crontab = _read("infra/backup/crontab")
    assert "/proc/1/fd/1" in crontab


def test_redpanda_runs_with_init_to_reap_healthcheck_zombies():
    """redpanda PID 1 olarak healthcheck'in (rpk | grep) çocuklarını reap etmiyordu."""
    for path in ("docker-compose.prod.yml", "docker-compose.yml"):
        assert _compose(path)["services"]["redpanda"].get("init") is True, path
