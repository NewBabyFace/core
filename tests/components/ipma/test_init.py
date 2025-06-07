"""Test the IPMA integration."""

from unittest.mock import patch

from pyipma import IPMAException

from menuai.components.ipma.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_MODE
from menuai.core import menuai

from .test_weather import MockLocation

from tests.common import MockConfigEntry


async def test_async_setup_raises_entry_not_ready(menuai: menuai) -> None:
    """Test that it throws ConfigEntryNotReady when exception occurs during setup."""

    with patch(
        "pyipma.location.Location.get", side_effect=IPMAException("API unavailable")
    ):
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            title="Home",
            data={CONF_LATITUDE: 0, CONF_LONGITUDE: 0, CONF_MODE: "daily"},
        )

        config_entry.add_to_menuai(menuai)

        await menuai.config_entries.async_setup(config_entry.entry_id)

        assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload_config_entry(menuai: menuai) -> None:
    """Test entry unloading."""

    with patch(
        "pyipma.location.Location.get",
        return_value=MockLocation(),
    ):
        config_entry = MockConfigEntry(
            domain="ipma",
            data={CONF_LATITUDE: 0, CONF_LONGITUDE: 0, CONF_MODE: "daily"},
        )
        config_entry.add_to_menuai(menuai)

        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

        assert config_entry.state is ConfigEntryState.LOADED

        await menuai.config_entries.async_unload(config_entry.entry_id)
        await menuai.async_block_till_done()

        assert config_entry.state is ConfigEntryState.NOT_LOADED
