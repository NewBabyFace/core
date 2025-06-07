"""The tests for the Universal Media player platform."""

from copy import copy
from unittest.mock import Mock, patch

import pytest
from voluptuous.error import MultipleInvalid

from menuai import config as menuai_config
from menuai.components import input_number, input_select, media_player, switch
from menuai.components.media_player import (
    BrowseMedia,
    MediaClass,
    MediaPlayerEntityFeature,
)
from menuai.components.universal import media_player as universal
from menuai.const import (
    SERVICE_RELOAD,
    STATE_OFF,
    STATE_ON,
    STATE_PAUSED,
    STATE_PLAYING,
    STATE_UNKNOWN,
)
from menuai.core import Context, menuai, callback
from menuai.helpers import entity_registry as er
from menuai.helpers.event import async_track_state_change_event
from menuai.setup import async_setup_component

from tests.common import MockEntityPlatform, async_mock_service, get_fixture_path

CONFIG_CHILDREN_ONLY = {
    "name": "test",
    "platform": "universal",
    "children": [
        media_player.ENTITY_ID_FORMAT.format("mock1"),
        media_player.ENTITY_ID_FORMAT.format("mock2"),
    ],
}

MOCK_BROWSE_MEDIA = BrowseMedia(
    media_class=MediaClass.APP,
    media_content_id="mock-id",
    media_content_type="mock-type",
    title="Mock Title",
    can_play=False,
    can_expand=True,
)


def validate_config(config):
    """Use the platform schema to validate configuration."""
    validated_config = universal.PLATFORM_SCHEMA(config)
    validated_config.pop("platform")
    return validated_config


class MockMediaPlayer(media_player.MediaPlayerEntity):
    """Mock media player for testing."""

    def __init__(self, menuai: menuai, name: str) -> None:
        """Initialize the media player."""
        self.menuai = menuai
        self._name = name
        self.entity_id = media_player.ENTITY_ID_FORMAT.format(name)
        self._state = STATE_OFF
        self._volume_level = 0
        self._is_volume_muted = False
        self._media_title = None
        self._supported_features = 0
        self._source = None
        self._tracks = 12
        self._media_image_url = None
        self._shuffle = False
        self._sound_mode = None
        self._repeat = None
        self.platform = MockEntityPlatform(menuai)

        self.service_calls = {
            "turn_on": async_mock_service(
                menuai, media_player.DOMAIN, media_player.SERVICE_TURN_ON
            ),
            "turn_off": async_mock_service(
                menuai, media_player.DOMAIN, media_player.SERVICE_TURN_OFF
            ),
            "mute_volume": async_mock_service(
                menuai, media_player.DOMAIN, media_player.SERVICE_VOLUME_MUTE
            ),
            "set_volume_level": async_mock_service(
                menuai, media_player.DOMAIN, media_player.SERVICE_VOLUME_SET
            ),
            "media_play": async_mock_service(
                menuai, media_player.DOMAIN, media_player.SERVICE_MEDIA_PLAY
            ),
            "media_pause": async_mock_service(
                menuai, media_player.DOMAIN, media_player.SERVICE_MEDIA_PAUSE
            ),
            "media_stop": async_mock_service(
                menuai, media_player.DOMAIN, media_player.SERVICE_MEDIA_STOP
            ),
            "media_previous_track": async_mock_service(
                menuai, media_player.DOMAIN, media_player.SERVICE_MEDIA_PREVIOUS_TRACK
            ),
            "media_next_track": async_mock_service(
                menuai, media_player.DOMAIN, media_player.SERVICE_MEDIA_NEXT_TRACK
            ),
            "media_seek": async_mock_service(
                menuai, media_player.DOMAIN, media_player.SERVICE_MEDIA_SEEK
            ),
            "play_media": async_mock_service(
                menuai, media_player.DOMAIN, media_player.SERVICE_PLAY_MEDIA
            ),
            "volume_up": async_mock_service(
                menuai, media_player.DOMAIN, media_player.SERVICE_VOLUME_UP
            ),
            "volume_down": async_mock_service(
                menuai, media_player.DOMAIN, media_player.SERVICE_VOLUME_DOWN
            ),
            "media_play_pause": async_mock_service(
                menuai, media_player.DOMAIN, media_player.SERVICE_MEDIA_PLAY_PAUSE
            ),
            "select_sound_mode": async_mock_service(
                menuai, media_player.DOMAIN, media_player.SERVICE_SELECT_SOUND_MODE
            ),
            "select_source": async_mock_service(
                menuai, media_player.DOMAIN, media_player.SERVICE_SELECT_SOURCE
            ),
            "toggle": async_mock_service(
                menuai, media_player.DOMAIN, media_player.SERVICE_TOGGLE
            ),
            "clear_playlist": async_mock_service(
                menuai, media_player.DOMAIN, media_player.SERVICE_CLEAR_PLAYLIST
            ),
            "repeat_set": async_mock_service(
                menuai, media_player.DOMAIN, media_player.SERVICE_REPEAT_SET
            ),
            "shuffle_set": async_mock_service(
                menuai, media_player.DOMAIN, media_player.SERVICE_SHUFFLE_SET
            ),
        }

    @property
    def name(self):
        """Return the name of player."""
        return self._name

    @property
    def state(self):
        """Return the state of the player."""
        return self._state

    @property
    def volume_level(self):
        """Return the volume level of player."""
        return self._volume_level

    @property
    def is_volume_muted(self):
        """Return true if the media player is muted."""
        return self._is_volume_muted

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return MediaPlayerEntityFeature(self._supported_features)

    @property
    def media_image_url(self):
        """Image url of current playing media."""
        return self._media_image_url

    @property
    def shuffle(self):
        """Return true if the media player is shuffling."""
        return self._shuffle

    def turn_on(self):
        """Mock turn_on function."""
        self._state = None

    def turn_off(self):
        """Mock turn_off function."""
        self._state = STATE_OFF

    def mute_volume(self, mute):
        """Mock mute function."""
        self._is_volume_muted = mute

    def set_volume_level(self, volume):
        """Mock set volume level."""
        self._volume_level = volume

    def media_play(self):
        """Mock play."""
        self._state = STATE_PLAYING

    def media_pause(self):
        """Mock pause."""
        self._state = STATE_PAUSED

    def select_sound_mode(self, sound_mode):
        """Set the sound mode."""
        self._sound_mode = sound_mode

    def select_source(self, source):
        """Set the input source."""
        self._source = source

    def async_toggle(self):
        """Toggle the power on the media player."""
        self._state = STATE_OFF if self._state == STATE_ON else STATE_ON

    def clear_playlist(self):
        """Clear players playlist."""
        self._tracks = 0

    def set_shuffle(self, shuffle):
        """Enable/disable shuffle mode."""
        self._shuffle = shuffle

    def set_repeat(self, repeat):
        """Enable/disable repeat mode."""
        self._repeat = repeat


