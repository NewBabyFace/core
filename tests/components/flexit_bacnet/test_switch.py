"""Tests for the Flexit Nordic (BACnet) switch entities."""

from unittest.mock import AsyncMock

from flexit_bacnet import DecodingError
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from menuai.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON, Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from . import setup_with_selected_platforms

from tests.common import MockConfigEntry, snapshot_platform

ENTITY_ID = "switch.device_name_electric_heater"


async def test_switches(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_flexit_bacnet: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test switch states are correctly collected from library."""

    await setup_with_selected_platforms(menuai, mock_config_entry, [Platform.SWITCH])

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_switches_implementation(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_flexit_bacnet: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that the switch can be turned on and off."""

    await setup_with_selected_platforms(menuai, mock_config_entry, [Platform.SWITCH])
    assert menuai.states.get(ENTITY_ID) == snapshot(name=f"{ENTITY_ID}-state")

    # Set to off
    mock_flexit_bacnet.electric_heater = False

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )

    mocked_method = mock_flexit_bacnet.disable_electric_heater
    assert len(mocked_method.mock_calls) == 1
    assert menuai.states.get(ENTITY_ID).state == STATE_OFF

    # Set to on
    mock_flexit_bacnet.electric_heater = True

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )

    mocked_method = mock_flexit_bacnet.enable_electric_heater
    assert len(mocked_method.mock_calls) == 1
    assert menuai.states.get(ENTITY_ID).state == STATE_ON

    # Error recovery, when turning off
    mock_flexit_bacnet.disable_electric_heater.side_effect = DecodingError

    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: ENTITY_ID},
            blocking=True,
        )

    mocked_method = mock_flexit_bacnet.disable_electric_heater
    assert len(mocked_method.mock_calls) == 2

    mock_flexit_bacnet.disable_electric_heater.side_effect = None
    mock_flexit_bacnet.electric_heater = False

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )

    assert menuai.states.get(ENTITY_ID).state == STATE_OFF

    # Error recovery, when turning on
    mock_flexit_bacnet.enable_electric_heater.side_effect = DecodingError

    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: ENTITY_ID},
            blocking=True,
        )

    mocked_method = mock_flexit_bacnet.enable_electric_heater
    assert len(mocked_method.mock_calls) == 2

    mock_flexit_bacnet.enable_electric_heater.side_effect = None
    mock_flexit_bacnet.electric_heater = True

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )

    assert menuai.states.get(ENTITY_ID).state == STATE_ON
