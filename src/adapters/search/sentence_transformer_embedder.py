import os
from sentence_transformers import SentenceTransformer
from src.domain.ports.embedding_port import EmbeddingPort

_model_instance: SentenceTransformer = None


def _get_model() -> SentenceTransformer:
    global _model_instance
    if _model_instance is None:
        _model_instance = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _model_instance


class SentenceTransformerEmbedder(EmbeddingPort):

    def __init__(self):
        self.model = _get_model()

    def embed_text(self, text: str) -> list[float]:
        return self.model.encode(text, normalize_embeddings=True).tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [v.tolist() for v in self.model.encode(texts, normalize_embeddings=True)]
