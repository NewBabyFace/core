"""The tests for the Monoprice Blackbird media player platform."""

from collections import defaultdict
from unittest import mock

import pytest
import voluptuous as vol

from menuai.components.blackbird.const import DOMAIN, SERVICE_SETALLZONES
from menuai.components.blackbird.media_player import (
    DATA_BLACKBIRD,
    PLATFORM_SCHEMA,
)
from menuai.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
)
from menuai.const import STATE_OFF, STATE_ON
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockEntityPlatform


class AttrDict(dict):
    """Helper class for mocking attributes."""

    def __setattr__(self, name, value):
        """Set attribute."""
        self[name] = value

    def __getattr__(self, item):
        """Get attribute."""
        return self[item]


class MockBlackbird:
    """Mock for pyblackbird object."""

    def __init__(self) -> None:
        """Init mock object."""
        self.zones = defaultdict(lambda: AttrDict(power=True, av=1))

    def zone_status(self, zone_id):
        """Get zone status."""
        status = self.zones[zone_id]
        status.zone = zone_id
        return AttrDict(status)

    def set_zone_source(self, zone_id, source_idx):
        """Set source for zone."""
        self.zones[zone_id].av = source_idx

    def set_zone_power(self, zone_id, power):
        """Turn zone on/off."""
        self.zones[zone_id].power = power

    def set_all_zone_source(self, source_idx):
        """Set source for all zones."""
        self.zones[3].av = source_idx


def test_valid_serial_schema() -> None:
    """Test valid schema."""
    valid_schema = {
        "platform": "blackbird",
        "port": "/dev/ttyUSB0",
        "zones": {
            1: {"name": "a"},
            2: {"name": "a"},
            3: {"name": "a"},
            4: {"name": "a"},
            5: {"name": "a"},
            6: {"name": "a"},
            7: {"name": "a"},
            8: {"name": "a"},
        },
        "sources": {
            1: {"name": "a"},
            2: {"name": "a"},
            3: {"name": "a"},
            4: {"name": "a"},
            5: {"name": "a"},
            6: {"name": "a"},
            7: {"name": "a"},
            8: {"name": "a"},
        },
    }
    PLATFORM_SCHEMA(valid_schema)


def test_valid_socket_schema() -> None:
    """Test valid schema."""
    valid_schema = {
        "platform": "blackbird",
        "host": "192.168.1.50",
        "zones": {
            1: {"name": "a"},
            2: {"name": "a"},
            3: {"name": "a"},
            4: {"name": "a"},
            5: {"name": "a"},
        },
        "sources": {
            1: {"name": "a"},
            2: {"name": "a"},
            3: {"name": "a"},
            4: {"name": "a"},
        },
    }
    PLATFORM_SCHEMA(valid_schema)


def test_invalid_schemas() -> None:
    """Test invalid schemas."""
    schemas = (
        {},  # Empty
        None,  # None
        # Port and host used concurrently
        {
            "platform": "blackbird",
            "port": "/dev/ttyUSB0",
            "host": "192.168.1.50",
            "name": "Name",
            "zones": {1: {"name": "a"}},
            "sources": {1: {"name": "b"}},
        },
        # Port or host missing
        {
            "platform": "blackbird",
            "name": "Name",
            "zones": {1: {"name": "a"}},
            "sources": {1: {"name": "b"}},
        },
        # Invalid zone number
        {
            "platform": "blackbird",
            "port": "/dev/ttyUSB0",
            "name": "Name",
            "zones": {11: {"name": "a"}},
            "sources": {1: {"name": "b"}},
        },
        # Invalid source number
        {
            "platform": "blackbird",
            "port": "/dev/ttyUSB0",
            "name": "Name",
            "zones": {1: {"name": "a"}},
            "sources": {9: {"name": "b"}},
        },
        # Zone missing name
        {
            "platform": "blackbird",
            "port": "/dev/ttyUSB0",
            "name": "Name",
            "zones": {1: {}},
            "sources": {1: {"name": "b"}},
        },
        # Source missing name
        {
            "platform": "blackbird",
            "port": "/dev/ttyUSB0",
            "name": "Name",
            "zones": {1: {"name": "a"}},
            "sources": {1: {}},
        },
    )
    for value in schemas:
        with pytest.raises(vol.MultipleInvalid):
            PLATFORM_SCHEMA(value)


@pytest.fixture
def mock_blackbird() -> MockBlackbird:
    """Return a mock blackbird instance."""
    return MockBlackbird()


@pytest.fixture
async def setup_blackbird(menuai: menuai, mock_blackbird: MockBlackbird) -> None:
    """Set up blackbird."""
    with mock.patch(
        "menuai.components.blackbird.media_player.get_blackbird",
        return_value=mock_blackbird,
    ):
        await async_setup_component(
            menuai,
            "media_player",
            {
                "media_player": {
                    "platform": "blackbird",
                    "port": "/dev/ttyUSB0",
                    "zones": {3: {"name": "Zone name"}},
                    "sources": {
                        1: {"name": "one"},
                        3: {"name": "three"},
                        2: {"name": "two"},
                    },
                }
            },
        )
        await menuai.async_block_till_done()


@pytest.fixture
def media_player_entity(
    menuai: menuai, setup_blackbird: None
) -> MediaPlayerEntity:
    """Return the media player entity."""
    media_player = menuai.data[DATA_BLACKBIRD]["/dev/ttyUSB0-3"]
    media_player.menuai = menuai
    media_player.platform = MockEntityPlatform(menuai)
    media_player.entity_id = "media_player.zone_3"
    return media_player


