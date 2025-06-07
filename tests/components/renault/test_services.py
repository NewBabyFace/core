"""Tests for Renault sensors."""

from collections.abc import Generator
from datetime import datetime
from unittest.mock import patch

import pytest
from renault_api.exceptions import RenaultException
from renault_api.kamereon import schemas
from renault_api.kamereon.models import ChargeSchedule, HvacSchedule
from syrupy.assertion import SnapshotAssertion

from menuai.components.renault.const import DOMAIN
from menuai.components.renault.services import (
    ATTR_SCHEDULES,
    ATTR_TEMPERATURE,
    ATTR_VEHICLE,
    ATTR_WHEN,
    SERVICE_AC_CANCEL,
    SERVICE_AC_SET_SCHEDULES,
    SERVICE_AC_START,
    SERVICE_CHARGE_SET_SCHEDULES,
)
from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.exceptions import menuaiError, ServiceValidationError
from menuai.helpers import device_registry as dr

from tests.common import async_load_fixture

pytestmark = pytest.mark.usefixtures("patch_renault_account", "patch_get_vehicles")


@pytest.fixture(autouse=True)
def override_platforms() -> Generator[None]:
    """Override PLATFORMS."""
    with patch("menuai.components.renault.PLATFORMS", []):
        yield


@pytest.fixture(autouse=True, name="vehicle_type", params=["zoe_40"])
def override_vehicle_type(request: pytest.FixtureRequest) -> str:
    """Parametrize vehicle type."""
    return request.param


def get_device_id(menuai: menuai) -> str:
    """Get device_id."""
    device_registry = dr.async_get(menuai)
    identifiers = {(DOMAIN, "VF1ZOE40VIN")}
    device = device_registry.async_get_device(identifiers=identifiers)
    return device.id


async def test_service_set_ac_cancel(
    menuai: menuai, config_entry: ConfigEntry
) -> None:
    """Test that service invokes renault_api with correct data."""
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    data = {
        ATTR_VEHICLE: get_device_id(menuai),
    }

    with patch(
        "renault_api.renault_vehicle.RenaultVehicle.set_ac_stop",
        return_value=(
            schemas.KamereonVehicleHvacStartActionDataSchema.loads(
                await async_load_fixture(menuai, "action.set_ac_stop.json", DOMAIN)
            )
        ),
    ) as mock_action:
        await menuai.services.async_call(
            DOMAIN, SERVICE_AC_CANCEL, service_data=data, blocking=True
        )
    assert len(mock_action.mock_calls) == 1
    assert mock_action.mock_calls[0][1] == ()


async def test_service_set_ac_start_simple(
    menuai: menuai, config_entry: ConfigEntry
) -> None:
    """Test that service invokes renault_api with correct data."""
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    temperature = 13.5
    data = {
        ATTR_VEHICLE: get_device_id(menuai),
        ATTR_TEMPERATURE: temperature,
    }

    with patch(
        "renault_api.renault_vehicle.RenaultVehicle.set_ac_start",
        return_value=(
            schemas.KamereonVehicleHvacStartActionDataSchema.loads(
                await async_load_fixture(menuai, "action.set_ac_start.json", DOMAIN)
            )
        ),
    ) as mock_action:
        await menuai.services.async_call(
            DOMAIN, SERVICE_AC_START, service_data=data, blocking=True
        )
    assert len(mock_action.mock_calls) == 1
    assert mock_action.mock_calls[0][1] == (temperature, None)


async def test_service_set_ac_start_with_date(
    menuai: menuai, config_entry: ConfigEntry
) -> None:
    """Test that service invokes renault_api with correct data."""
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    temperature = 13.5
    when = datetime(2025, 8, 23, 17, 12, 45)
    data = {
        ATTR_VEHICLE: get_device_id(menuai),
        ATTR_TEMPERATURE: temperature,
        ATTR_WHEN: when,
    }

    with patch(
        "renault_api.renault_vehicle.RenaultVehicle.set_ac_start",
        return_value=(
            schemas.KamereonVehicleHvacStartActionDataSchema.loads(
                await async_load_fixture(menuai, "action.set_ac_start.json", DOMAIN)
            )
        ),
    ) as mock_action:
        await menuai.services.async_call(
            DOMAIN, SERVICE_AC_START, service_data=data, blocking=True
        )
    assert len(mock_action.mock_calls) == 1
    assert mock_action.mock_calls[0][1] == (temperature, when)


