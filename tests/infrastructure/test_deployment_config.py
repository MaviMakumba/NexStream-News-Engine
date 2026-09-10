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
