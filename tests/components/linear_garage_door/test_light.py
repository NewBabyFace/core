"""Test Linear Garage Door light."""

from datetime import timedelta
from unittest.mock import AsyncMock

from freezegun.api import FrozenDateTimeFactory
from syrupy.assertion import SnapshotAssertion

from menuai.components.light import (
    DOMAIN as LIGHT_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from menuai.components.linear_garage_door import DOMAIN
from menuai.const import (
    ATTR_ENTITY_ID,
    CONF_BRIGHTNESS,
    STATE_OFF,
    STATE_ON,
    Platform,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_load_json_object_fixture,
    snapshot_platform,
)


async def test_data(
    menuai: menuai,
    mock_linear: AsyncMock,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that data gets parsed and returned appropriately."""

    await setup_integration(menuai, mock_config_entry, [Platform.LIGHT])

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_turn_on(
    menuai: menuai, mock_linear: AsyncMock, mock_config_entry: MockConfigEntry
) -> None:
    """Test that turning on the light works as intended."""

    await setup_integration(menuai, mock_config_entry, [Platform.LIGHT])

    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "light.test_garage_2_light"},
        blocking=True,
    )

    assert mock_linear.operate_device.call_count == 1


async def test_turn_on_with_brightness(
    menuai: menuai, mock_linear: AsyncMock, mock_config_entry: MockConfigEntry
) -> None:
    """Test that turning on the light works as intended."""

    await setup_integration(menuai, mock_config_entry, [Platform.LIGHT])

    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "light.test_garage_2_light", CONF_BRIGHTNESS: 50},
        blocking=True,
    )

    mock_linear.operate_device.assert_called_once_with(
        "test2", "Light", "DimPercent:20"
    )


async def test_turn_off(
    menuai: menuai, mock_linear: AsyncMock, mock_config_entry: MockConfigEntry
) -> None:
    """Test that turning off the light works as intended."""

    await setup_integration(menuai, mock_config_entry, [Platform.LIGHT])

    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "light.test_garage_1_light"},
        blocking=True,
    )

    assert mock_linear.operate_device.call_count == 1


async def test_update_light_state(
    menuai: menuai,
    mock_linear: AsyncMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that turning off the light works as intended."""

    await setup_integration(menuai, mock_config_entry, [Platform.LIGHT])

    assert menuai.states.get("light.test_garage_1_light").state == STATE_ON
    assert menuai.states.get("light.test_garage_2_light").state == STATE_OFF

    device_states = await async_load_json_object_fixture(
        menuai, "get_device_state_1.json", DOMAIN
    )
    mock_linear.get_device_state.side_effect = lambda device_id: device_states[
        device_id
    ]

    freezer.tick(timedelta(seconds=60))
    async_fire_time_changed(menuai)

    assert menuai.states.get("light.test_garage_1_light").state == STATE_OFF
    assert menuai.states.get("light.test_garage_2_light").state == STATE_ON
