"""Test the Melnor sensors."""

from __future__ import annotations

from menuai.components.switch import SwitchDeviceClass
from menuai.const import STATE_OFF, STATE_ON
from menuai.core import menuai

from .conftest import (
    mock_config_entry,
    patch_async_ble_device_from_address,
    patch_async_register_callback,
    patch_melnor_device,
)


async def test_manual_watering_switch_metadata(menuai: menuai) -> None:
    """Test the manual watering switch."""

    entry = mock_config_entry(menuai)

    with (
        patch_async_ble_device_from_address(),
        patch_melnor_device(),
        patch_async_register_callback(),
    ):
        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

        switch = menuai.states.get("switch.zone_1")

        assert switch is not None
        assert switch.attributes["device_class"] == SwitchDeviceClass.SWITCH


async def test_manual_watering_switch_on_off(menuai: menuai) -> None:
    """Test the manual watering switch."""

    entry = mock_config_entry(menuai)

    with (
        patch_async_ble_device_from_address(),
        patch_melnor_device() as device_patch,
        patch_async_register_callback(),
    ):
        device = device_patch.return_value

        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

        switch = menuai.states.get("switch.zone_1")

        assert switch is not None
        assert switch.state is STATE_OFF

        await menuai.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": "switch.zone_1"},
            blocking=True,
        )

        switch = menuai.states.get("switch.zone_1")

        assert switch is not None
        assert switch.state is STATE_ON
        assert device.zone1.is_watering is True

        await menuai.services.async_call(
            "switch",
            "turn_off",
            {"entity_id": "switch.zone_1"},
            blocking=True,
        )

        switch = menuai.states.get("switch.zone_1")

        assert switch is not None
        assert switch.state is STATE_OFF
        assert device.zone1.is_watering is False


async def test_schedule_enabled_switch_on_off(menuai: menuai) -> None:
    """Test the schedule enabled switch."""

    entry = mock_config_entry(menuai)

    with (
        patch_async_ble_device_from_address(),
        patch_melnor_device() as device_patch,
        patch_async_register_callback(),
    ):
        device = device_patch.return_value

        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

        switch = menuai.states.get("switch.zone_1_schedule")

        assert switch is not None
        assert switch.state is STATE_OFF
        assert device.zone1.schedule_enabled is False

        await menuai.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": "switch.zone_1_schedule"},
            blocking=True,
        )

        switch = menuai.states.get("switch.zone_1_schedule")

        assert switch is not None
        assert switch.state is STATE_ON
        assert device.zone1.schedule_enabled is True
