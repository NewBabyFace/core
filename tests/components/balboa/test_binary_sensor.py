"""Tests of the binary sensors of the balboa integration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from syrupy.assertion import SnapshotAssertion

from menuai.const import STATE_OFF, STATE_ON, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import init_integration

from tests.common import MockConfigEntry, snapshot_platform

ENTITY_BINARY_SENSOR = "binary_sensor.fakespa_"


async def test_binary_sensors(
    menuai: menuai,
    client: MagicMock,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test spa binary sensors."""
    with patch("menuai.components.balboa.PLATFORMS", [Platform.BINARY_SENSOR]):
        entry = await init_integration(menuai)

    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)


async def test_filters(
    menuai: menuai, client: MagicMock, integration: MockConfigEntry
) -> None:
    """Test spa filters."""
    for num in (1, 2):
        sensor = f"{ENTITY_BINARY_SENSOR}filter_cycle_{num}"

        state = menuai.states.get(sensor)
        assert state.state == STATE_OFF

        setattr(client, f"filter_cycle_{num}_running", True)
        client.emit("")
        await menuai.async_block_till_done()

        state = menuai.states.get(sensor)
        assert state.state == STATE_ON


async def test_circ_pump(
    menuai: menuai, client: MagicMock, integration: MockConfigEntry
) -> None:
    """Test spa circ pump."""
    sensor = f"{ENTITY_BINARY_SENSOR}circulation_pump"

    state = menuai.states.get(sensor)
    assert state.state == STATE_OFF

    client.circulation_pump.state = 1
    client.emit("")
    await menuai.async_block_till_done()

    state = menuai.states.get(sensor)
    assert state.state == STATE_ON
