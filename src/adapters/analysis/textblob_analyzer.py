from textblob import TextBlob
from src.domain.ports.analysis_port import AnalysisPort

class TextBlobAnalyzer(AnalysisPort):

    def analyze_text(self, text: str) -> dict:
        if not text:
            return {
                "sentiment_score": 0.0,
                "sentiment_label": "Neutral",
                "summary": "No Content"
            }

        blob = TextBlob(text)
        polarity = blob.sentiment.polarity

        if polarity > 0.1:
            label = "Positive"
        elif polarity < -0.1:
            label = "Negative"
        else:
            label = "Neutral"

        summary = " ".join([str(s) for s in blob.sentences[:2]])

        return {
            "sentiment_score": polarity,
            "sentiment_label": label,
            "summary": summary,
        }