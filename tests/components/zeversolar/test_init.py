"""Test the init file code."""

from unittest.mock import patch

from zeversolar import ZeverSolarData
from zeversolar.exceptions import ZeverSolarTimeout

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from tests.common import MockConfigEntry


async def test_async_setup_entry_fails(
    menuai: menuai, config_entry: MockConfigEntry, zeversolar_data: ZeverSolarData
) -> None:
    """Test to load/unload the integration."""

    config_entry.add_to_menuai(menuai)

    with (
        patch("zeversolar.ZeverSolarClient.get_data", side_effect=ZeverSolarTimeout),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY

    with (
        patch("menuai.components.zeversolar.PLATFORMS", []),
        patch("zeversolar.ZeverSolarClient.get_data", return_value=zeversolar_data),
    ):
        menuai.config_entries.async_schedule_reload(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.LOADED

    with (
        patch("menuai.components.zeversolar.PLATFORMS", []),
    ):
        result = await menuai.config_entries.async_unload(config_entry.entry_id)
    assert result is True
    assert config_entry.state is ConfigEntryState.NOT_LOADED
