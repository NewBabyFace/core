"""The tests for the Demo Media player platform."""

from http import HTTPStatus
from unittest.mock import patch

import pytest
import voluptuous as vol

from menuai.components.media_player import (
    ATTR_GROUP_MEMBERS,
    ATTR_INPUT_SOURCE,
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    ATTR_MEDIA_EPISODE,
    ATTR_MEDIA_REPEAT,
    ATTR_MEDIA_SEEK_POSITION,
    ATTR_MEDIA_TRACK,
    ATTR_MEDIA_VOLUME_LEVEL,
    ATTR_MEDIA_VOLUME_MUTED,
    DOMAIN as MP_DOMAIN,
    SERVICE_CLEAR_PLAYLIST,
    SERVICE_JOIN,
    SERVICE_PLAY_MEDIA,
    SERVICE_SELECT_SOURCE,
    SERVICE_UNJOIN,
    MediaPlayerEntityFeature,
    RepeatMode,
    is_on,
)
from menuai.const import (
    ATTR_ENTITY_ID,
    ATTR_ENTITY_PICTURE,
    ATTR_SUPPORTED_FEATURES,
    SERVICE_MEDIA_NEXT_TRACK,
    SERVICE_MEDIA_PAUSE,
    SERVICE_MEDIA_PLAY,
    SERVICE_MEDIA_PLAY_PAUSE,
    SERVICE_MEDIA_PREVIOUS_TRACK,
    SERVICE_MEDIA_SEEK,
    SERVICE_MEDIA_STOP,
    SERVICE_REPEAT_SET,
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    SERVICE_VOLUME_DOWN,
    SERVICE_VOLUME_MUTE,
    SERVICE_VOLUME_SET,
    SERVICE_VOLUME_UP,
    STATE_OFF,
    STATE_PAUSED,
    STATE_PLAYING,
    Platform,
)
from menuai.core import menuai
from menuai.helpers.aiohttp_client import DATA_CLIENTSESSION, _make_key
from menuai.setup import async_setup_component

from tests.typing import ClientSessionGenerator

TEST_ENTITY_ID = "media_player.walkman"


@pytest.fixture(autouse=True)
def autouse_disable_platforms(disable_platforms):
    """Auto use the disable_platforms fixture."""
    with patch(
        "menuai.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.MEDIA_PLAYER],
    ):
        yield


@pytest.fixture(name="mock_media_seek")
def media_player_media_seek_fixture():
    """Mock demo YouTube player media seek."""
    with patch(
        "menuai.components.demo.media_player.DemoYoutubePlayer.media_seek",
        autospec=True,
    ) as seek:
        yield seek


async def test_source_select(menuai: menuai) -> None:
    """Test the input source service."""
    entity_id = "media_player.lounge_room"

    assert await async_setup_component(
        menuai, MP_DOMAIN, {"media_player": {"platform": "demo"}}
    )
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.attributes.get(ATTR_INPUT_SOURCE) == "dvd"

    with pytest.raises(vol.Invalid):
        await menuai.services.async_call(
            MP_DOMAIN,
            SERVICE_SELECT_SOURCE,
            {ATTR_ENTITY_ID: entity_id, ATTR_INPUT_SOURCE: None},
            blocking=True,
        )
    state = menuai.states.get(entity_id)
    assert state.attributes.get(ATTR_INPUT_SOURCE) == "dvd"

    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_SELECT_SOURCE,
        {ATTR_ENTITY_ID: entity_id, ATTR_INPUT_SOURCE: "xbox"},
        blocking=True,
    )
    state = menuai.states.get(entity_id)
    assert state.attributes.get(ATTR_INPUT_SOURCE) == "xbox"


async def test_repeat_set(menuai: menuai) -> None:
    """Test the repeat set service."""
    entity_id = "media_player.walkman"

    assert await async_setup_component(
        menuai, MP_DOMAIN, {"media_player": {"platform": "demo"}}
    )
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.attributes.get(ATTR_MEDIA_REPEAT) == RepeatMode.OFF

    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_REPEAT_SET,
        {ATTR_ENTITY_ID: entity_id, ATTR_MEDIA_REPEAT: RepeatMode.ALL},
        blocking=True,
    )
    state = menuai.states.get(entity_id)
    assert state.attributes.get(ATTR_MEDIA_REPEAT) == RepeatMode.ALL


async def test_clear_playlist(menuai: menuai) -> None:
    """Test clear playlist."""
    assert await async_setup_component(
        menuai, MP_DOMAIN, {"media_player": {"platform": "demo"}}
    )
    await menuai.async_block_till_done()

    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == STATE_PLAYING

    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_CLEAR_PLAYLIST,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID},
        blocking=True,
    )
    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == STATE_OFF


