"""Test cases for the Webmin sensors."""

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .conftest import async_init_integration

from tests.common import snapshot_platform


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensor(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the sensor entities and states."""

    entry = await async_init_integration(menuai)

    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)
