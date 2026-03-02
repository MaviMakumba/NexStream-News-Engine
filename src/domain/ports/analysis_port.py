from abc import ABC, abstractmethod

class AnalysisPort(ABC):
    """Yapay Zeka analizi için sözleşme. Yarın TextBlob gider, Gemini gelir, kod değişmez."""
    
    @abstractmethod
    def analyze_text(self, text: str) -> dict:
        """
        Dönüş formatı garanti edilmelidir:
        {'sentiment_score': float, 'sentiment_label': str, 'summary': str}
        """
        pass