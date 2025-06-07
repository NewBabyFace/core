"""Tests for Shelly binary sensor platform."""

from copy import deepcopy
from unittest.mock import Mock

from aioshelly.const import MODEL_BLU_GATEWAY_G3, MODEL_MOTION
from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from menuai.components.shelly.const import UPDATE_PERIOD_MULTIPLIER
from menuai.const import STATE_OFF, STATE_ON, STATE_UNKNOWN
from menuai.core import menuai, State
from menuai.helpers.device_registry import DeviceRegistry
from menuai.helpers.entity_registry import EntityRegistry

from . import (
    init_integration,
    mock_rest_update,
    mutate_rpc_device_status,
    register_device,
    register_entity,
)

from tests.common import mock_restore_cache

RELAY_BLOCK_ID = 0
SENSOR_BLOCK_ID = 3


async def test_block_binary_sensor(
    menuai: menuai,
    mock_block_device: Mock,
    monkeypatch: pytest.MonkeyPatch,
    entity_registry: EntityRegistry,
) -> None:
    """Test block binary sensor."""
    monkeypatch.setitem(mock_block_device.shelly, "num_outputs", 1)
    entity_id = f"{BINARY_SENSOR_DOMAIN}.test_name_overpowering"
    await init_integration(menuai, 1)

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_OFF

    monkeypatch.setattr(mock_block_device.blocks[RELAY_BLOCK_ID], "overpower", 1)
    mock_block_device.mock_update()

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_ON

    assert (entry := entity_registry.async_get(entity_id))
    assert entry.unique_id == "123456789ABC-relay_0-overpower"


async def test_block_binary_sensor_extra_state_attr(
    menuai: menuai,
    mock_block_device: Mock,
    monkeypatch: pytest.MonkeyPatch,
    entity_registry: EntityRegistry,
) -> None:
    """Test block binary sensor extra state attributes."""
    entity_id = f"{BINARY_SENSOR_DOMAIN}.test_name_gas"
    await init_integration(menuai, 1)

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_ON
    assert state.attributes.get("detected") == "mild"

    monkeypatch.setattr(mock_block_device.blocks[SENSOR_BLOCK_ID], "gas", "none")
    mock_block_device.mock_update()

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_OFF
    assert state.attributes.get("detected") == "none"

    assert (entry := entity_registry.async_get(entity_id))
    assert entry.unique_id == "123456789ABC-sensor_0-gas"


async def test_block_rest_binary_sensor(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    mock_block_device: Mock,
    monkeypatch: pytest.MonkeyPatch,
    entity_registry: EntityRegistry,
) -> None:
    """Test block REST binary sensor."""
    entity_id = register_entity(menuai, BINARY_SENSOR_DOMAIN, "test_name_cloud", "cloud")
    monkeypatch.setitem(mock_block_device.status, "cloud", {"connected": False})
    await init_integration(menuai, 1)

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_OFF

    monkeypatch.setitem(mock_block_device.status["cloud"], "connected", True)
    await mock_rest_update(menuai, freezer)

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_ON

    assert (entry := entity_registry.async_get(entity_id))
    assert entry.unique_id == "123456789ABC-cloud"


async def test_block_rest_binary_sensor_connected_battery_devices(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    mock_block_device: Mock,
    monkeypatch: pytest.MonkeyPatch,
    entity_registry: EntityRegistry,
) -> None:
    """Test block REST binary sensor for connected battery devices."""
    entity_id = register_entity(menuai, BINARY_SENSOR_DOMAIN, "test_name_cloud", "cloud")
    monkeypatch.setitem(mock_block_device.status, "cloud", {"connected": False})
    monkeypatch.setitem(mock_block_device.settings["device"], "type", MODEL_MOTION)
    monkeypatch.setitem(mock_block_device.settings["coiot"], "update_period", 3600)
    await init_integration(menuai, 1, model=MODEL_MOTION)

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_OFF

    monkeypatch.setitem(mock_block_device.status["cloud"], "connected", True)

    # Verify no update on fast intervals
    await mock_rest_update(menuai, freezer)
    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_OFF

    # Verify update on slow intervals
    await mock_rest_update(menuai, freezer, seconds=UPDATE_PERIOD_MULTIPLIER * 3600)
    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_ON

    assert (entry := entity_registry.async_get(entity_id))
    assert entry.unique_id == "123456789ABC-cloud"