@pytest.fixture
async def mock_states(menuai: menuai) -> Mock:
    """Set mock states used in tests."""
    result = Mock()

    result.mock_mp_1 = MockMediaPlayer(menuai, "mock1")
    result.mock_mp_1.async_schedule_update_ha_state()

    result.mock_mp_2 = MockMediaPlayer(menuai, "mock2")
    result.mock_mp_2.async_schedule_update_ha_state()

    await menuai.async_block_till_done()

    result.mock_mute_switch_id = switch.ENTITY_ID_FORMAT.format("mute")
    menuai.states.async_set(result.mock_mute_switch_id, STATE_OFF)

    result.mock_state_switch_id = switch.ENTITY_ID_FORMAT.format("state")
    menuai.states.async_set(result.mock_state_switch_id, STATE_OFF)

    result.mock_volume_id = f"{input_number.DOMAIN}.volume_level"
    menuai.states.async_set(result.mock_volume_id, 0)

    result.mock_source_list_id = f"{input_select.DOMAIN}.source_list"
    menuai.states.async_set(result.mock_source_list_id, ["dvd", "htpc"])

    result.mock_source_id = f"{input_select.DOMAIN}.source"
    menuai.states.async_set(result.mock_source_id, "dvd")

    result.mock_sound_mode_list_id = f"{input_select.DOMAIN}.sound_mode_list"
    menuai.states.async_set(result.mock_sound_mode_list_id, ["music", "movie"])

    result.mock_sound_mode_id = f"{input_select.DOMAIN}.sound_mode"
    menuai.states.async_set(result.mock_sound_mode_id, "music")

    result.mock_shuffle_switch_id = switch.ENTITY_ID_FORMAT.format("shuffle")
    menuai.states.async_set(result.mock_shuffle_switch_id, STATE_OFF)

    result.mock_repeat_switch_id = switch.ENTITY_ID_FORMAT.format("repeat")
    menuai.states.async_set(result.mock_repeat_switch_id, STATE_OFF)

    return result


@pytest.fixture
def config_children_and_attr(mock_states):
    """Return configuration that references the mock states."""
    return {
        "name": "test",
        "platform": "universal",
        "children": [
            media_player.ENTITY_ID_FORMAT.format("mock1"),
            media_player.ENTITY_ID_FORMAT.format("mock2"),
        ],
        "attributes": {
            "is_volume_muted": mock_states.mock_mute_switch_id,
            "volume_level": mock_states.mock_volume_id,
            "source": mock_states.mock_source_id,
            "source_list": mock_states.mock_source_list_id,
            "state": mock_states.mock_state_switch_id,
            "shuffle": mock_states.mock_shuffle_switch_id,
            "repeat": mock_states.mock_repeat_switch_id,
            "sound_mode_list": mock_states.mock_sound_mode_list_id,
            "sound_mode": mock_states.mock_sound_mode_id,
        },
    }


async def test_config_children_only(menuai: menuai) -> None:
    """Check config with only children."""
    config_start = copy(CONFIG_CHILDREN_ONLY)
    del config_start["platform"]
    config_start["commands"] = {}
    config_start["attributes"] = {}

    config = validate_config(CONFIG_CHILDREN_ONLY)
    assert config_start == config


async def test_config_children_and_attr(
    menuai: menuai, config_children_and_attr
) -> None:
    """Check config with children and attributes."""
    config_start = copy(config_children_and_attr)
    del config_start["platform"]
    config_start["commands"] = {}

    config = validate_config(config_children_and_attr)
    assert config_start == config


async def test_config_no_name(menuai: menuai) -> None:
    """Check config with no Name entry."""
    response = True
    try:
        validate_config({"platform": "universal"})
    except MultipleInvalid:
        response = False
    assert not response


async def test_config_bad_children(menuai: menuai) -> None:
    """Check config with bad children entry."""
    config_no_children = {"name": "test", "platform": "universal"}
    config_bad_children = {"name": "test", "children": {}, "platform": "universal"}

    config_no_children = validate_config(config_no_children)
    assert config_no_children["children"] == []

    config_bad_children = validate_config(config_bad_children)
    assert config_bad_children["children"] == []


