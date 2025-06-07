"""Test for sensor platform of the Cookidoo integration."""

from collections.abc import Generator
from unittest.mock import patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.config_entries import ConfigEntryState
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry, snapshot_platform


@pytest.fixture(autouse=True)
def sensor_only() -> Generator[None]:
    """Enable only the sensor platform."""
    with patch(
        "menuai.components.cookidoo.PLATFORMS",
        [Platform.SENSOR],
    ):
        yield


@pytest.mark.usefixtures("mock_cookidoo_client")
async def test_setup(
    menuai: menuai,
    cookidoo_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
) -> None:
    """Snapshot test states of sensor platform."""

    cookidoo_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(cookidoo_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert cookidoo_config_entry.state is ConfigEntryState.LOADED

    await snapshot_platform(
        menuai, entity_registry, snapshot, cookidoo_config_entry.entry_id
    )
