"""SCRAPER_REGISTRY — kaynak adı → scraper sınıfı eşlemesi (tek doğruluk noktası).

Yeni kaynak eklemek: rss_scrapers.py'de sınıf + buraya kayıt + settings.scrape_sources.
Worker ve /news/sources endpoint'i bu sözlüğü kullanır.
"""

from src.adapters.scrapers.rss_scrapers import (
    TRTHaberScraper, BBCTurkishScraper,
    HurriyetScraper, HurriyetSporScraper,
    SabahScraper, CNNTurkScraper, SozcuScraper,
    HaberturkScraper, HaberturkSporScraper,
    BBCTechnologyScraper, BBCSportScraper,
    GuardianTechScraper, TechCrunchScraper, HackerNewsScraper, TheVergeScraper,
    AnadoluAjansiScraper, AnadoluEkonomiScraper,
)

# Kayıtlı tüm scraper'ların tek kayıt noktası.
# Yeni kaynak eklemek için buraya bir satır yeterlı.
SCRAPER_REGISTRY: dict = {
    # Türkçe
    "TRT Haber":       TRTHaberScraper(),
    "BBC Türkçe":      BBCTurkishScraper(),
    "Hürriyet":        HurriyetScraper(),
    "Hürriyet Spor":   HurriyetSporScraper(),
    "Sabah":           SabahScraper(),
    "CNN Türk":        CNNTurkScraper(),
    "Sözcü":           SozcuScraper(),
    "Habertürk":       HaberturkScraper(),
    "HT Spor":         HaberturkSporScraper(),
    "Anadolu Ajansı":  AnadoluAjansiScraper(),
    "AA Ekonomi":      AnadoluEkonomiScraper(),
    # İngilizce
    "BBC Technology":  BBCTechnologyScraper(),
    "BBC Sport":       BBCSportScraper(),
    "Guardian Tech":   GuardianTechScraper(),
    "TechCrunch":      TechCrunchScraper(),
    "Hacker News":     HackerNewsScraper(),
    "The Verge":       TheVergeScraper(),
}