async def test_config_bad_commands(menuai: menuai) -> None:
    """Check config with bad commands entry."""
    config = {"name": "test", "platform": "universal"}

    config = validate_config(config)
    assert config["commands"] == {}


async def test_config_bad_attributes(menuai: menuai) -> None:
    """Check config with bad attributes."""
    config = {"name": "test", "platform": "universal"}

    config = validate_config(config)
    assert config["attributes"] == {}


async def test_config_bad_key(menuai: menuai) -> None:
    """Check config with bad key."""
    config = {"name": "test", "asdf": 5, "platform": "universal"}

    config = validate_config(config)
    assert "asdf" not in config


async def test_platform_setup(menuai: menuai) -> None:
    """Test platform setup."""
    config = {"name": "test", "platform": "universal"}
    assert await async_setup_component(menuai, "media_player", {"media_player": config})
    await menuai.async_block_till_done()
    assert menuai.states.async_all() != []
    assert menuai.states.get("media_player.test") is not None


async def test_master_state(menuai: menuai) -> None:
    """Test master state property."""
    config = validate_config(CONFIG_CHILDREN_ONLY)

    ump = universal.UniversalMediaPlayer(menuai, config)

    assert ump.master_state is None


async def test_master_state_with_attrs(
    menuai: menuai, config_children_and_attr, mock_states
) -> None:
    """Test master state property."""
    config = validate_config(config_children_and_attr)

    ump = universal.UniversalMediaPlayer(menuai, config)

    assert ump.master_state == STATE_OFF
    menuai.states.async_set(mock_states.mock_state_switch_id, STATE_ON)
    assert ump.master_state == STATE_ON


async def test_master_state_with_bad_attrs(
    menuai: menuai, config_children_and_attr
) -> None:
    """Test master state property."""
    config = copy(config_children_and_attr)
    config["attributes"]["state"] = "bad.entity_id"
    config = validate_config(config)

    ump = universal.UniversalMediaPlayer(menuai, config)

    assert ump.master_state == STATE_OFF


async def test_active_child_state(menuai: menuai, mock_states) -> None:
    """Test active child state property."""
    config = validate_config(CONFIG_CHILDREN_ONLY)

    ump = universal.UniversalMediaPlayer(menuai, config)
    ump.entity_id = media_player.ENTITY_ID_FORMAT.format(config["name"])
    await ump.async_update()

    assert ump._child_state is None

    mock_states.mock_mp_1._state = STATE_PLAYING
    mock_states.mock_mp_1.async_schedule_update_ha_state()
    await menuai.async_block_till_done()
    await ump.async_update()
    assert mock_states.mock_mp_1.entity_id == ump._child_state.entity_id

    mock_states.mock_mp_2._state = STATE_PLAYING
    mock_states.mock_mp_2.async_schedule_update_ha_state()
    await menuai.async_block_till_done()
    await ump.async_update()
    assert mock_states.mock_mp_1.entity_id == ump._child_state.entity_id

    mock_states.mock_mp_1._state = STATE_PAUSED
    mock_states.mock_mp_1.async_schedule_update_ha_state()
    await menuai.async_block_till_done()
    await ump.async_update()
    assert mock_states.mock_mp_2.entity_id == ump._child_state.entity_id

    mock_states.mock_mp_1._state = STATE_OFF
    mock_states.mock_mp_1.async_schedule_update_ha_state()
    await menuai.async_block_till_done()
    await ump.async_update()
    assert mock_states.mock_mp_2.entity_id == ump._child_state.entity_id

    mock_states.mock_mp_1._state = "invalid_state"
    mock_states.mock_mp_1.async_schedule_update_ha_state()
    await menuai.async_block_till_done()
    await ump.async_update()
    assert mock_states.mock_mp_2.entity_id == ump._child_state.entity_id


async def test_name(menuai: menuai) -> None:
    """Test name property."""
    assert await async_setup_component(
        menuai, "media_player", {"media_player": CONFIG_CHILDREN_ONLY}
    )
    assert menuai.states.get("media_player.test") is not None


async def test_polling(menuai: menuai) -> None:
    """Test should_poll property."""
    config = validate_config(CONFIG_CHILDREN_ONLY)

    ump = universal.UniversalMediaPlayer(menuai, config)

    assert ump.should_poll is False


async def test_state_children_only(menuai: menuai, mock_states) -> None:
    """Test media player state with only children."""
    config = validate_config(CONFIG_CHILDREN_ONLY)

    ump = universal.UniversalMediaPlayer(menuai, config)
    ump.entity_id = media_player.ENTITY_ID_FORMAT.format(config["name"])
    await ump.async_update()

    assert ump.state, STATE_OFF

    mock_states.mock_mp_1._state = STATE_PLAYING
    mock_states.mock_mp_1.async_schedule_update_ha_state()
    await menuai.async_block_till_done()
    await ump.async_update()
    assert ump.state == STATE_PLAYING

    mock_states.mock_mp_1._state = STATE_ON
    mock_states.mock_mp_1._attr_assumed_state = True
    mock_states.mock_mp_1.async_schedule_update_ha_state()
    await menuai.async_block_till_done()
    await ump.async_update()
    assert ump.assumed_state is True


