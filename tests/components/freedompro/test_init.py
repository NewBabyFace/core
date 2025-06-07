"""Freedompro component tests."""

import logging
from unittest.mock import patch

from menuai.components.freedompro.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from tests.common import MockConfigEntry

LOGGER = logging.getLogger(__name__)

ENTITY_ID = f"{DOMAIN}.fake_name"


async def test_async_setup_entry(
    menuai: menuai, init_integration: MockConfigEntry
) -> None:
    """Test a successful setup entry."""
    entry = init_integration
    assert entry is not None
    state = menuai.states
    assert state is not None


async def test_config_not_ready(menuai: menuai) -> None:
    """Test for setup failure if connection to Freedompro is missing."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Feedompro",
        unique_id="0123456",
        data={
            "api_key": "gdhsksjdhcncjdkdjndjdkdmndjdjdkd",
        },
    )

    with patch(
        "menuai.components.freedompro.coordinator.get_list",
        return_value={
            "state": False,
        },
    ):
        entry.add_to_menuai(menuai)
        await menuai.config_entries.async_setup(entry.entry_id)
        assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload_entry(
    menuai: menuai, init_integration: MockConfigEntry
) -> None:
    """Test successful unload of entry."""
    entry = init_integration

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
