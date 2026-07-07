import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.fixture
def app_client():
    """
    DB ve Kafka bağlantısı olmadan FastAPI TestClient döner.
    Tüm HTTP katmanı testleri bu fixture'ı kullanmalı.
    """
    async def _noop_broadcast(*args, **kwargs):
        """Test sırasında DB polling task'ını bastır."""
        await asyncio.sleep(9999)

    with patch("src.infrastructure.config.database.engine") as mock_engine, \
         patch("src.infrastructure.config.database.Base") as mock_base, \
         patch("src.adapters.messaging.kafka_publisher.KafkaPublisherAdapter") as mock_kafka, \
         patch("src.dependencies.get_search_repository"), \
         patch("src.main._broadcast_new_articles", side_effect=_noop_broadcast), \
         patch("src.main.run_newsletter_job", side_effect=_noop_broadcast), \
         patch("src.main.run_retention_job", side_effect=_noop_broadcast):
        mock_base.metadata.create_all = MagicMock()

        mock_kafka_instance = AsyncMock()
        mock_kafka_instance.start = AsyncMock(return_value=None)
        mock_kafka_instance.stop = AsyncMock(return_value=None)
        mock_kafka.return_value = mock_kafka_instance

        import importlib
        import src.main
        importlib.reload(src.main)
        from src.main import app
        from fastapi.testclient import TestClient
        with TestClient(app) as client:
            yield client