async def test_state_with_children_and_attrs(
    menuai: menuai, config_children_and_attr, mock_states
) -> None:
    """Test media player with children and master state."""
    config = validate_config(config_children_and_attr)

    ump = universal.UniversalMediaPlayer(menuai, config)
    ump.entity_id = media_player.ENTITY_ID_FORMAT.format(config["name"])
    await ump.async_update()

    assert ump.state == STATE_OFF

    menuai.states.async_set(mock_states.mock_state_switch_id, STATE_ON)
    await ump.async_update()
    assert ump.state == STATE_ON

    mock_states.mock_mp_1._state = STATE_PLAYING
    mock_states.mock_mp_1.async_schedule_update_ha_state()
    await menuai.async_block_till_done()
    await ump.async_update()
    assert ump.state == STATE_PLAYING

    menuai.states.async_set(mock_states.mock_state_switch_id, STATE_OFF)
    await ump.async_update()
    assert ump.state == STATE_OFF


async def test_volume_level(menuai: menuai, mock_states) -> None:
    """Test volume level property."""
    config = validate_config(CONFIG_CHILDREN_ONLY)

    ump = universal.UniversalMediaPlayer(menuai, config)
    ump.entity_id = media_player.ENTITY_ID_FORMAT.format(config["name"])
    await ump.async_update()

    assert ump.volume_level is None

    mock_states.mock_mp_1._state = STATE_PLAYING
    mock_states.mock_mp_1.async_schedule_update_ha_state()
    await menuai.async_block_till_done()
    await ump.async_update()
    assert ump.volume_level == 0

    mock_states.mock_mp_1._volume_level = 1
    mock_states.mock_mp_1.async_schedule_update_ha_state()
    await menuai.async_block_till_done()
    await ump.async_update()
    assert ump.volume_level == 1


async def test_media_image_url(menuai: menuai, mock_states) -> None:
    """Test media_image_url property."""
    test_url = "test_url"
    config = validate_config(CONFIG_CHILDREN_ONLY)

    ump = universal.UniversalMediaPlayer(menuai, config)
    ump.entity_id = media_player.ENTITY_ID_FORMAT.format(config["name"])
    await ump.async_update()

    assert ump.media_image_url is None

    mock_states.mock_mp_1._state = STATE_PLAYING
    mock_states.mock_mp_1._media_image_url = test_url
    mock_states.mock_mp_1.async_schedule_update_ha_state()
    await menuai.async_block_till_done()
    await ump.async_update()
    # mock_mp_1 will convert the url to the api proxy url. This test
    # ensures ump passes through the same url without an additional proxy.
    assert mock_states.mock_mp_1.entity_picture == ump.entity_picture


async def test_is_volume_muted_children_only(menuai: menuai, mock_states) -> None:
    """Test is volume muted property w/ children only."""
    config = validate_config(CONFIG_CHILDREN_ONLY)

    ump = universal.UniversalMediaPlayer(menuai, config)
    ump.entity_id = media_player.ENTITY_ID_FORMAT.format(config["name"])
    await ump.async_update()

    assert not ump.is_volume_muted

    mock_states.mock_mp_1._state = STATE_PLAYING
    mock_states.mock_mp_1.async_schedule_update_ha_state()
    await menuai.async_block_till_done()
    await ump.async_update()
    assert not ump.is_volume_muted

    mock_states.mock_mp_1._is_volume_muted = True
    mock_states.mock_mp_1.async_schedule_update_ha_state()
    await menuai.async_block_till_done()
    await ump.async_update()
    assert ump.is_volume_muted


async def test_sound_mode_list_children_and_attr(
    menuai: menuai, config_children_and_attr, mock_states
) -> None:
    """Test sound mode list property w/ children and attrs."""
    config = validate_config(config_children_and_attr)

    ump = universal.UniversalMediaPlayer(menuai, config)

    assert ump.sound_mode_list == "['music', 'movie']"

    menuai.states.async_set(
        mock_states.mock_sound_mode_list_id, ["music", "movie", "game"]
    )
    assert ump.sound_mode_list == "['music', 'movie', 'game']"


async def test_source_list_children_and_attr(
    menuai: menuai, config_children_and_attr, mock_states
) -> None:
    """Test source list property w/ children and attrs."""
    config = validate_config(config_children_and_attr)

    ump = universal.UniversalMediaPlayer(menuai, config)

    assert ump.source_list == "['dvd', 'htpc']"

    menuai.states.async_set(mock_states.mock_source_list_id, ["dvd", "htpc", "game"])
    assert ump.source_list == "['dvd', 'htpc', 'game']"


async def test_sound_mode_children_and_attr(
    menuai: menuai, config_children_and_attr, mock_states
) -> None:
    """Test sound modeproperty w/ children and attrs."""
    config = validate_config(config_children_and_attr)

    ump = universal.UniversalMediaPlayer(menuai, config)

    assert ump.sound_mode == "music"

    menuai.states.async_set(mock_states.mock_sound_mode_id, "movie")
    assert ump.sound_mode == "movie"


async def test_source_children_and_attr(
    menuai: menuai, config_children_and_attr, mock_states
) -> None:
    """Test source property w/ children and attrs."""
    config = validate_config(config_children_and_attr)

    ump = universal.UniversalMediaPlayer(menuai, config)

    assert ump.source == "dvd"

    menuai.states.async_set(mock_states.mock_source_id, "htpc")
    assert ump.source == "htpc"


async def test_volume_level_children_and_attr(
    menuai: menuai, config_children_and_attr, mock_states
) -> None:
    """Test volume level property w/ children and attrs."""
    config = validate_config(config_children_and_attr)

    ump = universal.UniversalMediaPlayer(menuai, config)

    assert ump.volume_level == 0

    menuai.states.async_set(mock_states.mock_volume_id, 100)
    assert ump.volume_level == 100


