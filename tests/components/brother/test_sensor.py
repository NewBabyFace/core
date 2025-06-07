"""Test sensor of Brother integration."""

from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.brother.const import DOMAIN, UPDATE_INTERVAL
from menuai.components.sensor import DOMAIN as SENSOR_DOMAIN
from menuai.const import STATE_UNAVAILABLE, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import init_integration

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensors(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_brother_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test states of the sensors."""
    with patch("menuai.components.brother.PLATFORMS", [Platform.SENSOR]):
        await init_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_availability(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    mock_brother_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Ensure that we mark the entities unavailable correctly when device is offline."""
    entity_id = "sensor.hl_l2340dw_status"
    await init_integration(menuai, mock_config_entry)

    state = menuai.states.get(entity_id)
    assert state
    assert state.state != STATE_UNAVAILABLE
    assert state.state == "waiting"

    mock_brother_client.async_update.side_effect = ConnectionError
    freezer.tick(UPDATE_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_UNAVAILABLE

    mock_brother_client.async_update.side_effect = None
    freezer.tick(UPDATE_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state
    assert state.state != STATE_UNAVAILABLE
    assert state.state == "waiting"


async def test_unique_id_migration(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_config_entry: MockConfigEntry,
    mock_brother_client: AsyncMock,
) -> None:
    """Test states of the unique_id migration."""

    entity_registry.async_get_or_create(
        SENSOR_DOMAIN,
        DOMAIN,
        "0123456789_b/w_counter",
        suggested_object_id="hl_l2340dw_b_w_counter",
        disabled_by=None,
    )

    await init_integration(menuai, mock_config_entry)

    entry = entity_registry.async_get("sensor.hl_l2340dw_b_w_counter")
    assert entry
    assert entry.unique_id == "0123456789_bw_counter"
