"""Tests for the climate module."""

from unittest.mock import AsyncMock, MagicMock, patch

from eheimdigital.heater import EheimDigitalHeater
from eheimdigital.types import (
    EheimDeviceType,
    EheimDigitalClientError,
    HeaterMode,
    HeaterUnit,
)
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.climate import (
    ATTR_HVAC_MODE,
    ATTR_PRESET_MODE,
    DOMAIN as CLIMATE_DOMAIN,
    PRESET_NONE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
    SERVICE_SET_TEMPERATURE,
    HVACAction,
    HVACMode,
)
from menuai.components.eheimdigital.const import (
    HEATER_BIO_MODE,
    HEATER_SMART_MODE,
)
from menuai.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE, Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from .conftest import init_integration

from tests.common import MockConfigEntry, snapshot_platform


@pytest.mark.usefixtures("heater_mock")
async def test_setup_heater(
    menuai: menuai,
    eheimdigital_hub_mock: MagicMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test climate platform setup for heater."""
    mock_config_entry.add_to_menuai(menuai)

    with (
        patch("menuai.components.eheimdigital.PLATFORMS", [Platform.CLIMATE]),
        patch(
            "menuai.components.eheimdigital.coordinator.asyncio.Event",
            new=AsyncMock,
        ),
    ):
        await menuai.config_entries.async_setup(mock_config_entry.entry_id)

    await eheimdigital_hub_mock.call_args.kwargs["device_found_callback"](
        "00:00:00:00:00:02", EheimDeviceType.VERSION_EHEIM_EXT_HEATER
    )
    await menuai.async_block_till_done()

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_dynamic_new_devices(
    menuai: menuai,
    eheimdigital_hub_mock: MagicMock,
    heater_mock: EheimDigitalHeater,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test light platform setup with at first no devices and dynamically adding a device."""
    mock_config_entry.add_to_menuai(menuai)

    eheimdigital_hub_mock.return_value.devices = {}

    with (
        patch("menuai.components.eheimdigital.PLATFORMS", [Platform.CLIMATE]),
        patch(
            "menuai.components.eheimdigital.coordinator.asyncio.Event",
            new=AsyncMock,
        ),
    ):
        await menuai.config_entries.async_setup(mock_config_entry.entry_id)

    assert (
        len(
            entity_registry.entities.get_entries_for_config_entry_id(
                mock_config_entry.entry_id
            )
        )
        == 0
    )

    eheimdigital_hub_mock.return_value.devices = {"00:00:00:00:00:02": heater_mock}

    await eheimdigital_hub_mock.call_args.kwargs["device_found_callback"](
        "00:00:00:00:00:02", EheimDeviceType.VERSION_EHEIM_EXT_HEATER
    )
    await menuai.async_block_till_done()

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.parametrize(
    ("preset_mode", "heater_mode"),
    [
        (PRESET_NONE, HeaterMode.MANUAL),
        (HEATER_BIO_MODE, HeaterMode.BIO),
        (HEATER_SMART_MODE, HeaterMode.SMART),
    ],
)
async def test_set_preset_mode(
    menuai: menuai,
    eheimdigital_hub_mock: MagicMock,
    heater_mock: EheimDigitalHeater,
    mock_config_entry: MockConfigEntry,
    preset_mode: str,
    heater_mode: HeaterMode,
) -> None:
    """Test setting a preset mode."""
    await init_integration(menuai, mock_config_entry)

    await eheimdigital_hub_mock.call_args.kwargs["device_found_callback"](
        "00:00:00:00:00:02", EheimDeviceType.VERSION_EHEIM_EXT_HEATER
    )
    await menuai.async_block_till_done()

    heater_mock.hub.send_packet.side_effect = EheimDigitalClientError

    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_PRESET_MODE,
            {ATTR_ENTITY_ID: "climate.mock_heater", ATTR_PRESET_MODE: preset_mode},
            blocking=True,
        )

    heater_mock.hub.send_packet.side_effect = None

    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: "climate.mock_heater", ATTR_PRESET_MODE: preset_mode},
        blocking=True,
    )

    calls = [call for call in heater_mock.hub.mock_calls if call[0] == "send_packet"]
    assert len(calls) == 2 and calls[1][1][0]["mode"] == int(heater_mode)


async def test_set_temperature(
    menuai: menuai,
    eheimdigital_hub_mock: MagicMock,
    heater_mock: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setting a preset mode."""
    await init_integration(menuai, mock_config_entry)

    await eheimdigital_hub_mock.call_args.kwargs["device_found_callback"](
        "00:00:00:00:00:02", EheimDeviceType.VERSION_EHEIM_EXT_HEATER
    )
    await menuai.async_block_till_done()

    heater_mock.hub.send_packet.side_effect = EheimDigitalClientError

    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {ATTR_ENTITY_ID: "climate.mock_heater", ATTR_TEMPERATURE: 26.0},
            blocking=True,
        )

    heater_mock.hub.send_packet.side_effect = None

    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: "climate.mock_heater", ATTR_TEMPERATURE: 26.0},
        blocking=True,
    )

    calls = [call for call in heater_mock.hub.mock_calls if call[0] == "send_packet"]
    assert len(calls) == 2 and calls[1][1][0]["sollTemp"] == 260


@pytest.mark.parametrize(
    ("hvac_mode", "active"), [(HVACMode.AUTO, True), (HVACMode.OFF, False)]
)
async def test_set_hvac_mode(
    menuai: menuai,
    eheimdigital_hub_mock: MagicMock,
    heater_mock: MagicMock,
    mock_config_entry: MockConfigEntry,
    hvac_mode: HVACMode,
    active: bool,
) -> None:
    """Test setting a preset mode."""
    await init_integration(menuai, mock_config_entry)

    await eheimdigital_hub_mock.call_args.kwargs["device_found_callback"](
        "00:00:00:00:00:02", EheimDeviceType.VERSION_EHEIM_EXT_HEATER
    )
    await menuai.async_block_till_done()

    heater_mock.hub.send_packet.side_effect = EheimDigitalClientError

    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            {ATTR_ENTITY_ID: "climate.mock_heater", ATTR_HVAC_MODE: hvac_mode},
            blocking=True,
        )

    heater_mock.hub.send_packet.side_effect = None

    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: "climate.mock_heater", ATTR_HVAC_MODE: hvac_mode},
        blocking=True,
    )

    calls = [call for call in heater_mock.hub.mock_calls if call[0] == "send_packet"]
    assert len(calls) == 2 and calls[1][1][0]["active"] == int(active)


async def test_state_update(
    menuai: menuai,
    eheimdigital_hub_mock: MagicMock,
    mock_config_entry: MockConfigEntry,
    heater_mock: EheimDigitalHeater,
) -> None:
    """Test the climate state update."""
    heater_mock.heater_data["mUnit"] = int(HeaterUnit.FAHRENHEIT)
    heater_mock.heater_data["isHeating"] = int(False)
    heater_mock.heater_data["mode"] = int(HeaterMode.BIO)

    await init_integration(menuai, mock_config_entry)

    await eheimdigital_hub_mock.call_args.kwargs["device_found_callback"](
        "00:00:00:00:00:02", EheimDeviceType.VERSION_EHEIM_EXT_HEATER
    )
    await menuai.async_block_till_done()

    assert (state := menuai.states.get("climate.mock_heater"))

    assert state.attributes["hvac_action"] == HVACAction.IDLE
    assert state.attributes["preset_mode"] == HEATER_BIO_MODE

    heater_mock.heater_data["active"] = int(False)
    heater_mock.heater_data["mode"] = int(HeaterMode.SMART)

    await eheimdigital_hub_mock.call_args.kwargs["receive_callback"]()

    assert (state := menuai.states.get("climate.mock_heater"))
    assert state.state == HVACMode.OFF
    assert state.attributes["preset_mode"] == HEATER_SMART_MODE