async def test_is_volume_muted_children_and_attr(
    menuai: menuai, config_children_and_attr, mock_states
) -> None:
    """Test is volume muted property w/ children and attrs."""
    config = validate_config(config_children_and_attr)

    ump = universal.UniversalMediaPlayer(menuai, config)

    assert not ump.is_volume_muted

    menuai.states.async_set(mock_states.mock_mute_switch_id, STATE_ON)
    assert ump.is_volume_muted


async def test_supported_features_children_only(
    menuai: menuai, mock_states
) -> None:
    """Test supported media commands with only children."""
    config = validate_config(CONFIG_CHILDREN_ONLY)

    ump = universal.UniversalMediaPlayer(menuai, config)
    ump.entity_id = media_player.ENTITY_ID_FORMAT.format(config["name"])
    await ump.async_update()

    assert ump.supported_features == 0

    mock_states.mock_mp_1._supported_features = 512
    mock_states.mock_mp_1._state = STATE_PLAYING
    mock_states.mock_mp_1.async_schedule_update_ha_state()
    await menuai.async_block_till_done()
    await ump.async_update()
    assert ump.supported_features == 512


async def test_supported_features_children_and_cmds(
    menuai: menuai, config_children_and_attr, mock_states
) -> None:
    """Test supported media commands with children and attrs."""
    config = copy(config_children_and_attr)
    excmd = {"service": "media_player.test", "data": {}}
    config["commands"] = {
        "turn_on": excmd,
        "turn_off": excmd,
        "volume_up": excmd,
        "volume_down": excmd,
        "volume_mute": excmd,
        "volume_set": excmd,
        "select_sound_mode": excmd,
        "select_source": excmd,
        "repeat_set": excmd,
        "shuffle_set": excmd,
        "media_play": excmd,
        "media_pause": excmd,
        "media_stop": excmd,
        "media_next_track": excmd,
        "media_previous_track": excmd,
        "toggle": excmd,
        "play_media": excmd,
        "clear_playlist": excmd,
    }
    config["browse_media_entity"] = "media_player.test"
    config = validate_config(config)

    ump = universal.UniversalMediaPlayer(menuai, config)
    ump.entity_id = media_player.ENTITY_ID_FORMAT.format(config["name"])
    await ump.async_update()

    mock_states.mock_mp_1._state = STATE_PLAYING
    mock_states.mock_mp_1.async_schedule_update_ha_state()
    await menuai.async_block_till_done()
    await ump.async_update()

    check_flags = (
        MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.SELECT_SOUND_MODE
        | MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.REPEAT_SET
        | MediaPlayerEntityFeature.SHUFFLE_SET
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.NEXT_TRACK
        | MediaPlayerEntityFeature.PREVIOUS_TRACK
        | MediaPlayerEntityFeature.PLAY_MEDIA
        | MediaPlayerEntityFeature.CLEAR_PLAYLIST
        | MediaPlayerEntityFeature.BROWSE_MEDIA
    )

    assert check_flags == ump.supported_features


async def test_overrides(menuai: menuai, config_children_and_attr) -> None:
    """Test overrides."""
    config = copy(config_children_and_attr)
    excmd = {"service": "test.override", "data": {}}
    config["name"] = "overridden"
    config["commands"] = {
        "turn_on": excmd,
        "turn_off": excmd,
        "volume_up": excmd,
        "volume_down": excmd,
        "volume_mute": excmd,
        "volume_set": excmd,
        "select_sound_mode": excmd,
        "select_source": excmd,
        "repeat_set": excmd,
        "shuffle_set": excmd,
        "media_play": excmd,
        "media_play_pause": excmd,
        "media_pause": excmd,
        "media_stop": excmd,
        "media_next_track": excmd,
        "media_previous_track": excmd,
        "clear_playlist": excmd,
        "play_media": excmd,
        "toggle": excmd,
    }
    await async_setup_component(menuai, "media_player", {"media_player": config})
    await menuai.async_block_till_done()

    service = async_mock_service(menuai, "test", "override")
    await menuai.services.async_call(
        "media_player",
        "turn_on",
        service_data={"entity_id": "media_player.overridden"},
        blocking=True,
    )
    assert len(service) == 1
    await menuai.services.async_call(
        "media_player",
        "turn_off",
        service_data={"entity_id": "media_player.overridden"},
        blocking=True,
    )
    assert len(service) == 2
    await menuai.services.async_call(
        "media_player",
        "volume_up",
        service_data={"entity_id": "media_player.overridden"},
        blocking=True,
    )
    assert len(service) == 3
    await menuai.services.async_call(
        "media_player",
        "volume_down",
        service_data={"entity_id": "media_player.overridden"},
        blocking=True,
    )
    assert len(service) == 4
    await menuai.services.async_call(
        "media_player",
        "volume_mute",
        service_data={
            "entity_id": "media_player.overridden",
            "is_volume_muted": True,
        },
        blocking=True,
    )
    assert len(service) == 5
    await menuai.services.async_call(
        "media_player",
        "volume_set",
        service_data={"entity_id": "media_player.overridden", "volume_level": 1},
        blocking=True,
    )
    assert len(service) == 6
    await menuai.services.async_call(
        "media_player",
        "select_sound_mode",
        service_data={
            "entity_id": "media_player.overridden",
            "sound_mode": "music",
        },
        blocking=True,
    )
    assert len(service) == 7
    await menuai.services.async_call(
        "media_player",
        "select_source",
        service_data={"entity_id": "media_player.overridden", "source": "video1"},
        blocking=True,
    )
    assert len(service) == 8
    await menuai.services.async_call(
        "media_player",
        "repeat_set",
        service_data={"entity_id": "media_player.overridden", "repeat": "all"},
        blocking=True,
    )
    assert len(service) == 9
    await menuai.services.async_call(
        "media_player",
        "shuffle_set",
        service_data={"entity_id": "media_player.overridden", "shuffle": True},
        blocking=True,
    )
    assert len(service) == 10
    await menuai.services.async_call(
        "media_player",
        "media_play",
        service_data={"entity_id": "media_player.overridden"},
        blocking=True,
    )
    assert len(service) == 11
    await menuai.services.async_call(
        "media_player",
        "media_pause",
        service_data={"entity_id": "media_player.overridden"},
        blocking=True,
    )
    assert len(service) == 12
    await menuai.services.async_call(
        "media_player",
        "media_stop",
        service_data={"entity_id": "media_player.overridden"},
        blocking=True,
    )
    assert len(service) == 13
    await menuai.services.async_call(
        "media_player",
        "media_next_track",
        service_data={"entity_id": "media_player.overridden"},
        blocking=True,
    )
    assert len(service) == 14
    await menuai.services.async_call(
        "media_player",
        "media_previous_track",
        service_data={"entity_id": "media_player.overridden"},
        blocking=True,
    )
    assert len(service) == 15
    await menuai.services.async_call(
        "media_player",
        "clear_playlist",
        service_data={"entity_id": "media_player.overridden"},
        blocking=True,
    )
    assert len(service) == 16
    await menuai.services.async_call(
        "media_player",
        "media_play_pause",
        service_data={"entity_id": "media_player.overridden"},
        blocking=True,
    )
    assert len(service) == 17
    await menuai.services.async_call(
        "media_player",
        "play_media",
        service_data={
            "entity_id": "media_player.overridden",
            "media_content_id": 1,
            "media_content_type": "channel",
        },
        blocking=True,
    )
    assert len(service) == 18
    await menuai.services.async_call(
        "media_player",
        "toggle",
        service_data={"entity_id": "media_player.overridden"},
        blocking=True,
    )
    assert len(service) == 19


