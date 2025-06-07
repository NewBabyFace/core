"""Tests for the Flexit Nordic (BACnet) number entities."""

from unittest.mock import AsyncMock

from flexit_bacnet import DecodingError
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from . import setup_with_selected_platforms

from tests.common import MockConfigEntry, snapshot_platform

ENTITY_ID = "number.device_name_fireplace_supply_fan_setpoint"


async def test_numbers(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_flexit_bacnet: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test number states are correctly collected from library."""

    await setup_with_selected_platforms(menuai, mock_config_entry, [Platform.NUMBER])

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_numbers_implementation(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_flexit_bacnet: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that the number can be changed."""

    await setup_with_selected_platforms(menuai, mock_config_entry, [Platform.NUMBER])

    mock_flexit_bacnet.fan_setpoint_supply_air_fire = 60

    await menuai.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {
            ATTR_ENTITY_ID: ENTITY_ID,
            ATTR_VALUE: 60,
        },
        blocking=True,
    )

    mocked_method = mock_flexit_bacnet.set_fan_setpoint_supply_air_fire
    assert len(mocked_method.mock_calls) == 1
    assert menuai.states.get(ENTITY_ID).state == "60"

    mock_flexit_bacnet.fan_setpoint_supply_air_fire = 40

    await menuai.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {
            ATTR_ENTITY_ID: ENTITY_ID,
            ATTR_VALUE: 40,
        },
        blocking=True,
    )

    mocked_method = mock_flexit_bacnet.set_fan_setpoint_supply_air_fire
    assert len(mocked_method.mock_calls) == 2
    assert menuai.states.get(ENTITY_ID).state == "40"

    # Error recovery, when setting the value
    mock_flexit_bacnet.set_fan_setpoint_supply_air_fire.side_effect = DecodingError

    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {
                ATTR_ENTITY_ID: ENTITY_ID,
                ATTR_VALUE: 40,
            },
            blocking=True,
        )

    mocked_method = mock_flexit_bacnet.set_fan_setpoint_supply_air_fire
    assert len(mocked_method.mock_calls) == 3

    mock_flexit_bacnet.set_fan_setpoint_supply_air_fire.side_effect = None
    mock_flexit_bacnet.fan_setpoint_supply_air_fire = 30

    await menuai.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {
            ATTR_ENTITY_ID: ENTITY_ID,
            ATTR_VALUE: 30,
        },
        blocking=True,
    )

    assert menuai.states.get(ENTITY_ID).state == "30"
