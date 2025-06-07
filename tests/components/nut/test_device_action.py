"""The tests for Network UPS Tools (NUT) device actions."""

from unittest.mock import AsyncMock

from aionut import NUTError
import pytest
from pytest_unordered import unordered

from menuai.components import automation, device_automation
from menuai.components.device_automation import (
    DeviceAutomationType,
    InvalidDeviceAutomationConfig,
)
from menuai.components.nut import DOMAIN
from menuai.components.nut.const import INTEGRATION_SUPPORTED_COMMANDS
from menuai.const import CONF_DEVICE_ID, CONF_TYPE
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import device_registry as dr
from menuai.setup import async_setup_component

from .util import async_init_integration

from tests.common import MockConfigEntry, async_get_device_automations


async def test_get_all_actions_for_specified_user(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test we get all the expected actions from a nut if user is specified."""
    list_commands_return_value = {
        supported_command: supported_command
        for supported_command in INTEGRATION_SUPPORTED_COMMANDS
    }

    await async_init_integration(
        menuai,
        username="someuser",
        password="somepassword",
        list_vars={"ups.status": "OL"},
        list_commands_return_value=list_commands_return_value,
    )
    device_entry = next(device for device in device_registry.devices.values())
    expected_actions = [
        {
            "domain": DOMAIN,
            "type": action.replace(".", "_"),
            "device_id": device_entry.id,
            "metadata": {},
        }
        for action in INTEGRATION_SUPPORTED_COMMANDS
    ]
    actions = await async_get_device_automations(
        menuai, DeviceAutomationType.ACTION, device_entry.id
    )
    assert actions == unordered(expected_actions)


async def test_no_actions_for_anonymous_user(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test we get no actions if user is not specified."""
    list_commands_return_value = {"some action": "some description"}

    await async_init_integration(
        menuai,
        username=None,
        password=None,
        list_vars={"ups.status": "OL"},
        list_commands_return_value=list_commands_return_value,
    )
    device_entry = next(device for device in device_registry.devices.values())
    actions = await async_get_device_automations(
        menuai, DeviceAutomationType.ACTION, device_entry.id
    )

    assert len(actions) == 0


async def test_no_actions_device_not_found(
    menuai: menuai,
) -> None:
    """Test we get no actions for a device that cannot be found."""
    list_commands_return_value = {"beeper.enable": None}
    await async_init_integration(
        menuai,
        list_vars={"ups.status": "OL"},
        list_commands_return_value=list_commands_return_value,
    )

    device_id = "invalid_device_id"
    platform = await device_automation.async_get_device_automation_platform(
        menuai, DOMAIN, DeviceAutomationType.ACTION
    )
    actions = await platform.async_get_actions(menuai, device_id)

    assert len(actions) == 0


async def test_no_actions_device_invalid(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test we get no actions for a device that is invalid."""
    list_commands_return_value = {"beeper.enable": None}
    entry = await async_init_integration(
        menuai,
        list_vars={"ups.status": "OL"},
        list_commands_return_value=list_commands_return_value,
    )
    device_entry = next(device for device in device_registry.devices.values())

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    platform = await device_automation.async_get_device_automation_platform(
        menuai, DOMAIN, DeviceAutomationType.ACTION
    )
    actions = await platform.async_get_actions(menuai, device_entry.id)

    assert len(actions) == 0


async def test_list_commands_exception(
    menuai: menuai, device_registry: dr.DeviceRegistry
) -> None:
    """Test there are no actions if list_commands raises exception."""
    await async_init_integration(
        menuai, list_vars={"ups.status": "OL"}, list_commands_side_effect=NUTError
    )

    device_entry = next(device for device in device_registry.devices.values())
    actions = await async_get_device_automations(
        menuai, DeviceAutomationType.ACTION, device_entry.id
    )
    assert len(actions) == 0


async def test_unsupported_command(
    menuai: menuai, device_registry: dr.DeviceRegistry
) -> None:
    """Test unsupported command is excluded."""

    list_commands_return_value = {
        "beeper.enable": None,
        "device.something": "Does something unsupported",
    }
    await async_init_integration(
        menuai,
        list_vars={"ups.status": "OL"},
        list_commands_return_value=list_commands_return_value,
    )
    device_entry = next(device for device in device_registry.devices.values())
    actions = await async_get_device_automations(
        menuai, DeviceAutomationType.ACTION, device_entry.id
    )
    assert len(actions) == 1


async def test_action(menuai: menuai, device_registry: dr.DeviceRegistry) -> None:
    """Test actions are executed."""

    list_commands_return_value = {
        "beeper.enable": None,
        "beeper.disable": None,
    }
    run_command = AsyncMock()
    await async_init_integration(
        menuai,
        list_ups={"someUps": "Some UPS"},
        list_vars={"ups.status": "OL"},
        list_commands_return_value=list_commands_return_value,
        run_command=run_command,
    )
    device_entry = next(device for device in device_registry.devices.values())

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {
                        "platform": "event",
                        "event_type": "test_some_event",
                    },
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "type": "beeper_enable",
                    },
                },
                {
                    "trigger": {
                        "platform": "event",
                        "event_type": "test_another_event",
                    },
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "type": "beeper_disable",
                    },
                },
            ]
        },
    )

    menuai.bus.async_fire("test_some_event")
    await menuai.async_block_till_done()
    run_command.assert_called_with("someUps", "beeper.enable")

    menuai.bus.async_fire("test_another_event")
    await menuai.async_block_till_done()
    run_command.assert_called_with("someUps", "beeper.disable")


async def test_run_command_exception(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test if run command raises exception with translation."""

    command_name = "beeper.enable"
    nut_error_message = "Something wrong happened"
    run_command = AsyncMock(side_effect=NUTError(nut_error_message))
    await async_init_integration(
        menuai,
        list_vars={"ups.status": "OL"},
        list_ups={"ups1": "UPS 1"},
        list_commands_return_value={command_name: None},
        run_command=run_command,
    )
    device_entry = next(device for device in device_registry.devices.values())

    platform = await device_automation.async_get_device_automation_platform(
        menuai, DOMAIN, DeviceAutomationType.ACTION
    )

    error_message = f"Error running command {command_name}, {nut_error_message}"
    with pytest.raises(menuaiError, match=error_message):
        await platform.async_call_action_from_config(
            menuai,
            {
                CONF_TYPE: command_name,
                CONF_DEVICE_ID: device_entry.id,
            },
            {},
            None,
        )


async def test_action_exception_device_not_found(menuai: menuai) -> None:
    """Test raises exception if device not found."""
    list_commands_return_value = {"beeper.enable": None}
    await async_init_integration(
        menuai,
        list_vars={"ups.status": "OL"},
        list_commands_return_value=list_commands_return_value,
    )

    platform = await device_automation.async_get_device_automation_platform(
        menuai, DOMAIN, DeviceAutomationType.ACTION
    )

    device_id = "invalid_device_id"
    error_message = f"Unable to find a NUT device with ID {device_id}"
    with pytest.raises(InvalidDeviceAutomationConfig, match=error_message):
        await platform.async_call_action_from_config(
            menuai,
            {CONF_TYPE: "beeper.enable", CONF_DEVICE_ID: device_id},
            {},
            None,
        )


async def test_action_exception_invalid_config(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test raises exception if no NUT config entry found."""

    config_entry = MockConfigEntry()
    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, "mock-identifier")},
    )

    platform = await device_automation.async_get_device_automation_platform(
        menuai, DOMAIN, DeviceAutomationType.ACTION
    )

    with pytest.raises(InvalidDeviceAutomationConfig):
        await platform.async_call_action_from_config(
            menuai,
            {CONF_TYPE: "beeper.enable", CONF_DEVICE_ID: device_entry.id},
            {},
            None,
        )


async def test_action_exception_device_invalid(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test raises exception if config entry for device is invalid."""
    list_commands_return_value = {"beeper.enable": None}
    entry = await async_init_integration(
        menuai,
        list_vars={"ups.status": "OL"},
        list_commands_return_value=list_commands_return_value,
    )
    device_entry = next(device for device in device_registry.devices.values())

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    platform = await device_automation.async_get_device_automation_platform(
        menuai, DOMAIN, DeviceAutomationType.ACTION
    )

    error_message = (
        f"Invalid configuration entries for NUT device with ID {device_entry.id}"
    )
    with pytest.raises(InvalidDeviceAutomationConfig, match=error_message):
        await platform.async_call_action_from_config(
            menuai,
            {CONF_TYPE: "beeper.enable", CONF_DEVICE_ID: device_entry.id},
            {},
            None,
        )