async def test_volume_services(menuai: menuai) -> None:
    """Test the volume service."""
    assert await async_setup_component(
        menuai, MP_DOMAIN, {"media_player": {"platform": "demo"}}
    )
    await menuai.async_block_till_done()

    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.attributes.get(ATTR_MEDIA_VOLUME_LEVEL) == 1.0

    with pytest.raises(vol.Invalid):
        await menuai.services.async_call(
            MP_DOMAIN,
            SERVICE_VOLUME_SET,
            {ATTR_ENTITY_ID: TEST_ENTITY_ID, ATTR_MEDIA_VOLUME_LEVEL: None},
            blocking=True,
        )

    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.attributes.get(ATTR_MEDIA_VOLUME_LEVEL) == 1.0

    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID, ATTR_MEDIA_VOLUME_LEVEL: 0.5},
        blocking=True,
    )
    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.attributes.get(ATTR_MEDIA_VOLUME_LEVEL) == 0.5

    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_VOLUME_DOWN,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID},
        blocking=True,
    )
    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.attributes.get(ATTR_MEDIA_VOLUME_LEVEL) == 0.4

    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_VOLUME_UP,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID},
        blocking=True,
    )
    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.attributes.get(ATTR_MEDIA_VOLUME_LEVEL) == 0.5

    assert state.attributes.get(ATTR_MEDIA_VOLUME_MUTED) is False

    with pytest.raises(vol.Invalid):
        await menuai.services.async_call(
            MP_DOMAIN,
            SERVICE_VOLUME_MUTE,
            {ATTR_ENTITY_ID: TEST_ENTITY_ID, ATTR_MEDIA_VOLUME_MUTED: None},
            blocking=True,
        )

    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.attributes.get(ATTR_MEDIA_VOLUME_MUTED) is False

    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_VOLUME_MUTE,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID, ATTR_MEDIA_VOLUME_MUTED: True},
        blocking=True,
    )

    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.attributes.get(ATTR_MEDIA_VOLUME_MUTED) is True


async def test_turning_off_and_on(menuai: menuai) -> None:
    """Test turn_on and turn_off."""
    assert await async_setup_component(
        menuai, MP_DOMAIN, {"media_player": {"platform": "demo"}}
    )
    await menuai.async_block_till_done()

    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == STATE_PLAYING

    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID},
        blocking=True,
    )
    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == STATE_OFF
    assert not is_on(menuai, TEST_ENTITY_ID)

    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID},
        blocking=True,
    )
    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == STATE_PLAYING
    assert is_on(menuai, TEST_ENTITY_ID)

    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_TOGGLE,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID},
        blocking=True,
    )
    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == STATE_OFF
    assert not is_on(menuai, TEST_ENTITY_ID)


async def test_playing_pausing(menuai: menuai) -> None:
    """Test media_pause."""
    assert await async_setup_component(
        menuai, MP_DOMAIN, {"media_player": {"platform": "demo"}}
    )
    await menuai.async_block_till_done()

    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == STATE_PLAYING

    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_MEDIA_PAUSE,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID},
        blocking=True,
    )
    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == STATE_PAUSED

    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_MEDIA_PLAY_PAUSE,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID},
        blocking=True,
    )
    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == STATE_PLAYING

    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_MEDIA_PLAY_PAUSE,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID},
        blocking=True,
    )
    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == STATE_PAUSED

    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_MEDIA_PLAY,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID},
        blocking=True,
    )
    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == STATE_PLAYING


async def test_prev_next_track(menuai: menuai) -> None:
    """Test media_next_track and media_previous_track ."""
    assert await async_setup_component(
        menuai, MP_DOMAIN, {"media_player": {"platform": "demo"}}
    )
    await menuai.async_block_till_done()

    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.attributes.get(ATTR_MEDIA_TRACK) == 1

    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_MEDIA_NEXT_TRACK,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID},
        blocking=True,
    )
    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.attributes.get(ATTR_MEDIA_TRACK) == 2

    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_MEDIA_NEXT_TRACK,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID},
        blocking=True,
    )
    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.attributes.get(ATTR_MEDIA_TRACK) == 3

    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_MEDIA_PREVIOUS_TRACK,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID},
        blocking=True,
    )
    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.attributes.get(ATTR_MEDIA_TRACK) == 2

    assert await async_setup_component(
        menuai, MP_DOMAIN, {"media_player": {"platform": "demo"}}
    )
    await menuai.async_block_till_done()

    ent_id = "media_player.lounge_room"
    state = menuai.states.get(ent_id)
    assert state.attributes.get(ATTR_MEDIA_EPISODE) == "1"

    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_MEDIA_NEXT_TRACK,
        {ATTR_ENTITY_ID: ent_id},
        blocking=True,
    )
    state = menuai.states.get(ent_id)
    assert state.attributes.get(ATTR_MEDIA_EPISODE) == "2"

    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_MEDIA_PREVIOUS_TRACK,
        {ATTR_ENTITY_ID: ent_id},
        blocking=True,
    )
    state = menuai.states.get(ent_id)
    assert state.attributes.get(ATTR_MEDIA_EPISODE) == "1"


