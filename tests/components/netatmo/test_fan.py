"""The tests for Netatmo fan."""

from unittest.mock import AsyncMock, patch

from syrupy.assertion import SnapshotAssertion

from menuai.components.fan import (
    ATTR_PRESET_MODE,
    DOMAIN as FAN_DOMAIN,
    SERVICE_SET_PRESET_MODE,
)
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .common import selected_platforms, snapshot_platform_entities

from tests.common import MockConfigEntry


async def test_entity(
    menuai: menuai,
    config_entry: MockConfigEntry,
    netatmo_auth: AsyncMock,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test entities."""
    await snapshot_platform_entities(
        menuai,
        config_entry,
        Platform.FAN,
        entity_registry,
        snapshot,
    )


async def test_switch_setup_and_services(
    menuai: menuai, config_entry: MockConfigEntry, netatmo_auth: AsyncMock
) -> None:
    """Test setup and services."""
    with selected_platforms([Platform.FAN]):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)

        await menuai.async_block_till_done()

    fan_entity = "fan.centralized_ventilation_controler"

    assert menuai.states.get(fan_entity).state == "on"
    assert menuai.states.get(fan_entity).attributes[ATTR_PRESET_MODE] == "slow"

    # Test turning switch on
    with patch("pyatmo.home.Home.async_set_state") as mock_set_state:
        await menuai.services.async_call(
            FAN_DOMAIN,
            SERVICE_SET_PRESET_MODE,
            {ATTR_ENTITY_ID: fan_entity, ATTR_PRESET_MODE: "fast"},
            blocking=True,
        )
        await menuai.async_block_till_done()
        mock_set_state.assert_called_once_with(
            {
                "modules": [
                    {
                        "id": "12:34:56:00:01:01:01:b1",
                        "fan_speed": 2,
                        "bridge": "12:34:56:80:60:40",
                    }
                ]
            }
        )