async def test_supported_features_play_pause(
    menuai: menuai, config_children_and_attr, mock_states
) -> None:
    """Test supported media commands with play_pause function."""
    config = copy(config_children_and_attr)
    excmd = {"service": "media_player.test", "data": {"entity_id": "test"}}
    config["commands"] = {"media_play_pause": excmd}
    config = validate_config(config)

    ump = universal.UniversalMediaPlayer(menuai, config)
    ump.entity_id = media_player.ENTITY_ID_FORMAT.format(config["name"])
    await ump.async_update()

    mock_states.mock_mp_1._state = STATE_PLAYING
    mock_states.mock_mp_1.async_schedule_update_ha_state()
    await menuai.async_block_till_done()
    await ump.async_update()

    check_flags = MediaPlayerEntityFeature.PLAY | MediaPlayerEntityFeature.PAUSE

    assert check_flags == ump.supported_features


async def test_service_call_no_active_child(
    menuai: menuai, config_children_and_attr, mock_states
) -> None:
    """Test a service call to children with no active child."""
    config = validate_config(config_children_and_attr)

    ump = universal.UniversalMediaPlayer(menuai, config)
    ump.entity_id = media_player.ENTITY_ID_FORMAT.format(config["name"])
    await ump.async_update()

    mock_states.mock_mp_1._state = STATE_OFF
    mock_states.mock_mp_1.async_schedule_update_ha_state()
    mock_states.mock_mp_2._state = STATE_OFF
    mock_states.mock_mp_2.async_schedule_update_ha_state()
    await menuai.async_block_till_done()
    await ump.async_update()

    await ump.async_turn_off()
    assert len(mock_states.mock_mp_1.service_calls["turn_off"]) == 0
    assert len(mock_states.mock_mp_2.service_calls["turn_off"]) == 0


async def test_service_call_to_child(menuai: menuai, mock_states) -> None:
    """Test service calls that should be routed to a child."""
    config = validate_config(CONFIG_CHILDREN_ONLY)

    ump = universal.UniversalMediaPlayer(menuai, config)
    ump.entity_id = media_player.ENTITY_ID_FORMAT.format(config["name"])
    await ump.async_update()

    mock_states.mock_mp_2._state = STATE_PLAYING
    mock_states.mock_mp_2.async_schedule_update_ha_state()
    await menuai.async_block_till_done()
    await ump.async_update()

    await ump.async_turn_off()
    assert len(mock_states.mock_mp_2.service_calls["turn_off"]) == 1

    await ump.async_turn_on()
    assert len(mock_states.mock_mp_2.service_calls["turn_on"]) == 1

    await ump.async_mute_volume(True)
    assert len(mock_states.mock_mp_2.service_calls["mute_volume"]) == 1

    await ump.async_set_volume_level(0.5)
    assert len(mock_states.mock_mp_2.service_calls["set_volume_level"]) == 1

    await ump.async_media_play()
    assert len(mock_states.mock_mp_2.service_calls["media_play"]) == 1

    await ump.async_media_pause()
    assert len(mock_states.mock_mp_2.service_calls["media_pause"]) == 1

    await ump.async_media_stop()
    assert len(mock_states.mock_mp_2.service_calls["media_stop"]) == 1

    await ump.async_media_previous_track()
    assert len(mock_states.mock_mp_2.service_calls["media_previous_track"]) == 1

    await ump.async_media_next_track()
    assert len(mock_states.mock_mp_2.service_calls["media_next_track"]) == 1

    await ump.async_media_seek(100)
    assert len(mock_states.mock_mp_2.service_calls["media_seek"]) == 1

    await ump.async_play_media("movie", "batman")
    assert len(mock_states.mock_mp_2.service_calls["play_media"]) == 1

    await ump.async_volume_up()
    assert len(mock_states.mock_mp_2.service_calls["volume_up"]) == 1

    await ump.async_volume_down()
    assert len(mock_states.mock_mp_2.service_calls["volume_down"]) == 1

    await ump.async_media_play_pause()
    assert len(mock_states.mock_mp_2.service_calls["media_play_pause"]) == 1

    await ump.async_select_sound_mode("music")
    assert len(mock_states.mock_mp_2.service_calls["select_sound_mode"]) == 1

    await ump.async_select_source("dvd")
    assert len(mock_states.mock_mp_2.service_calls["select_source"]) == 1

    await ump.async_clear_playlist()
    assert len(mock_states.mock_mp_2.service_calls["clear_playlist"]) == 1

    await ump.async_set_repeat(True)
    assert len(mock_states.mock_mp_2.service_calls["repeat_set"]) == 1

    await ump.async_set_shuffle(True)
    assert len(mock_states.mock_mp_2.service_calls["shuffle_set"]) == 1

    await ump.async_toggle()
    # Delegate to turn_off
    assert len(mock_states.mock_mp_2.service_calls["turn_off"]) == 2


