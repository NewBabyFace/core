"""Test the World Air Quality Index (WAQI) sensor."""

import json
from unittest.mock import patch

from aiowaqi import WAQIAirQuality, WAQIError
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.sensor import DOMAIN as SENSOR_DOMAIN
from menuai.components.waqi.const import DOMAIN
from menuai.components.waqi.sensor import SENSORS
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry, async_load_fixture


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensor(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test failed update."""
    mock_config_entry.add_to_menuai(menuai)
    with patch(
        "aiowaqi.WAQIClient.get_by_station_number",
        return_value=WAQIAirQuality.from_dict(
            json.loads(
                await async_load_fixture(menuai, "air_quality_sensor.json", DOMAIN)
            )
        ),
    ):
        assert await async_setup_component(menuai, DOMAIN, {})
        await menuai.async_block_till_done()
    for sensor in SENSORS:
        entity_id = entity_registry.async_get_entity_id(
            SENSOR_DOMAIN, DOMAIN, f"4584_{sensor.key}"
        )
        assert menuai.states.get(entity_id) == snapshot


async def test_updating_failed(
    menuai: menuai, mock_config_entry: MockConfigEntry
) -> None:
    """Test failed update."""
    mock_config_entry.add_to_menuai(menuai)
    with patch(
        "aiowaqi.WAQIClient.get_by_station_number",
        side_effect=WAQIError(),
    ):
        assert await async_setup_component(menuai, DOMAIN, {})
        await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY
