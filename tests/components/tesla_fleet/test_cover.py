"""Test the Teslemetry cover platform."""

from unittest.mock import AsyncMock, patch

import pytest
from syrupy.assertion import SnapshotAssertion
from tesla_fleet_api.exceptions import VehicleOffline

from menuai.components.cover import (
    DOMAIN as COVER_DOMAIN,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    SERVICE_STOP_COVER,
    CoverState,
)
from menuai.const import ATTR_ENTITY_ID, STATE_UNKNOWN, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import assert_entities, setup_platform
from .const import COMMAND_OK, VEHICLE_DATA_ALT

from tests.common import MockConfigEntry


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_cover(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    normal_config_entry: MockConfigEntry,
) -> None:
    """Tests that the cover entities are correct."""

    await setup_platform(menuai, normal_config_entry, [Platform.COVER])
    assert_entities(menuai, normal_config_entry.entry_id, entity_registry, snapshot)


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_cover_alt(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_vehicle_data: AsyncMock,
    normal_config_entry: MockConfigEntry,
) -> None:
    """Tests that the cover entities are correct with alternate values."""

    mock_vehicle_data.return_value = VEHICLE_DATA_ALT
    await setup_platform(menuai, normal_config_entry, [Platform.COVER])
    assert_entities(menuai, normal_config_entry.entry_id, entity_registry, snapshot)


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_cover_readonly(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    readonly_config_entry: MockConfigEntry,
) -> None:
    """Tests that the cover entities are correct without scopes."""

    await setup_platform(menuai, readonly_config_entry, [Platform.COVER])
    assert_entities(menuai, readonly_config_entry.entry_id, entity_registry, snapshot)


async def test_cover_offline(
    menuai: menuai,
    mock_vehicle_data: AsyncMock,
    normal_config_entry: MockConfigEntry,
) -> None:
    """Tests that the cover entities are correct when offline."""

    mock_vehicle_data.side_effect = VehicleOffline
    await setup_platform(menuai, normal_config_entry, [Platform.COVER])
    state = menuai.states.get("cover.test_windows")
    assert state.state == STATE_UNKNOWN


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_cover_services(
    menuai: menuai,
    normal_config_entry: MockConfigEntry,
) -> None:
    """Tests that the cover entities are correct."""

    await setup_platform(menuai, normal_config_entry, [Platform.COVER])

    # Vent Windows
    entity_id = "cover.test_windows"
    with patch(
        "tesla_fleet_api.tesla.VehicleFleet.window_control",
        return_value=COMMAND_OK,
    ) as call:
        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_OPEN_COVER,
            {ATTR_ENTITY_ID: [entity_id]},
            blocking=True,
        )
        call.assert_called_once()
        state = menuai.states.get(entity_id)
        assert state
        assert state.state == CoverState.OPEN

        call.reset_mock()
        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_CLOSE_COVER,
            {ATTR_ENTITY_ID: ["cover.test_windows"]},
            blocking=True,
        )
        call.assert_called_once()
        state = menuai.states.get(entity_id)
        assert state
        assert state.state == CoverState.CLOSED

    # Charge Port Door
    entity_id = "cover.test_charge_port_door"
    with patch(
        "tesla_fleet_api.tesla.VehicleFleet.charge_port_door_open",
        return_value=COMMAND_OK,
    ) as call:
        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_OPEN_COVER,
            {ATTR_ENTITY_ID: [entity_id]},
            blocking=True,
        )
        call.assert_called_once()
        state = menuai.states.get(entity_id)
        assert state
        assert state.state == CoverState.OPEN

    with patch(
        "tesla_fleet_api.tesla.VehicleFleet.charge_port_door_close",
        return_value=COMMAND_OK,
    ) as call:
        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_CLOSE_COVER,
            {ATTR_ENTITY_ID: [entity_id]},
            blocking=True,
        )
        call.assert_called_once()
        state = menuai.states.get(entity_id)
        assert state
        assert state.state == CoverState.CLOSED

    # Frunk
    entity_id = "cover.test_frunk"
    with patch(
        "tesla_fleet_api.tesla.VehicleFleet.actuate_trunk",
        return_value=COMMAND_OK,
    ) as call:
        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_OPEN_COVER,
            {ATTR_ENTITY_ID: [entity_id]},
            blocking=True,
        )
        call.assert_called_once()
        state = menuai.states.get(entity_id)
        assert state
        assert state.state == CoverState.OPEN

    # Trunk
    entity_id = "cover.test_trunk"
    with patch(
        "tesla_fleet_api.tesla.VehicleFleet.actuate_trunk",
        return_value=COMMAND_OK,
    ) as call:
        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_OPEN_COVER,
            {ATTR_ENTITY_ID: [entity_id]},
            blocking=True,
        )
        call.assert_called_once()
        state = menuai.states.get(entity_id)
        assert state
        assert state.state == CoverState.OPEN

        call.reset_mock()
        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_CLOSE_COVER,
            {ATTR_ENTITY_ID: [entity_id]},
            blocking=True,
        )
        call.assert_called_once()
        state = menuai.states.get(entity_id)
        assert state
        assert state.state == CoverState.CLOSED

    # Sunroof
    entity_id = "cover.test_sunroof"
    with patch(
        "tesla_fleet_api.tesla.VehicleFleet.sun_roof_control",
        return_value=COMMAND_OK,
    ) as call:
        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_OPEN_COVER,
            {ATTR_ENTITY_ID: [entity_id]},
            blocking=True,
        )
        call.assert_called_once()
        state = menuai.states.get(entity_id)
        assert state
        assert state.state == CoverState.OPEN

        call.reset_mock()
        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_STOP_COVER,
            {ATTR_ENTITY_ID: [entity_id]},
            blocking=True,
        )
        call.assert_called_once()
        state = menuai.states.get(entity_id)
        assert state
        assert state.state == CoverState.OPEN

        call.reset_mock()
        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_CLOSE_COVER,
            {ATTR_ENTITY_ID: [entity_id]},
            blocking=True,
        )
        call.assert_called_once()
        state = menuai.states.get(entity_id)
        assert state
        assert state.state == CoverState.CLOSED
