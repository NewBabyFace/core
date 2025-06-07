"""Test the BlueMaestro sensors."""

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.bluemaestro.const import DOMAIN
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import BLUEMAESTRO_SERVICE_INFO

from tests.common import MockConfigEntry
from tests.components.bluetooth import inject_bluetooth_service_info


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensors(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test setting up creates the sensors."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="aa:bb:cc:dd:ee:ff",
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all("sensor")) == 0
    inject_bluetooth_service_info(menuai, BLUEMAESTRO_SERVICE_INFO)
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all("sensor")) == 5
    entity_entries = er.async_entries_for_config_entry(entity_registry, entry.entry_id)

    assert entity_entries
    for entity_entry in entity_entries:
        assert menuai.states.get(entity_entry.entity_id) == snapshot(
            name=f"{entity_entry.entity_id}-state"
        )
        assert entity_entry == snapshot(name=f"{entity_entry.entity_id}-entry")

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()