async def test_service_set_charge_schedule(
    menuai: menuai, config_entry: ConfigEntry, snapshot: SnapshotAssertion
) -> None:
    """Test that service invokes renault_api with correct data."""
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    schedules = {"id": 2}
    data = {
        ATTR_VEHICLE: get_device_id(menuai),
        ATTR_SCHEDULES: schedules,
    }

    with (
        patch("renault_api.renault_vehicle.RenaultVehicle.get_full_endpoint"),
        patch(
            "renault_api.renault_vehicle.RenaultVehicle.http_get",
            return_value=schemas.KamereonResponseSchema.loads(
                await async_load_fixture(menuai, "charging_settings.json", DOMAIN)
            ),
        ),
        patch(
            "renault_api.renault_vehicle.RenaultVehicle.set_charge_schedules",
            return_value=(
                schemas.KamereonVehicleHvacStartActionDataSchema.loads(
                    await async_load_fixture(
                        menuai, "action.set_charge_schedules.json", DOMAIN
                    )
                )
            ),
        ) as mock_action,
    ):
        await menuai.services.async_call(
            DOMAIN, SERVICE_CHARGE_SET_SCHEDULES, service_data=data, blocking=True
        )
    assert len(mock_action.mock_calls) == 1
    mock_call_data: list[ChargeSchedule] = mock_action.mock_calls[0][1][0]
    assert mock_call_data == snapshot


async def test_service_set_charge_schedule_multi(
    menuai: menuai, config_entry: ConfigEntry, snapshot: SnapshotAssertion
) -> None:
    """Test that service invokes renault_api with correct data."""
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    schedules = [
        {
            "id": 2,
            "activated": True,
            "monday": {"startTime": "T12:00Z", "duration": 30},
            "tuesday": {"startTime": "T12:00Z", "duration": 30},
            "wednesday": None,
            "friday": {"startTime": "T12:00Z", "duration": 30},
            "saturday": {"startTime": "T12:00Z", "duration": 30},
            "sunday": {"startTime": "T12:00Z", "duration": 30},
        },
        {"id": 3},
    ]
    data = {
        ATTR_VEHICLE: get_device_id(menuai),
        ATTR_SCHEDULES: schedules,
    }

    with (
        patch("renault_api.renault_vehicle.RenaultVehicle.get_full_endpoint"),
        patch(
            "renault_api.renault_vehicle.RenaultVehicle.http_get",
            return_value=schemas.KamereonResponseSchema.loads(
                await async_load_fixture(menuai, "charging_settings.json", DOMAIN)
            ),
        ),
        patch(
            "renault_api.renault_vehicle.RenaultVehicle.set_charge_schedules",
            return_value=(
                schemas.KamereonVehicleHvacStartActionDataSchema.loads(
                    await async_load_fixture(
                        menuai, "action.set_charge_schedules.json", DOMAIN
                    )
                )
            ),
        ) as mock_action,
    ):
        await menuai.services.async_call(
            DOMAIN, SERVICE_CHARGE_SET_SCHEDULES, service_data=data, blocking=True
        )
    assert len(mock_action.mock_calls) == 1
    mock_call_data: list[ChargeSchedule] = mock_action.mock_calls[0][1][0]
    assert mock_call_data == snapshot

    # Monday updated with new values
    assert mock_call_data[1].monday.startTime == "T12:00Z"
    assert mock_call_data[1].monday.duration == 30
    # Wednesday has original values cleared
    assert mock_call_data[1].wednesday is None
    # Thursday keeps original values
    assert mock_call_data[1].thursday.startTime == "T23:30Z"
    assert mock_call_data[1].thursday.duration == 15


async def test_service_set_ac_schedule(
    menuai: menuai, config_entry: ConfigEntry, snapshot: SnapshotAssertion
) -> None:
    """Test that service invokes renault_api with correct data."""
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    schedules = {"id": 2}
    data = {
        ATTR_VEHICLE: get_device_id(menuai),
        ATTR_SCHEDULES: schedules,
    }

    with (
        patch(
            "renault_api.renault_vehicle.RenaultVehicle.get_hvac_settings",
            return_value=schemas.KamereonVehicleDataResponseSchema.loads(
                await async_load_fixture(menuai, "hvac_settings.json", DOMAIN)
            ).get_attributes(schemas.KamereonVehicleHvacSettingsDataSchema),
        ),
        patch(
            "renault_api.renault_vehicle.RenaultVehicle.set_hvac_schedules",
            return_value=(
                schemas.KamereonVehicleHvacScheduleActionDataSchema.loads(
                    await async_load_fixture(
                        menuai, "action.set_ac_schedules.json", DOMAIN
                    )
                )
            ),
        ) as mock_action,
    ):
        await menuai.services.async_call(
            DOMAIN, SERVICE_AC_SET_SCHEDULES, service_data=data, blocking=True
        )
    assert len(mock_action.mock_calls) == 1
    mock_call_data: list[ChargeSchedule] = mock_action.mock_calls[0][1][0]
    assert mock_call_data == snapshot


