"""Tests for the Gree Integration."""

from unittest.mock import patch

from menuai.components.gree.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry


async def test_setup_simple(menuai: menuai) -> None:
    """Test gree integration is setup."""
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.gree.climate.async_setup_entry",
            return_value=True,
        ) as climate_setup,
        patch(
            "menuai.components.gree.switch.async_setup_entry",
            return_value=True,
        ) as switch_setup,
    ):
        assert await async_setup_component(menuai, DOMAIN, {})
        await menuai.async_block_till_done()

        assert len(climate_setup.mock_calls) == 1
        assert len(switch_setup.mock_calls) == 1
        assert entry.state is ConfigEntryState.LOADED

    # No flows started
    assert len(menuai.config_entries.flow.async_progress()) == 0


async def test_unload_config_entry(menuai: menuai) -> None:
    """Test that the async_unload_entry works."""
    # As we have currently no configuration, we just to pass the domain here.
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_menuai(menuai)

    assert await async_setup_component(menuai, DOMAIN, {})
    await menuai.async_block_till_done()

    await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
