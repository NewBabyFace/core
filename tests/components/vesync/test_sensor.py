"""Tests for the sensor module."""

import pytest
import requests_mock
from syrupy.assertion import SnapshotAssertion

from menuai.components.sensor import DOMAIN as SENSOR_DOMAIN
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er

from .common import ALL_DEVICE_NAMES, ENTITY_HUMIDIFIER_HUMIDITY, mock_devices_response

from tests.common import MockConfigEntry


@pytest.mark.parametrize("device_name", ALL_DEVICE_NAMES)
async def test_sensor_state(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    config_entry: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    requests_mock: requests_mock.Mocker,
    device_name: str,
) -> None:
    """Test the resulting setup state is as expected for the platform."""

    # Configure the API devices call for device_name
    mock_devices_response(requests_mock, device_name)

    # setup platform - only including the named device
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    # Check device registry
    devices = dr.async_entries_for_config_entry(device_registry, config_entry.entry_id)
    assert devices == snapshot(name="devices")

    # Check entity registry
    entities = [
        entity
        for entity in er.async_entries_for_config_entry(
            entity_registry, config_entry.entry_id
        )
        if entity.domain == SENSOR_DOMAIN
    ]
    assert entities == snapshot(name="entities")

    # Check states
    for entity in entities:
        assert menuai.states.get(entity.entity_id) == snapshot(name=entity.entity_id)


async def test_humidity(
    menuai: menuai, humidifier_config_entry: MockConfigEntry
) -> None:
    """Test the state of humidity sensor entity."""

    assert menuai.states.get(ENTITY_HUMIDIFIER_HUMIDITY).state == "35"
