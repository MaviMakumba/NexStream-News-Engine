import asyncio
from unittest.mock import AsyncMock, patch
import src.adapters.scheduling.scheduler_service as sched


def setup_function(_):
    sched._tick_index = 0


def test_send_scrape_command_rotates_start_each_tick():
    sched.producer = AsyncMock()
    with patch("src.adapters.scheduling.scheduler_service.settings") as mock_settings:
        mock_settings.scrape_sources = "A,B,C"

        asyncio.run(sched.send_scrape_command())
        first_order = [call.args[1] for call in sched.producer.send_and_wait.call_args_list]

        sched.producer.reset_mock()
        asyncio.run(sched.send_scrape_command())
        second_order = [call.args[1] for call in sched.producer.send_and_wait.call_args_list]

    assert first_order != second_order


def test_send_scrape_command_never_drops_or_duplicates_sources():
    import json
    sched.producer = AsyncMock()
    with patch("src.adapters.scheduling.scheduler_service.settings") as mock_settings:
        mock_settings.scrape_sources = "A,B,C"

        asyncio.run(sched.send_scrape_command())
        sent = [json.loads(call.args[1])["source"] for call in sched.producer.send_and_wait.call_args_list]

    assert sorted(sent) == ["A", "B", "C"]
