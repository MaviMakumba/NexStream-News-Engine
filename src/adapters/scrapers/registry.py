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
    DunyaScraper, CoinDeskScraper, CointelegraphScraper, ScienceDailyScraper,
    AABilimTeknolojiScraper, AAKulturScraper, AlJazeeraScraper, DWScraper,
    BBCHealthScraper, BBCEntertainmentScraper, BBCScienceEnvironmentScraper,
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
    "Dünya": DunyaScraper(),
    "AA Bilim-Teknoloji": AABilimTeknolojiScraper(),
    "AA Kültür": AAKulturScraper(),
    # İngilizce
    "BBC Technology":  BBCTechnologyScraper(),
    "BBC Sport":       BBCSportScraper(),
    "Guardian Tech":   GuardianTechScraper(),
    "TechCrunch":      TechCrunchScraper(),
    "Hacker News":     HackerNewsScraper(),
    "The Verge":       TheVergeScraper(),
    "CoinDesk": CoinDeskScraper(),
    "Cointelegraph": CointelegraphScraper(),
    "ScienceDaily": ScienceDailyScraper(),
    "Al Jazeera": AlJazeeraScraper(),
    "DW": DWScraper(),
    "BBC Health": BBCHealthScraper(),
    "BBC Entertainment": BBCEntertainmentScraper(),
    "BBC Science & Environment": BBCScienceEnvironmentScraper(),
}