async def test_play_media(menuai: menuai) -> None:
    """Test play_media ."""
    assert await async_setup_component(
        menuai, MP_DOMAIN, {"media_player": {"platform": "demo"}}
    )
    await menuai.async_block_till_done()

    ent_id = "media_player.living_room"
    state = menuai.states.get(ent_id)
    assert (
        MediaPlayerEntityFeature.PLAY_MEDIA
        & state.attributes.get(ATTR_SUPPORTED_FEATURES)
        > 0
    )
    assert state.attributes.get(ATTR_MEDIA_CONTENT_ID) is not None

    with pytest.raises(vol.Invalid):
        await menuai.services.async_call(
            MP_DOMAIN,
            SERVICE_PLAY_MEDIA,
            {ATTR_ENTITY_ID: ent_id, ATTR_MEDIA_CONTENT_ID: "some_id"},
            blocking=True,
        )
    state = menuai.states.get(ent_id)
    assert (
        MediaPlayerEntityFeature.PLAY_MEDIA
        & state.attributes.get(ATTR_SUPPORTED_FEATURES)
        > 0
    )
    assert state.attributes.get(ATTR_MEDIA_CONTENT_ID) != "some_id"

    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_PLAY_MEDIA,
        {
            ATTR_ENTITY_ID: ent_id,
            ATTR_MEDIA_CONTENT_TYPE: "youtube",
            ATTR_MEDIA_CONTENT_ID: "some_id",
        },
        blocking=True,
    )
    state = menuai.states.get(ent_id)
    assert (
        MediaPlayerEntityFeature.PLAY_MEDIA
        & state.attributes.get(ATTR_SUPPORTED_FEATURES)
        > 0
    )
    assert state.attributes.get(ATTR_MEDIA_CONTENT_ID) == "some_id"


async def test_seek(menuai: menuai, mock_media_seek) -> None:
    """Test seek."""
    assert await async_setup_component(
        menuai, MP_DOMAIN, {"media_player": {"platform": "demo"}}
    )
    await menuai.async_block_till_done()

    ent_id = "media_player.living_room"
    state = menuai.states.get(ent_id)
    assert state.attributes[ATTR_SUPPORTED_FEATURES] & MediaPlayerEntityFeature.SEEK
    assert not mock_media_seek.called

    with pytest.raises(vol.Invalid):
        await menuai.services.async_call(
            MP_DOMAIN,
            SERVICE_MEDIA_SEEK,
            {
                ATTR_ENTITY_ID: ent_id,
                ATTR_MEDIA_SEEK_POSITION: None,
            },
            blocking=True,
        )
    assert not mock_media_seek.called

    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_MEDIA_SEEK,
        {
            ATTR_ENTITY_ID: ent_id,
            ATTR_MEDIA_SEEK_POSITION: 100,
        },
        blocking=True,
    )
    assert mock_media_seek.called


async def test_stop(menuai: menuai) -> None:
    """Test stop."""
    assert await async_setup_component(
        menuai, MP_DOMAIN, {"media_player": {"platform": "demo"}}
    )
    await menuai.async_block_till_done()

    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == STATE_PLAYING

    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_MEDIA_STOP,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID},
        blocking=True,
    )
    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == STATE_OFF


async def test_media_image_proxy(
    menuai: menuai, menuai_client: ClientSessionGenerator
) -> None:
    """Test the media server image proxy server ."""
    assert await async_setup_component(
        menuai, MP_DOMAIN, {"media_player": {"platform": "demo"}}
    )
    await menuai.async_block_till_done()

    fake_picture_data = "test.test"

    class MockResponse:
        """Test response."""

        def __init__(self) -> None:
            """Test response init."""
            self.status = 200
            self.headers = {"Content-Type": "sometype"}

        async def read(self):
            """Test response read."""
            return fake_picture_data.encode("ascii")

        async def release(self):
            """Test response release."""

    class MockWebsession:
        """Test websession."""

        async def get(self, url, **kwargs):
            """Test websession get."""
            return MockResponse()

        def detach(self):
            """Test websession detach."""

    menuai.data[DATA_CLIENTSESSION] = {_make_key(): MockWebsession()}

    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == STATE_PLAYING
    client = await menuai_client()
    req = await client.get(state.attributes.get(ATTR_ENTITY_PICTURE))
    assert req.status == HTTPStatus.OK
    assert await req.text() == fake_picture_data


async def test_grouping(menuai: menuai) -> None:
    """Test the join/unjoin services."""
    walkman = "media_player.walkman"
    kitchen = "media_player.kitchen"

    assert await async_setup_component(
        menuai, MP_DOMAIN, {"media_player": {"platform": "demo"}}
    )
    await menuai.async_block_till_done()
    state = menuai.states.get(walkman)
    assert state.attributes.get(ATTR_GROUP_MEMBERS) == []

    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_JOIN,
        {
            ATTR_ENTITY_ID: walkman,
            ATTR_GROUP_MEMBERS: [
                kitchen,
            ],
        },
        blocking=True,
    )
    state = menuai.states.get(walkman)
    assert state.attributes.get(ATTR_GROUP_MEMBERS) == [walkman, kitchen]

    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_UNJOIN,
        {ATTR_ENTITY_ID: walkman},
        blocking=True,
    )
    state = menuai.states.get(walkman)
    assert state.attributes.get(ATTR_GROUP_MEMBERS) == []
