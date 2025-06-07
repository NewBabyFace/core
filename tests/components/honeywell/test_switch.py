"""Tests for Honeywell switch component."""

from unittest.mock import MagicMock

from aiosomecomfort.exceptions import SomeComfortError
import pytest

from menuai.components.switch import DOMAIN as SWITCH_DOMAIN
from menuai.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, SERVICE_TURN_ON
from menuai.core import menuai
from menuai.exceptions import menuaiError

from . import init_integration

from tests.common import MockConfigEntry


async def test_emheat_switch(
    menuai: menuai,
    config_entry: MockConfigEntry,
    device: MagicMock,
) -> None:
    """Test emergency heat switch."""

    await init_integration(menuai, config_entry)
    entity_id = f"switch.{device.name}_emergency_heat"
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    device.set_system_mode.assert_called_once_with("emheat")

    device.set_system_mode.reset_mock()

    device.system_mode = "emheat"
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    device.set_system_mode.assert_called_once_with("off")

    device.set_system_mode.reset_mock()
    device.system_mode = "heat"
    device.set_system_mode.side_effect = SomeComfortError
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )
    device.set_system_mode.assert_called_once_with("emheat")

    device.set_system_mode.reset_mock()
    device.system_mode = "emheat"
    device.set_system_mode.side_effect = SomeComfortError
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )
    device.set_system_mode.assert_called_once_with("off")