@pytest.mark.usefixtures("setup_blackbird")
async def test_setup_platform(menuai: menuai) -> None:
    """Test setting up platform."""
    # One service must be registered
    assert menuai.services.has_service(DOMAIN, SERVICE_SETALLZONES)
    assert len(menuai.data[DATA_BLACKBIRD]) == 1
    assert menuai.data[DATA_BLACKBIRD]["/dev/ttyUSB0-3"].name == "Zone name"


async def test_setallzones_service_call_with_entity_id(
    menuai: menuai,
    media_player_entity: MediaPlayerEntity,
    mock_blackbird: MockBlackbird,
) -> None:
    """Test set all zone source service call with entity id."""
    await menuai.async_add_executor_job(media_player_entity.update)
    assert media_player_entity.name == "Zone name"
    assert media_player_entity.state == STATE_ON
    assert media_player_entity.source == "one"

    # Call set all zones service
    await menuai.services.async_call(
        DOMAIN,
        SERVICE_SETALLZONES,
        {"entity_id": "media_player.zone_3", "source": "three"},
        blocking=True,
    )

    # Check that source was changed
    assert mock_blackbird.zones[3].av == 3
    await menuai.async_add_executor_job(media_player_entity.update)
    assert media_player_entity.source == "three"


async def test_setallzones_service_call_without_entity_id(
    mock_blackbird: MockBlackbird,
    menuai: menuai,
    media_player_entity: MediaPlayerEntity,
) -> None:
    """Test set all zone source service call without entity id."""
    await menuai.async_add_executor_job(media_player_entity.update)
    assert media_player_entity.name == "Zone name"
    assert media_player_entity.state == STATE_ON
    assert media_player_entity.source == "one"

    # Call set all zones service
    await menuai.services.async_call(
        DOMAIN, SERVICE_SETALLZONES, {"source": "three"}, blocking=True
    )

    # Check that source was changed
    assert mock_blackbird.zones[3].av == 3
    await menuai.async_add_executor_job(media_player_entity.update)
    assert media_player_entity.source == "three"


async def test_update(
    menuai: menuai, media_player_entity: MediaPlayerEntity
) -> None:
    """Test updating values from blackbird."""

    assert media_player_entity.state == STATE_ON
    assert media_player_entity.source == "one"


async def test_name(media_player_entity: MediaPlayerEntity) -> None:
    """Test name property."""
    assert media_player_entity.name == "Zone name"


async def test_state(
    menuai: menuai,
    media_player_entity: MediaPlayerEntity,
    mock_blackbird: MockBlackbird,
) -> None:
    """Test state property."""
    assert media_player_entity.state == STATE_ON

    mock_blackbird.zones[3].power = False
    await menuai.async_add_executor_job(media_player_entity.update)
    assert media_player_entity.state == STATE_OFF


async def test_supported_features(media_player_entity: MediaPlayerEntity) -> None:
    """Test supported features property."""
    assert (
        media_player_entity.supported_features
        == MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.SELECT_SOURCE
    )


async def test_source(
    menuai: menuai, media_player_entity: MediaPlayerEntity
) -> None:
    """Test source property."""
    assert media_player_entity.source == "one"


async def test_media_title(
    menuai: menuai, media_player_entity: MediaPlayerEntity
) -> None:
    """Test media title property."""
    assert media_player_entity.media_title == "one"


async def test_source_list(media_player_entity: MediaPlayerEntity) -> None:
    """Test source list property."""
    # Note, the list is sorted!
    assert media_player_entity.source_list == ["one", "two", "three"]


async def test_select_source(
    menuai: menuai,
    media_player_entity: MediaPlayerEntity,
    mock_blackbird: MockBlackbird,
) -> None:
    """Test source selection methods."""
    await menuai.async_add_executor_job(media_player_entity.update)

    assert media_player_entity.source == "one"

    await media_player_entity.async_select_source("two")
    assert mock_blackbird.zones[3].av == 2
    await menuai.async_add_executor_job(media_player_entity.update)
    assert media_player_entity.source == "two"

    # Trying to set unknown source.
    await media_player_entity.async_select_source("no name")
    assert mock_blackbird.zones[3].av == 2
    await menuai.async_add_executor_job(media_player_entity.update)
    assert media_player_entity.source == "two"


async def test_turn_on(
    menuai: menuai,
    media_player_entity: MediaPlayerEntity,
    mock_blackbird: MockBlackbird,
) -> None:
    """Testing turning on the zone."""
    mock_blackbird.zones[3].power = False
    await menuai.async_add_executor_job(media_player_entity.update)
    assert media_player_entity.state == STATE_OFF

    await media_player_entity.async_turn_on()
    assert mock_blackbird.zones[3].power
    await menuai.async_add_executor_job(media_player_entity.update)
    assert media_player_entity.state == STATE_ON


async def test_turn_off(
    menuai: menuai,
    media_player_entity: MediaPlayerEntity,
    mock_blackbird: MockBlackbird,
) -> None:
    """Testing turning off the zone."""
    mock_blackbird.zones[3].power = True
    await menuai.async_add_executor_job(media_player_entity.update)
    assert media_player_entity.state == STATE_ON

    await media_player_entity.async_turn_off()
    assert not mock_blackbird.zones[3].power
    await menuai.async_add_executor_job(media_player_entity.update)
    assert media_player_entity.state == STATE_OFF
