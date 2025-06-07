"""The tests for the Season integration."""

from datetime import datetime

from freezegun import freeze_time
import pytest

from menuai.components.season.const import (
    DOMAIN,
    TYPE_ASTRONOMICAL,
    TYPE_METEOROLOGICAL,
)
from menuai.components.season.sensor import (
    STATE_AUTUMN,
    STATE_SPRING,
    STATE_SUMMER,
    STATE_WINTER,
)
from menuai.components.sensor import ATTR_OPTIONS, SensorDeviceClass
from menuai.const import ATTR_DEVICE_CLASS, CONF_TYPE, STATE_UNKNOWN
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er

from tests.common import MockConfigEntry

HEMISPHERE_NORTHERN = {
    "menuai": {"latitude": 48.864716, "longitude": 2.349014},
    "sensor": {"platform": "season", "type": "astronomical"},
}

HEMISPHERE_SOUTHERN = {
    "menuai": {"latitude": -33.918861, "longitude": 18.423300},
    "sensor": {"platform": "season", "type": "astronomical"},
}

HEMISPHERE_EQUATOR = {
    "menuai": {"latitude": 0, "longitude": -51.065100},
    "sensor": {"platform": "season", "type": "astronomical"},
}

HEMISPHERE_EMPTY = {
    "menuai": {},
    "sensor": {"platform": "season", "type": "meteorological"},
}

NORTHERN_PARAMETERS = [
    (TYPE_ASTRONOMICAL, datetime(2017, 9, 3, 0, 0), STATE_SUMMER),
    (TYPE_METEOROLOGICAL, datetime(2017, 8, 13, 0, 0), STATE_SUMMER),
    (TYPE_ASTRONOMICAL, datetime(2017, 9, 23, 0, 0), STATE_AUTUMN),
    (TYPE_METEOROLOGICAL, datetime(2017, 9, 3, 0, 0), STATE_AUTUMN),
    (TYPE_ASTRONOMICAL, datetime(2017, 12, 25, 0, 0), STATE_WINTER),
    (TYPE_METEOROLOGICAL, datetime(2017, 12, 3, 0, 0), STATE_WINTER),
    (TYPE_ASTRONOMICAL, datetime(2017, 4, 1, 0, 0), STATE_SPRING),
    (TYPE_METEOROLOGICAL, datetime(2017, 3, 3, 0, 0), STATE_SPRING),
]

SOUTHERN_PARAMETERS = [
    (TYPE_ASTRONOMICAL, datetime(2017, 12, 25, 0, 0), STATE_SUMMER),
    (TYPE_METEOROLOGICAL, datetime(2017, 12, 3, 0, 0), STATE_SUMMER),
    (TYPE_ASTRONOMICAL, datetime(2017, 4, 1, 0, 0), STATE_AUTUMN),
    (TYPE_METEOROLOGICAL, datetime(2017, 3, 3, 0, 0), STATE_AUTUMN),
    (TYPE_ASTRONOMICAL, datetime(2017, 9, 3, 0, 0), STATE_WINTER),
    (TYPE_METEOROLOGICAL, datetime(2017, 8, 13, 0, 0), STATE_WINTER),
    (TYPE_ASTRONOMICAL, datetime(2017, 9, 23, 0, 0), STATE_SPRING),
    (TYPE_METEOROLOGICAL, datetime(2017, 9, 3, 0, 0), STATE_SPRING),
]


def idfn(val):
    """Provide IDs for pytest parametrize."""
    if isinstance(val, (datetime)):
        return val.strftime("%Y%m%d")
    return None


@pytest.mark.parametrize(("type", "day", "expected"), NORTHERN_PARAMETERS, ids=idfn)
async def test_season_northern_hemisphere(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_config_entry: MockConfigEntry,
    type: str,
    day: datetime,
    expected: str,
) -> None:
    """Test that season should be summer."""
    menuai.config.latitude = HEMISPHERE_NORTHERN["menuai"]["latitude"]
    mock_config_entry.add_to_menuai(menuai)
    menuai.config_entries.async_update_entry(
        mock_config_entry, unique_id=type, data={CONF_TYPE: type}
    )

    with freeze_time(day):
        await menuai.config_entries.async_setup(mock_config_entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.season")
    assert state
    assert state.state == expected
    assert state.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.ENUM
    assert state.attributes[ATTR_OPTIONS] == ["spring", "summer", "autumn", "winter"]

    entry = entity_registry.async_get("sensor.season")
    assert entry
    assert entry.unique_id == mock_config_entry.entry_id
    assert entry.translation_key == "season"


@pytest.mark.parametrize(("type", "day", "expected"), SOUTHERN_PARAMETERS, ids=idfn)
async def test_season_southern_hemisphere(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    mock_config_entry: MockConfigEntry,
    type: str,
    day: datetime,
    expected: str,
) -> None:
    """Test that season should be summer."""
    menuai.config.latitude = HEMISPHERE_SOUTHERN["menuai"]["latitude"]
    mock_config_entry.add_to_menuai(menuai)
    menuai.config_entries.async_update_entry(
        mock_config_entry, unique_id=type, data={CONF_TYPE: type}
    )

    with freeze_time(day):
        await menuai.config_entries.async_setup(mock_config_entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.season")
    assert state
    assert state.state == expected
    assert state.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.ENUM
    assert state.attributes[ATTR_OPTIONS] == ["spring", "summer", "autumn", "winter"]

    entry = entity_registry.async_get("sensor.season")
    assert entry
    assert entry.unique_id == mock_config_entry.entry_id
    assert entry.translation_key == "season"

    assert entry.device_id
    device_entry = device_registry.async_get(entry.device_id)
    assert device_entry
    assert device_entry.identifiers == {(DOMAIN, mock_config_entry.entry_id)}
    assert device_entry.name == "Season"
    assert device_entry.entry_type is dr.DeviceEntryType.SERVICE


async def test_season_equator(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that season should be unknown for equator."""
    menuai.config.latitude = HEMISPHERE_EQUATOR["menuai"]["latitude"]
    mock_config_entry.add_to_menuai(menuai)

    with freeze_time(datetime(2017, 9, 3, 0, 0)):
        await menuai.config_entries.async_setup(mock_config_entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.season")
    assert state
    assert state.state == STATE_UNKNOWN

    entry = entity_registry.async_get("sensor.season")
    assert entry
    assert entry.unique_id == mock_config_entry.entry_id