async def test_service_call_to_command(menuai: menuai, mock_states) -> None:
    """Test service call to command."""
    config = copy(CONFIG_CHILDREN_ONLY)
    config["commands"] = {"turn_off": {"service": "test.turn_off", "data": {}}}
    config = validate_config(config)

    service = async_mock_service(menuai, "test", "turn_off")

    ump = universal.UniversalMediaPlayer(menuai, config)
    ump.entity_id = media_player.ENTITY_ID_FORMAT.format(config["name"])
    await ump.async_update()

    mock_states.mock_mp_2._state = STATE_PLAYING
    mock_states.mock_mp_2.async_schedule_update_ha_state()
    await menuai.async_block_till_done()
    await ump.async_update()

    await ump.async_turn_off()
    assert len(service) == 1


async def test_state_template(menuai: menuai) -> None:
    """Test with a simple valid state template."""
    menuai.states.async_set("sensor.test_sensor", STATE_ON)

    await async_setup_component(
        menuai,
        "media_player",
        {
            "media_player": {
                "platform": "universal",
                "name": "tv",
                "state_template": "{{ states.sensor.test_sensor.state }}",
            }
        },
    )
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == 2
    await menuai.async_start()

    await menuai.async_block_till_done()
    assert menuai.states.get("media_player.tv").state == STATE_ON
    menuai.states.async_set("sensor.test_sensor", STATE_OFF)
    await menuai.async_block_till_done()
    assert menuai.states.get("media_player.tv").state == STATE_OFF


async def test_browse_media(menuai: menuai) -> None:
    """Test browse media."""
    await async_setup_component(menuai, "menuai", {})
    await async_setup_component(
        menuai, "media_player", {"media_player": {"platform": "demo"}}
    )
    await menuai.async_block_till_done()

    config = {
        "name": "test",
        "platform": "universal",
        "children": [
            "media_player.bedroom",
        ],
    }
    config = validate_config(config)
    ump = universal.UniversalMediaPlayer(menuai, config)
    ump.entity_id = media_player.ENTITY_ID_FORMAT.format(config["name"])
    await ump.async_update()

    with (
        patch(
            "menuai.components.demo.media_player.MediaPlayerEntity.supported_features",
            MediaPlayerEntityFeature.BROWSE_MEDIA,
        ),
        patch(
            "menuai.components.demo.media_player.MediaPlayerEntity.async_browse_media",
            return_value=MOCK_BROWSE_MEDIA,
        ),
    ):
        result = await ump.async_browse_media()
        assert result == MOCK_BROWSE_MEDIA


async def test_browse_media_override(menuai: menuai) -> None:
    """Test browse media override."""
    await async_setup_component(menuai, "menuai", {})
    await async_setup_component(
        menuai, "media_player", {"media_player": {"platform": "demo"}}
    )
    await menuai.async_block_till_done()

    config = {
        "name": "test",
        "platform": "universal",
        "children": [
            "media_player.mock1",
        ],
        "browse_media_entity": "media_player.bedroom",
    }
    config = validate_config(config)
    ump = universal.UniversalMediaPlayer(menuai, config)
    ump.entity_id = media_player.ENTITY_ID_FORMAT.format(config["name"])
    await ump.async_update()

    with (
        patch(
            "menuai.components.demo.media_player.MediaPlayerEntity.supported_features",
            MediaPlayerEntityFeature.BROWSE_MEDIA,
        ),
        patch(
            "menuai.components.demo.media_player.MediaPlayerEntity.async_browse_media",
            return_value=MOCK_BROWSE_MEDIA,
        ),
    ):
        result = await ump.async_browse_media()
        assert result == MOCK_BROWSE_MEDIA


async def test_device_class(menuai: menuai) -> None:
    """Test device_class property."""
    menuai.states.async_set("sensor.test_sensor", "on")

    await async_setup_component(
        menuai,
        "media_player",
        {
            "media_player": {
                "platform": "universal",
                "name": "tv",
                "device_class": "tv",
            }
        },
    )
    await menuai.async_block_till_done()
    assert menuai.states.get("media_player.tv").attributes["device_class"] == "tv"


