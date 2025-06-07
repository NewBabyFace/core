"""KNX Telegrams Tests."""

from copy import copy
from datetime import datetime
from typing import Any

import pytest

from menuai.components.knx.const import (
    CONF_KNX_TELEGRAM_LOG_SIZE,
    KNX_MODULE_KEY,
)
from menuai.components.knx.telegrams import TelegramDict
from menuai.core import menuai

from .conftest import KNXTestKit

MOCK_TIMESTAMP = "2023-07-02T14:51:24.045162-07:00"
MOCK_TELEGRAMS = [
    {
        "destination": "1/3/4",
        "destination_name": "",
        "direction": "Incoming",
        "dpt_main": None,
        "dpt_sub": None,
        "dpt_name": None,
        "payload": True,
        "source": "1.2.3",
        "source_name": "",
        "telegramtype": "GroupValueWrite",
        "timestamp": MOCK_TIMESTAMP,
        "unit": None,
        "value": None,
    },
    {
        "destination": "2/2/2",
        "destination_name": "",
        "direction": "Outgoing",
        "dpt_main": None,
        "dpt_sub": None,
        "dpt_name": None,
        "payload": [1, 2, 3, 4],
        "source": "0.0.0",
        "source_name": "MenuAI",
        "telegramtype": "GroupValueWrite",
        "timestamp": MOCK_TIMESTAMP,
        "unit": None,
        "value": None,
    },
]


def assert_telegram_history(telegrams: list[TelegramDict]) -> bool:
    """Assert that the mock telegrams are equal to the given telegrams. Omitting timestamp."""
    assert len(telegrams) == len(MOCK_TELEGRAMS)
    for index, value in enumerate(telegrams):
        test_telegram = copy(value)  # don't modify the original
        comp_telegram = MOCK_TELEGRAMS[index]
        assert datetime.fromisoformat(test_telegram["timestamp"])
        if isinstance(test_telegram["payload"], tuple):
            # JSON encodes tuples to lists
            test_telegram["payload"] = list(test_telegram["payload"])
        assert test_telegram | {"timestamp": MOCK_TIMESTAMP} == comp_telegram
    return True


async def test_store_telegam_history(
    menuai: menuai,
    knx: KNXTestKit,
    menuai_storage: dict[str, Any],
) -> None:
    """Test storing telegram history."""
    await knx.setup_integration()

    await knx.receive_write("1/3/4", True)
    await menuai.services.async_call(
        "knx", "send", {"address": "2/2/2", "payload": [1, 2, 3, 4]}, blocking=True
    )
    await knx.assert_write("2/2/2", (1, 2, 3, 4))

    assert len(menuai.data[KNX_MODULE_KEY].telegrams.recent_telegrams) == 2
    with pytest.raises(KeyError):
        menuai_storage["knx/telegrams_history.json"]

    await menuai.config_entries.async_unload(knx.mock_config_entry.entry_id)
    saved_telegrams = menuai_storage["knx/telegrams_history.json"]["data"]
    assert assert_telegram_history(saved_telegrams)


async def test_load_telegam_history(
    menuai: menuai,
    knx: KNXTestKit,
    menuai_storage: dict[str, Any],
) -> None:
    """Test telegram history restoration."""
    menuai_storage["knx/telegrams_history.json"] = {"version": 1, "data": MOCK_TELEGRAMS}
    await knx.setup_integration()
    loaded_telegrams = menuai.data[KNX_MODULE_KEY].telegrams.recent_telegrams
    assert assert_telegram_history(loaded_telegrams)
    # TelegramDict "payload" is a tuple, this shall be restored when loading from JSON
    assert isinstance(loaded_telegrams[1]["payload"], tuple)


async def test_remove_telegam_history(
    menuai: menuai,
    knx: KNXTestKit,
    menuai_storage: dict[str, Any],
) -> None:
    """Test telegram history removal when configured to size 0."""
    menuai_storage["knx/telegrams_history.json"] = {"version": 1, "data": MOCK_TELEGRAMS}
    knx.mock_config_entry.add_to_menuai(menuai)
    menuai.config_entries.async_update_entry(
        knx.mock_config_entry,
        data=knx.mock_config_entry.data | {CONF_KNX_TELEGRAM_LOG_SIZE: 0},
    )
    await knx.setup_integration(add_entry_to_menuai=False)
    # Store.async_remove() is mocked by menuai_storage - check that data was removed.
    assert "knx/telegrams_history.json" not in menuai_storage
    assert not menuai.data[KNX_MODULE_KEY].telegrams.recent_telegrams
