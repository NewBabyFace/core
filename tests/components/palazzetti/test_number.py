"""Tests for the Palazzetti sensor platform."""

from unittest.mock import AsyncMock, patch

from pypalazzetti.exceptions import CommunicationError, ValidationError
from pypalazzetti.fan import FanType
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.number import DOMAIN as NUMBER_DOMAIN, SERVICE_SET_VALUE
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError, ServiceValidationError
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, snapshot_platform

POWER_ENTITY_ID = "number.stove_combustion_power"
FAN_ENTITY_ID = "number.stove_left_fan_speed"


async def test_all_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_palazzetti_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    with patch("menuai.components.palazzetti.PLATFORMS", [Platform.NUMBER]):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_async_set_data_power(
    menuai: menuai,
    mock_palazzetti_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setting number data via service call."""
    await setup_integration(menuai, mock_config_entry)

    # Set value: Success
    await menuai.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: POWER_ENTITY_ID, "value": 1},
        blocking=True,
    )
    mock_palazzetti_client.set_power_mode.assert_called_once_with(1)
    mock_palazzetti_client.set_power_mode.reset_mock()

    # Set value: Error
    mock_palazzetti_client.set_power_mode.side_effect = CommunicationError()
    message = "Could not connect to the device"
    with pytest.raises(menuaiError, match=message):
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: POWER_ENTITY_ID, "value": 1},
            blocking=True,
        )
    mock_palazzetti_client.set_power_mode.reset_mock()

    mock_palazzetti_client.set_power_mode.side_effect = ValidationError()
    message = "Combustion power 1.0 is invalid"
    with pytest.raises(ServiceValidationError, match=message):
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: POWER_ENTITY_ID, "value": 1},
            blocking=True,
        )


async def test_async_set_data_fan(
    menuai: menuai,
    mock_palazzetti_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setting number data via service call."""
    await setup_integration(menuai, mock_config_entry)

    # Set value: Success
    await menuai.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: FAN_ENTITY_ID, "value": 1},
        blocking=True,
    )
    mock_palazzetti_client.set_fan_speed.assert_called_once_with(1, FanType.LEFT)
    mock_palazzetti_client.set_on.reset_mock()

    # Set value: Error
    mock_palazzetti_client.set_fan_speed.side_effect = CommunicationError()
    message = "Could not connect to the device"
    with pytest.raises(menuaiError, match=message):
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: FAN_ENTITY_ID, "value": 1},
            blocking=True,
        )
    mock_palazzetti_client.set_on.reset_mock()

    mock_palazzetti_client.set_fan_speed.side_effect = ValidationError()
    message = "Fan left speed 1.0 is invalid"
    with pytest.raises(ServiceValidationError, match=message):
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: FAN_ENTITY_ID, "value": 1},
            blocking=True,
        )
