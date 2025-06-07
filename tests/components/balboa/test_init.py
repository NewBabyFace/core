"""Tests of the initialization of the balboa integration."""

from unittest.mock import MagicMock

from menuai.components.balboa.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_HOST
from menuai.core import menuai

from . import TEST_HOST

from tests.common import MockConfigEntry


async def test_setup_entry(
    menuai: menuai, client: MagicMock, integration: MockConfigEntry
) -> None:
    """Validate that setup entry also configure the client."""
    assert integration.state is ConfigEntryState.LOADED
    await menuai.config_entries.async_unload(integration.entry_id)
    assert integration.state is ConfigEntryState.NOT_LOADED


async def test_setup_entry_fails(menuai: menuai, client: MagicMock) -> None:
    """Validate that setup entry also configure the client."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: TEST_HOST,
        },
    )
    config_entry.add_to_menuai(menuai)

    client.connect.return_value = False

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY

    client.connect.return_value = True
    client.async_configuration_loaded.return_value = False

    await menuai.config_entries.async_reload(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY
