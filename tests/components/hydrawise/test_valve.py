"""Test Hydrawise valve."""

from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock, patch

from pydrawise.schema import Zone
from syrupy.assertion import SnapshotAssertion

from menuai.components.valve import DOMAIN as VALVE_DOMAIN
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_CLOSE_VALVE,
    SERVICE_OPEN_VALVE,
    Platform,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry, snapshot_platform


async def test_all_valves(
    menuai: menuai,
    mock_add_config_entry: Callable[[], Awaitable[MockConfigEntry]],
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test that all valves are working."""
    with patch(
        "menuai.components.hydrawise.PLATFORMS",
        [Platform.VALVE],
    ):
        config_entry = await mock_add_config_entry()
        await snapshot_platform(menuai, entity_registry, snapshot, config_entry.entry_id)


async def test_services(
    menuai: menuai,
    mock_added_config_entry: MockConfigEntry,
    mock_pydrawise: AsyncMock,
    zones: list[Zone],
) -> None:
    """Test valve services."""
    await menuai.services.async_call(
        VALVE_DOMAIN,
        SERVICE_OPEN_VALVE,
        service_data={ATTR_ENTITY_ID: "valve.zone_one"},
        blocking=True,
    )
    mock_pydrawise.start_zone.assert_called_once_with(zones[0])
    mock_pydrawise.reset_mock()

    await menuai.services.async_call(
        VALVE_DOMAIN,
        SERVICE_CLOSE_VALVE,
        service_data={ATTR_ENTITY_ID: "valve.zone_one"},
        blocking=True,
    )
    mock_pydrawise.stop_zone.assert_called_once_with(zones[0])
