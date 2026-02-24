from abc import ABC, abstractmethod
from typing import List, Dict

class NewsScraperPort(ABC):
    """
    Bu sınıf bir 'Sözleşme'dir (Interface).
    Sisteme eklenecek her haber robotu bu sınıfı miras almak ZORUNDADIR.
    Böylece sistemimiz 'BBC mi? Twitter mı?' diye sormaz, sadece 'Haber Getir' der.
    """
    
    @abstractmethod
    def fetch_news(self) -> List[Dict]:
        """
        Geriye mutlaka şu formatta bir liste dönmelidir:
        [
            {
                'title': 'Haber Başlığı',
                'content': 'Haberin kısa özeti...',
                'source': 'Kaynak Adı',
                'url': 'Haberin Linki'
            },
            ...
        ]
        """
        pass