async def test_unique_id(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test unique_id property."""
    menuai.states.async_set("sensor.test_sensor", "on")

    await async_setup_component(
        menuai,
        "media_player",
        {
            "media_player": {
                "platform": "universal",
                "name": "tv",
                "unique_id": "universal_master_bed_tv",
            }
        },
    )
    await menuai.async_block_till_done()
    assert (
        entity_registry.async_get("media_player.tv").unique_id
        == "universal_master_bed_tv"
    )


async def test_invalid_state_template(menuai: menuai) -> None:
    """Test invalid state template sets state to None."""
    menuai.states.async_set("sensor.test_sensor", "on")

    await async_setup_component(
        menuai,
        "media_player",
        {
            "media_player": {
                "platform": "universal",
                "name": "tv",
                "state_template": "{{ states.sensor.test_sensor.state + x }}",
            }
        },
    )
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == 2
    await menuai.async_start()

    await menuai.async_block_till_done()
    assert menuai.states.get("media_player.tv").state == STATE_UNKNOWN
    menuai.states.async_set("sensor.test_sensor", "off")
    await menuai.async_block_till_done()
    assert menuai.states.get("media_player.tv").state == STATE_UNKNOWN


async def test_master_state_with_template(menuai: menuai) -> None:
    """Test the state_template option."""
    menuai.states.async_set("input_boolean.test", STATE_OFF)
    menuai.states.async_set("media_player.mock1", STATE_OFF)

    templ = (
        '{% if states.input_boolean.test.state == "off" %}on'
        "{% else %}{{ states.media_player.mock1.state }}{% endif %}"
    )

    await async_setup_component(
        menuai,
        "media_player",
        {
            "media_player": {
                "platform": "universal",
                "name": "tv",
                "state_template": templ,
            }
        },
    )

    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == 3
    await menuai.async_start()

    await menuai.async_block_till_done()
    assert menuai.states.get("media_player.tv").state == STATE_ON

    events = []

    async_track_state_change_event(
        menuai,
        "media_player.tv",
        # pylint: disable-next=unnecessary-lambda
        callback(lambda event: events.append(event)),
    )

    context = Context()
    menuai.states.async_set("input_boolean.test", STATE_ON, context=context)
    await menuai.async_block_till_done()
    await menuai.async_block_till_done()

    assert menuai.states.get("media_player.tv").state == STATE_OFF
    assert events[0].context == context


async def test_invalid_active_child_template(menuai: menuai) -> None:
    """Test invalid active child template."""
    menuai.states.async_set("media_player.mock1", STATE_PLAYING)
    menuai.states.async_set("media_player.mock2", STATE_PAUSED)

    await async_setup_component(
        menuai,
        "media_player",
        {
            "media_player": {
                "platform": "universal",
                "name": "tv",
                "children": ["media_player.mock1", "media_player.mock2"],
                "active_child_template": "{{invalid.invalid}}!invalid",
            }
        },
    )
    await menuai.async_block_till_done()
    await menuai.async_start()

    await menuai.async_block_till_done()
    assert menuai.states.get("media_player.tv").state == STATE_PLAYING


async def test_active_child_template(menuai: menuai) -> None:
    """Test override active child with template."""
    menuai.states.async_set("media_player.mock1", STATE_PLAYING)
    menuai.states.async_set("media_player.mock2", STATE_PAUSED)

    await async_setup_component(
        menuai,
        "media_player",
        {
            "media_player": {
                "platform": "universal",
                "name": "tv",
                "children": ["media_player.mock1", "media_player.mock2"],
                "active_child_template": "{{ 'media_player.mock2' }}",
            }
        },
    )
    await menuai.async_block_till_done()
    await menuai.async_start()

    menuai.states.async_set("media_player.mock2", STATE_ON)

    await menuai.async_block_till_done()
    assert menuai.states.get("media_player.tv").state == STATE_ON


async def test_reload(menuai: menuai) -> None:
    """Test reloading the media player from yaml."""
    menuai.states.async_set("input_boolean.test", STATE_OFF)
    menuai.states.async_set("media_player.mock1", STATE_OFF)

    templ = (
        '{% if states.input_boolean.test.state == "off" %}on'
        "{% else %}{{ states.media_player.mock1.state }}{% endif %}"
    )

    await async_setup_component(
        menuai,
        "media_player",
        {
            "media_player": {
                "platform": "universal",
                "name": "tv",
                "state_template": templ,
            }
        },
    )

    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == 3
    await menuai.async_start()

    await menuai.async_block_till_done()
    assert menuai.states.get("media_player.tv").state == STATE_ON

    menuai.states.async_set("input_boolean.test", STATE_ON)
    await menuai.async_block_till_done()

    assert menuai.states.get("media_player.tv").state == STATE_OFF

    menuai.states.async_set("media_player.master_bedroom_2", STATE_OFF)
    menuai.states.async_set(
        "remote.alexander_master_bedroom",
        STATE_ON,
        {"activity_list": ["act1", "act2"], "current_activity": "act2"},
    )

    yaml_path = get_fixture_path("configuration.yaml", "universal")
    with patch.object(menuai_config, "YAML_CONFIG_FILE", yaml_path):
        await menuai.services.async_call(
            "universal",
            SERVICE_RELOAD,
            {},
            blocking=True,
        )
        await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 5

    assert menuai.states.get("media_player.tv") is None
    assert menuai.states.get("media_player.master_bed_tv").state == "on"
    assert menuai.states.get("media_player.master_bed_tv").attributes["source"] == "act2"
    assert (
        "device_class" not in menuai.states.get("media_player.master_bed_tv").attributes
    )
    assert "unique_id" not in menuai.states.get("media_player.master_bed_tv").attributes
