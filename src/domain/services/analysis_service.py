from textblob import TextBlob

class AnalysisService:
    def analyze_text(self, text: str) -> dict:
        """
        Metni analiz eder, duygu durumunu ve özetini çıkarır.
        """
        if not text:
            return {"sentiment_score": 0.0, "sentiment_label": "Neutral", "summary": "No Content"}

        blob = TextBlob(text)
        
        # 1. Duygu Analizi (-1.0 ile 1.0 arası)
        polarity = blob.sentiment.polarity
        
        # Etiketleme
        if polarity > 0.1:
            label = "Positive 😃"
        elif polarity < -0.1:
            label = "Negative 😡"
        else:
            label = "Neutral 😐"

        # 2. Özetleme (Basitçe ilk 2 cümleyi alıyoruz - Demo için)
        # Gerçek bir özetleme için 'sumy' veya 'Gemini API' kullanılabilir.
        summary = " ".join([str(sentence) for sentence in blob.sentences[:2]])

        return {
            "sentiment_score": polarity,
            "sentiment_label": label,
            "summary": summary
        }