"""Test the Melnor sensors."""

from __future__ import annotations

from menuai.core import menuai

from .conftest import (
    mock_config_entry,
    patch_async_ble_device_from_address,
    patch_async_register_callback,
    patch_melnor_device,
)


async def test_manual_watering_minutes(menuai: menuai) -> None:
    """Test the manual watering duration number."""

    entry = mock_config_entry(menuai)

    with (
        patch_async_ble_device_from_address(),
        patch_melnor_device() as device_patch,
        patch_async_register_callback(),
    ):
        device = device_patch.return_value

        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

        number = menuai.states.get("number.zone_1_manual_duration")

        assert number is not None
        assert number.state == "0"
        assert number.attributes["max"] == 360
        assert number.attributes["min"] == 1
        assert number.attributes["step"] == 1.0

        assert device.zone1.manual_watering_minutes == 0

        await menuai.services.async_call(
            "number",
            "set_value",
            {"entity_id": "number.zone_1_manual_duration", "value": 10},
            blocking=True,
        )

        number = menuai.states.get("number.zone_1_manual_duration")

        assert number is not None
        assert number.state == "10"
        assert device.zone1.manual_watering_minutes == 10


async def test_frequency_interval_hours(menuai: menuai) -> None:
    """Test the interval hours number."""

    entry = mock_config_entry(menuai)

    with (
        patch_async_ble_device_from_address(),
        patch_melnor_device() as device_patch,
        patch_async_register_callback(),
    ):
        device = device_patch.return_value

        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

        number = menuai.states.get("number.zone_1_schedule_interval")

        assert number is not None
        assert number.state == "0"
        assert number.attributes["max"] == 168
        assert number.attributes["min"] == 1
        assert number.attributes["step"] == 1.0

        assert device.zone1.frequency.interval_hours == 0

        await menuai.services.async_call(
            "number",
            "set_value",
            {"entity_id": "number.zone_1_schedule_interval", "value": 10},
            blocking=True,
        )

        number = menuai.states.get("number.zone_1_schedule_interval")

        assert number is not None
        assert number.state == "10"
        assert device.zone1.frequency.interval_hours == 10


async def test_frequency_duration_minutes(menuai: menuai) -> None:
    """Test the duration minutes number."""

    entry = mock_config_entry(menuai)

    with (
        patch_async_ble_device_from_address(),
        patch_melnor_device() as device_patch,
        patch_async_register_callback(),
    ):
        device = device_patch.return_value

        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

        number = menuai.states.get("number.zone_1_schedule_duration")

        assert number is not None
        assert number.state == "0"
        assert number.attributes["max"] == 360
        assert number.attributes["min"] == 1
        assert number.attributes["step"] == 1.0

        assert device.zone1.frequency.duration_minutes == 0

        await menuai.services.async_call(
            "number",
            "set_value",
            {"entity_id": "number.zone_1_schedule_duration", "value": 10},
            blocking=True,
        )

        number = menuai.states.get("number.zone_1_schedule_duration")

        assert number is not None
        assert number.state == "10"
        assert device.zone1.frequency.duration_minutes == 10
