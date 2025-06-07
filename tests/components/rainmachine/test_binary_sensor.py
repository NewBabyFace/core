"""Test RainMachine binary sensors."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.rainmachine import DOMAIN
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry, snapshot_platform


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_binary_sensors(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    config: dict[str, Any],
    config_entry: MockConfigEntry,
    client: AsyncMock,
) -> None:
    """Test binary sensors."""
    with (
        patch("menuai.components.rainmachine.Client", return_value=client),
        patch(
            "menuai.components.rainmachine.PLATFORMS", [Platform.BINARY_SENSOR]
        ),
    ):
        assert await async_setup_component(menuai, DOMAIN, config)
        await menuai.async_block_till_done()
    await snapshot_platform(menuai, entity_registry, snapshot, config_entry.entry_id)
