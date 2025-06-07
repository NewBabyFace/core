"""Test the Tessie binary sensor platform."""

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .common import assert_entities, setup_platform


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_binary_sensors(
    menuai: menuai, snapshot: SnapshotAssertion, entity_registry: er.EntityRegistry
) -> None:
    """Tests that the binary sensor entities are correct."""

    entry = await setup_platform(menuai, [Platform.BINARY_SENSOR])

    assert_entities(menuai, entry.entry_id, entity_registry, snapshot)
