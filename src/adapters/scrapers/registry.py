from src.adapters.scrapers.rss_scrapers import (
    TRTHaberScraper, BBCTurkishScraper,
    HurriyetScraper, HurriyetSporScraper,
    SabahScraper, CNNTurkScraper, SozcuScraper,
    HaberturkScraper, HaberturkSporScraper,
    BBCTechnologyScraper, BBCSportScraper,
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
    # İngilizce
    "BBC Technology":  BBCTechnologyScraper(),
    "BBC Sport":       BBCSportScraper(),
}