async def test_block_sleeping_binary_sensor(
    menuai: menuai,
    mock_block_device: Mock,
    monkeypatch: pytest.MonkeyPatch,
    entity_registry: EntityRegistry,
) -> None:
    """Test block sleeping binary sensor."""
    entity_id = f"{BINARY_SENSOR_DOMAIN}.test_name_motion"
    await init_integration(menuai, 1, sleep_period=1000)

    # Sensor should be created when device is online
    assert menuai.states.get(entity_id) is None

    # Make device online
    mock_block_device.mock_online()
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_OFF

    monkeypatch.setattr(mock_block_device.blocks[SENSOR_BLOCK_ID], "motion", 1)
    mock_block_device.mock_update()

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_ON

    assert (entry := entity_registry.async_get(entity_id))
    assert entry.unique_id == "123456789ABC-sensor_0-motion"


async def test_block_restored_sleeping_binary_sensor(
    menuai: menuai,
    mock_block_device: Mock,
    device_registry: DeviceRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test block restored sleeping binary sensor."""
    entry = await init_integration(menuai, 1, sleep_period=1000, skip_setup=True)
    device = register_device(device_registry, entry)
    entity_id = register_entity(
        menuai,
        BINARY_SENSOR_DOMAIN,
        "test_name_motion",
        "sensor_0-motion",
        entry,
        device_id=device.id,
    )
    mock_restore_cache(menuai, [State(entity_id, STATE_ON)])
    monkeypatch.setattr(mock_block_device, "initialized", False)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_ON

    # Make device online
    monkeypatch.setattr(mock_block_device, "initialized", True)
    mock_block_device.mock_online()
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_OFF


async def test_block_restored_sleeping_binary_sensor_no_last_state(
    menuai: menuai,
    mock_block_device: Mock,
    device_registry: DeviceRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test block restored sleeping binary sensor missing last state."""
    entry = await init_integration(menuai, 1, sleep_period=1000, skip_setup=True)
    device = register_device(device_registry, entry)
    entity_id = register_entity(
        menuai,
        BINARY_SENSOR_DOMAIN,
        "test_name_motion",
        "sensor_0-motion",
        entry,
        device_id=device.id,
    )
    monkeypatch.setattr(mock_block_device, "initialized", False)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_UNKNOWN

    # Make device online
    monkeypatch.setattr(mock_block_device, "initialized", True)
    mock_block_device.mock_online()
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_OFF


async def test_rpc_binary_sensor(
    menuai: menuai,
    mock_rpc_device: Mock,
    monkeypatch: pytest.MonkeyPatch,
    entity_registry: EntityRegistry,
) -> None:
    """Test RPC binary sensor."""
    entity_id = f"{BINARY_SENSOR_DOMAIN}.test_name_test_cover_0_overpowering"
    await init_integration(menuai, 2)

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_OFF

    mutate_rpc_device_status(
        monkeypatch, mock_rpc_device, "cover:0", "errors", "overpower"
    )
    mock_rpc_device.mock_update()

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_ON

    assert (entry := entity_registry.async_get(entity_id))
    assert entry.unique_id == "123456789ABC-cover:0-overpower"


async def test_rpc_binary_sensor_removal(
    menuai: menuai,
    mock_rpc_device: Mock,
    monkeypatch: pytest.MonkeyPatch,
    entity_registry: EntityRegistry,
) -> None:
    """Test RPC binary sensor is removed due to removal_condition."""
    entity_id = register_entity(
        menuai, BINARY_SENSOR_DOMAIN, "test_cover_0_input", "input:0-input"
    )

    assert entity_registry.async_get(entity_id) is not None

    monkeypatch.setattr(mock_rpc_device, "status", {"input:0": {"state": False}})
    await init_integration(menuai, 2)

    assert entity_registry.async_get(entity_id) is None


async def test_rpc_sleeping_binary_sensor(
    menuai: menuai,
    mock_rpc_device: Mock,
    monkeypatch: pytest.MonkeyPatch,
    entity_registry: EntityRegistry,
) -> None:
    """Test RPC online sleeping binary sensor."""
    entity_id = f"{BINARY_SENSOR_DOMAIN}.test_name_cloud"
    monkeypatch.setattr(mock_rpc_device, "connected", False)
    monkeypatch.setitem(mock_rpc_device.status["sys"], "wakeup_period", 1000)
    config_entry = await init_integration(menuai, 2, sleep_period=1000)

    # Sensor should be created when device is online
    assert menuai.states.get(entity_id) is None

    register_entity(
        menuai, BINARY_SENSOR_DOMAIN, "test_name_cloud", "cloud-cloud", config_entry
    )

    # Make device online
    mock_rpc_device.mock_online()
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_OFF

    mutate_rpc_device_status(monkeypatch, mock_rpc_device, "cloud", "connected", True)
    mock_rpc_device.mock_update()

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_ON

    # test external power sensor
    assert (state := menuai.states.get("binary_sensor.test_name_external_power"))
    assert state.state == STATE_ON

    assert (
        entry := entity_registry.async_get("binary_sensor.test_name_external_power")
    )
    assert entry.unique_id == "123456789ABC-devicepower:0-external_power"


async def test_rpc_restored_sleeping_binary_sensor(
    menuai: menuai,
    mock_rpc_device: Mock,
    device_registry: DeviceRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test RPC restored binary sensor."""
    entry = await init_integration(menuai, 2, sleep_period=1000, skip_setup=True)
    device = register_device(device_registry, entry)
    entity_id = register_entity(
        menuai,
        BINARY_SENSOR_DOMAIN,
        "test_name_cloud",
        "cloud-cloud",
        entry,
        device_id=device.id,
    )

    mock_restore_cache(menuai, [State(entity_id, STATE_ON)])
    monkeypatch.setattr(mock_rpc_device, "initialized", False)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_ON

    # Make device online
    monkeypatch.setattr(mock_rpc_device, "initialized", True)
    mock_rpc_device.mock_update()
    await menuai.async_block_till_done()

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_OFF


async def test_rpc_restored_sleeping_binary_sensor_no_last_state(
    menuai: menuai,
    mock_rpc_device: Mock,
    device_registry: DeviceRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test RPC restored sleeping binary sensor missing last state."""
    entry = await init_integration(menuai, 2, sleep_period=1000, skip_setup=True)
    device = register_device(device_registry, entry)
    entity_id = register_entity(
        menuai,
        BINARY_SENSOR_DOMAIN,
        "test_name_cloud",
        "cloud-cloud",
        entry,
        device_id=device.id,
    )

    monkeypatch.setattr(mock_rpc_device, "initialized", False)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_UNKNOWN

    # Make device online
    monkeypatch.setattr(mock_rpc_device, "initialized", True)
    mock_rpc_device.mock_online()
    await menuai.async_block_till_done(wait_background_tasks=True)

    # Mock update
    mock_rpc_device.mock_update()
    await menuai.async_block_till_done()

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_OFF


@pytest.mark.parametrize(
    ("name", "entity_id"),
    [
        ("Virtual binary sensor", "binary_sensor.test_name_virtual_binary_sensor"),
        (None, "binary_sensor.test_name_boolean_203"),
    ],
)
async def test_rpc_device_virtual_binary_sensor(
    menuai: menuai,
    entity_registry: EntityRegistry,
    mock_rpc_device: Mock,
    monkeypatch: pytest.MonkeyPatch,
    name: str | None,
    entity_id: str,
) -> None:
    """Test a virtual binary sensor for RPC device."""
    config = deepcopy(mock_rpc_device.config)
    config["boolean:203"] = {
        "name": name,
        "meta": {"ui": {"view": "label"}},
    }
    monkeypatch.setattr(mock_rpc_device, "config", config)

    status = deepcopy(mock_rpc_device.status)
    status["boolean:203"] = {"value": True}
    monkeypatch.setattr(mock_rpc_device, "status", status)

    await init_integration(menuai, 3)

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_ON

    assert (entry := entity_registry.async_get(entity_id))
    assert entry.unique_id == "123456789ABC-boolean:203-boolean"

    monkeypatch.setitem(mock_rpc_device.status["boolean:203"], "value", False)
    mock_rpc_device.mock_update()

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_OFF


async def test_rpc_remove_virtual_binary_sensor_when_mode_toggle(
    menuai: menuai,
    entity_registry: EntityRegistry,
    device_registry: DeviceRegistry,
    mock_rpc_device: Mock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test if the virtual binary sensor will be removed if the mode has been changed to a toggle."""
    config = deepcopy(mock_rpc_device.config)
    config["boolean:200"] = {"name": None, "meta": {"ui": {"view": "toggle"}}}
    monkeypatch.setattr(mock_rpc_device, "config", config)

    status = deepcopy(mock_rpc_device.status)
    status["boolean:200"] = {"value": True}
    monkeypatch.setattr(mock_rpc_device, "status", status)

    config_entry = await init_integration(menuai, 3, skip_setup=True)
    device_entry = register_device(device_registry, config_entry)
    entity_id = register_entity(
        menuai,
        BINARY_SENSOR_DOMAIN,
        "test_name_boolean_200",
        "boolean:200-boolean",
        config_entry,
        device_id=device_entry.id,
    )

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert entity_registry.async_get(entity_id) is None


async def test_rpc_remove_virtual_binary_sensor_when_orphaned(
    menuai: menuai,
    entity_registry: EntityRegistry,
    device_registry: DeviceRegistry,
    mock_rpc_device: Mock,
) -> None:
    """Check whether the virtual binary sensor will be removed if it has been removed from the device configuration."""
    config_entry = await init_integration(menuai, 3, skip_setup=True)
    device_entry = register_device(device_registry, config_entry)
    entity_id = register_entity(
        menuai,
        BINARY_SENSOR_DOMAIN,
        "test_name_boolean_200",
        "boolean:200-boolean",
        config_entry,
        device_id=device_entry.id,
    )

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert entity_registry.async_get(entity_id) is None


async def test_blu_trv_binary_sensor_entity(
    menuai: menuai,
    mock_blu_trv: Mock,
    entity_registry: EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test BLU TRV binary sensor entity."""
    await init_integration(menuai, 3, model=MODEL_BLU_GATEWAY_G3)

    for entity in ("calibration",):
        entity_id = f"{BINARY_SENSOR_DOMAIN}.trv_name_{entity}"

        state = menuai.states.get(entity_id)
        assert state == snapshot(name=f"{entity_id}-state")

        entry = entity_registry.async_get(entity_id)
        assert entry == snapshot(name=f"{entity_id}-entry")


async def test_rpc_flood_entities(
    menuai: menuai,
    mock_rpc_device: Mock,
    entity_registry: EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test RPC flood sensor entities."""
    await init_integration(menuai, 4)

    for entity in ("flood", "mute"):
        entity_id = f"{BINARY_SENSOR_DOMAIN}.test_name_kitchen_{entity}"

        state = menuai.states.get(entity_id)
        assert state == snapshot(name=f"{entity_id}-state")

        entry = entity_registry.async_get(entity_id)
        assert entry == snapshot(name=f"{entity_id}-entry")
