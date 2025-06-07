"""Test the Balboa Spa Client integration."""

from __future__ import annotations

from unittest.mock import MagicMock

from menuai.components.balboa.const import CONF_SYNC_TIME, DOMAIN
from menuai.const import CONF_HOST
from menuai.core import menuai, State

from tests.common import MockConfigEntry

TEST_HOST = "balboatest.localdomain"


async def init_integration(menuai: menuai) -> MockConfigEntry:
    """Mock integration setup."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: TEST_HOST}, options={CONF_SYNC_TIME: True}
    )
    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    return entry


async def client_update(menuai: menuai, client: MagicMock, entity: str) -> State:
    """Update the client."""
    client.emit("")
    await menuai.async_block_till_done()
    assert (state := menuai.states.get(entity)) is not None
    return state
