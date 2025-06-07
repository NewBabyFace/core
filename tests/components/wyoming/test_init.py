"""Test init."""

from unittest.mock import patch

from menuai.config_entries import ConfigEntry
from menuai.core import menuai


async def test_cannot_connect(
    menuai: menuai, stt_config_entry: ConfigEntry
) -> None:
    """Test we handle cannot connect error."""
    with patch(
        "menuai.components.wyoming.data.load_wyoming_info",
        return_value=None,
    ):
        assert not await menuai.config_entries.async_setup(stt_config_entry.entry_id)


async def test_unload(
    menuai: menuai, stt_config_entry: ConfigEntry, init_wyoming_stt
) -> None:
    """Test unload."""
    assert await menuai.config_entries.async_unload(stt_config_entry.entry_id)
