"""Test the LIFX sensor platform."""

from __future__ import annotations

from datetime import timedelta

from menuai.components import lifx
from menuai.components.sensor import SensorDeviceClass, SensorStateClass
from menuai.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_HOST,
    SIGNAL_STRENGTH_DECIBELS,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from . import (
    DEFAULT_ENTRY_TITLE,
    IP_ADDRESS,
    SERIAL,
    _mocked_bulb,
    _mocked_bulb_old_firmware,
    _patch_config_flow_try_connect,
    _patch_device,
    _patch_discovery,
)

from tests.common import MockConfigEntry, async_fire_time_changed


async def test_rssi_sensor(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test LIFX RSSI sensor entity."""

    config_entry = MockConfigEntry(
        domain=lifx.DOMAIN,
        title=DEFAULT_ENTRY_TITLE,
        data={CONF_HOST: IP_ADDRESS},
        unique_id=SERIAL,
    )
    config_entry.add_to_menuai(menuai)
    bulb = _mocked_bulb()
    with (
        _patch_discovery(device=bulb),
        _patch_config_flow_try_connect(device=bulb),
        _patch_device(device=bulb),
    ):
        await async_setup_component(menuai, lifx.DOMAIN, {lifx.DOMAIN: {}})
        await menuai.async_block_till_done()

    entity_id = "sensor.my_bulb_rssi"

    entry = entity_registry.entities.get(entity_id)
    assert entry
    assert entry.disabled
    assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION

    # Test enabling entity
    updated_entry = entity_registry.async_update_entity(
        entry.entity_id, disabled_by=None
    )

    with (
        _patch_discovery(device=bulb),
        _patch_config_flow_try_connect(device=bulb),
        _patch_device(device=bulb),
    ):
        await menuai.config_entries.async_reload(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert updated_entry != entry
    assert updated_entry.disabled is False
    assert updated_entry.unit_of_measurement == SIGNAL_STRENGTH_DECIBELS_MILLIWATT

    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=120))
    await menuai.async_block_till_done()

    rssi = menuai.states.get(entity_id)
    assert (
        rssi.attributes[ATTR_UNIT_OF_MEASUREMENT] == SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    )
    assert rssi.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.SIGNAL_STRENGTH
    assert rssi.attributes["state_class"] == SensorStateClass.MEASUREMENT


async def test_rssi_sensor_old_firmware(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test LIFX RSSI sensor entity."""

    config_entry = MockConfigEntry(
        domain=lifx.DOMAIN,
        title=DEFAULT_ENTRY_TITLE,
        data={CONF_HOST: IP_ADDRESS},
        unique_id=SERIAL,
    )
    config_entry.add_to_menuai(menuai)
    bulb = _mocked_bulb_old_firmware()
    with (
        _patch_discovery(device=bulb),
        _patch_config_flow_try_connect(device=bulb),
        _patch_device(device=bulb),
    ):
        await async_setup_component(menuai, lifx.DOMAIN, {lifx.DOMAIN: {}})
        await menuai.async_block_till_done()

    entity_id = "sensor.my_bulb_rssi"

    entry = entity_registry.entities.get(entity_id)
    assert entry
    assert entry.disabled
    assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION

    # Test enabling entity
    updated_entry = entity_registry.async_update_entity(
        entry.entity_id, disabled_by=None
    )

    with (
        _patch_discovery(device=bulb),
        _patch_config_flow_try_connect(device=bulb),
        _patch_device(device=bulb),
    ):
        await menuai.config_entries.async_reload(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert updated_entry != entry
    assert updated_entry.disabled is False
    assert updated_entry.unit_of_measurement == SIGNAL_STRENGTH_DECIBELS

    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=120))
    await menuai.async_block_till_done()

    rssi = menuai.states.get(entity_id)
    assert rssi.attributes[ATTR_UNIT_OF_MEASUREMENT] == SIGNAL_STRENGTH_DECIBELS
    assert rssi.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.SIGNAL_STRENGTH
    assert rssi.attributes["state_class"] == SensorStateClass.MEASUREMENT
