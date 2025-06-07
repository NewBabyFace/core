"""Test opentherm_gw buttons."""

from unittest.mock import AsyncMock, MagicMock

from pyotgw.vars import OTGW_MODE_RESET

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.components.opentherm_gw import DOMAIN
from menuai.components.opentherm_gw.const import OpenThermDeviceIdentifier
from menuai.const import ATTR_ENTITY_ID, CONF_ID
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .conftest import MINIMAL_STATUS

from tests.common import MockConfigEntry


async def test_cancel_room_setpoint_override_button(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_config_entry: MockConfigEntry,
    mock_pyotgw: MagicMock,
) -> None:
    """Test cancel room setpoint override button."""

    mock_pyotgw.return_value.set_target_temp = AsyncMock(return_value=0)
    mock_config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert (
        button_entity_id := entity_registry.async_get_entity_id(
            BUTTON_DOMAIN,
            DOMAIN,
            f"{mock_config_entry.data[CONF_ID]}-{OpenThermDeviceIdentifier.THERMOSTAT}-cancel_room_setpoint_override",
        )
    ) is not None

    await menuai.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {
            ATTR_ENTITY_ID: button_entity_id,
        },
        blocking=True,
    )

    mock_pyotgw.return_value.set_target_temp.assert_awaited_once_with(0, True)


async def test_restart_button(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_config_entry: MockConfigEntry,
    mock_pyotgw: MagicMock,
) -> None:
    """Test restart button."""

    mock_pyotgw.return_value.set_mode = AsyncMock(return_value=MINIMAL_STATUS)
    mock_config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert (
        button_entity_id := entity_registry.async_get_entity_id(
            BUTTON_DOMAIN,
            DOMAIN,
            f"{mock_config_entry.data[CONF_ID]}-{OpenThermDeviceIdentifier.GATEWAY}-restart_button",
        )
    ) is not None

    await menuai.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {
            ATTR_ENTITY_ID: button_entity_id,
        },
        blocking=True,
    )

    mock_pyotgw.return_value.set_mode.assert_awaited_once_with(OTGW_MODE_RESET)