async def test_service_set_ac_schedule_multi(
    menuai: menuai, config_entry: ConfigEntry, snapshot: SnapshotAssertion
) -> None:
    """Test that service invokes renault_api with correct data."""
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    schedules = [
        {
            "id": 3,
            "activated": True,
            "monday": {"readyAtTime": "T12:00Z"},
            "tuesday": {"readyAtTime": "T12:00Z"},
            "wednesday": None,
            "friday": {"readyAtTime": "T12:00Z"},
            "saturday": {"readyAtTime": "T12:00Z"},
            "sunday": {"readyAtTime": "T12:00Z"},
        },
        {"id": 4},
    ]
    data = {
        ATTR_VEHICLE: get_device_id(menuai),
        ATTR_SCHEDULES: schedules,
    }

    with (
        patch(
            "renault_api.renault_vehicle.RenaultVehicle.get_hvac_settings",
            return_value=schemas.KamereonVehicleDataResponseSchema.loads(
                await async_load_fixture(menuai, "hvac_settings.json", DOMAIN)
            ).get_attributes(schemas.KamereonVehicleHvacSettingsDataSchema),
        ),
        patch(
            "renault_api.renault_vehicle.RenaultVehicle.set_hvac_schedules",
            return_value=(
                schemas.KamereonVehicleHvacScheduleActionDataSchema.loads(
                    await async_load_fixture(
                        menuai, "action.set_ac_schedules.json", DOMAIN
                    )
                )
            ),
        ) as mock_action,
    ):
        await menuai.services.async_call(
            DOMAIN, SERVICE_AC_SET_SCHEDULES, service_data=data, blocking=True
        )
    assert len(mock_action.mock_calls) == 1
    mock_call_data: list[HvacSchedule] = mock_action.mock_calls[0][1][0]
    assert mock_call_data == snapshot

    # Schedule is activated now
    assert mock_call_data[2].activated is True
    # Monday updated with new values
    assert mock_call_data[2].monday.readyAtTime == "T12:00Z"
    # Wednesday has original values cleared
    assert mock_call_data[2].wednesday is None
    # Thursday keeps original values
    assert mock_call_data[2].thursday.readyAtTime == "T23:30Z"


async def test_service_invalid_device_id(
    menuai: menuai, config_entry: ConfigEntry
) -> None:
    """Test that service fails if device_id not found in registry."""
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    data = {ATTR_VEHICLE: "some_random_id"}

    with pytest.raises(ServiceValidationError) as err:
        await menuai.services.async_call(
            DOMAIN, SERVICE_AC_CANCEL, service_data=data, blocking=True
        )
    assert err.value.translation_key == "invalid_device_id"
    assert err.value.translation_placeholders == {"device_id": "some_random_id"}


async def test_service_invalid_device_id2(
    menuai: menuai, device_registry: dr.DeviceRegistry, config_entry: ConfigEntry
) -> None:
    """Test that service fails if device_id not available in the hub."""
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    # Create a fake second vehicle in the device registry, but
    # not initialised by the hub.
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, "VF1AAAAA111222333")},
        name="REG-NUMBER",
    )
    device_id = device_registry.async_get_device(
        identifiers={(DOMAIN, "VF1AAAAA111222333")},
    ).id

    data = {ATTR_VEHICLE: device_id}

    with pytest.raises(ServiceValidationError) as err:
        await menuai.services.async_call(
            DOMAIN, SERVICE_AC_CANCEL, service_data=data, blocking=True
        )
    assert err.value.translation_key == "no_config_entry_for_device"
    assert err.value.translation_placeholders == {"device_id": "REG-NUMBER"}


async def test_service_exception(
    menuai: menuai, config_entry: ConfigEntry
) -> None:
    """Test that service invokes renault_api with correct data."""
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    data = {
        ATTR_VEHICLE: get_device_id(menuai),
    }

    with (
        patch(
            "renault_api.renault_vehicle.RenaultVehicle.set_ac_stop",
            side_effect=RenaultException("Didn't work"),
        ) as mock_action,
        pytest.raises(menuaiError, match="Didn't work"),
    ):
        await menuai.services.async_call(
            DOMAIN, SERVICE_AC_CANCEL, service_data=data, blocking=True
        )
    assert len(mock_action.mock_calls) == 1
    assert mock_action.mock_calls[0][1] == ()
