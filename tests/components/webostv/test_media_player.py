"""The tests for the LG webOS TV media player platform."""

from datetime import timedelta
from http import HTTPStatus

from aiowebostv import WebOsTvPairError
from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.components import automation
from menuai.components.media_player import (
    ATTR_INPUT_SOURCE,
    ATTR_INPUT_SOURCE_LIST,
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    ATTR_MEDIA_TITLE,
    ATTR_MEDIA_VOLUME_LEVEL,
    ATTR_MEDIA_VOLUME_MUTED,
    DOMAIN as MP_DOMAIN,
    SERVICE_PLAY_MEDIA,
    SERVICE_SELECT_SOURCE,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from menuai.components.webostv.const import (
    ATTR_BUTTON,
    ATTR_PAYLOAD,
    ATTR_SOUND_OUTPUT,
    DOMAIN,
    LIVE_TV_APP_ID,
    SERVICE_BUTTON,
    SERVICE_COMMAND,
    SERVICE_SELECT_SOUND_OUTPUT,
    WebOsTvCommandError,
)
from menuai.components.webostv.media_player import (
    SUPPORT_WEBOSTV,
    SUPPORT_WEBOSTV_VOLUME,
)
from menuai.config_entries import SOURCE_REAUTH, ConfigEntryState
from menuai.const import (
    ATTR_COMMAND,
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    CONF_CLIENT_SECRET,
    ENTITY_MATCH_NONE,
    SERVICE_MEDIA_NEXT_TRACK,
    SERVICE_MEDIA_PAUSE,
    SERVICE_MEDIA_PLAY,
    SERVICE_MEDIA_PLAY_PAUSE,
    SERVICE_MEDIA_PREVIOUS_TRACK,
    SERVICE_MEDIA_STOP,
    SERVICE_TURN_OFF,
    SERVICE_VOLUME_DOWN,
    SERVICE_VOLUME_MUTE,
    SERVICE_VOLUME_SET,
    SERVICE_VOLUME_UP,
    STATE_OFF,
)
from menuai.core import menuai, State
from menuai.exceptions import menuaiError
from menuai.helpers import device_registry as dr
from menuai.setup import async_setup_component

from . import setup_webostv
from .const import CHANNEL_2, ENTITY_ID, TV_NAME

from tests.common import async_fire_time_changed, mock_restore_cache
from tests.test_util.aiohttp import AiohttpClientMocker
from tests.typing import ClientSessionGenerator


@pytest.mark.parametrize(
    ("service", "attr_data", "client_call"),
    [
        (SERVICE_VOLUME_MUTE, {ATTR_MEDIA_VOLUME_MUTED: True}, ("set_mute", True)),
        (SERVICE_VOLUME_MUTE, {ATTR_MEDIA_VOLUME_MUTED: False}, ("set_mute", False)),
        (SERVICE_VOLUME_SET, {ATTR_MEDIA_VOLUME_LEVEL: 1.00}, ("set_volume", 100)),
        (SERVICE_VOLUME_SET, {ATTR_MEDIA_VOLUME_LEVEL: 0.54}, ("set_volume", 54)),
        (SERVICE_VOLUME_SET, {ATTR_MEDIA_VOLUME_LEVEL: 0.0}, ("set_volume", 0)),
    ],
)
async def test_services_with_parameters(
    menuai: menuai, client, service, attr_data, client_call
) -> None:
    """Test services that has parameters in calls."""
    await setup_webostv(menuai)

    data = {ATTR_ENTITY_ID: ENTITY_ID, **attr_data}
    await menuai.services.async_call(MP_DOMAIN, service, data, True)

    getattr(client, client_call[0]).assert_called_once_with(client_call[1])


@pytest.mark.parametrize(
    ("service", "client_call"),
    [
        (SERVICE_TURN_OFF, "power_off"),
        (SERVICE_VOLUME_UP, "volume_up"),
        (SERVICE_VOLUME_DOWN, "volume_down"),
        (SERVICE_MEDIA_PLAY, "play"),
        (SERVICE_MEDIA_PAUSE, "pause"),
        (SERVICE_MEDIA_STOP, "stop"),
    ],
)
async def test_services(menuai: menuai, client, service, client_call) -> None:
    """Test simple services without parameters."""
    await setup_webostv(menuai)

    data = {ATTR_ENTITY_ID: ENTITY_ID}
    await menuai.services.async_call(MP_DOMAIN, service, data, True)

    getattr(client, client_call).assert_called_once()


async def test_media_play_pause(menuai: menuai, client) -> None:
    """Test media play pause service."""
    await setup_webostv(menuai)

    data = {ATTR_ENTITY_ID: ENTITY_ID}

    # After init state is playing - check pause call
    await menuai.services.async_call(MP_DOMAIN, SERVICE_MEDIA_PLAY_PAUSE, data, True)

    client.pause.assert_called_once()
    client.play.assert_not_called()

    # After pause state is paused - check play call
    await menuai.services.async_call(MP_DOMAIN, SERVICE_MEDIA_PLAY_PAUSE, data, True)

    client.play.assert_called_once()
    client.pause.assert_called_once()


@pytest.mark.parametrize(
    ("service", "client_call"),
    [
        (SERVICE_MEDIA_NEXT_TRACK, ("fast_forward", "channel_up")),
        (SERVICE_MEDIA_PREVIOUS_TRACK, ("rewind", "channel_down")),
    ],
)
async def test_media_next_previous_track(
    menuai: menuai, client, service, client_call
) -> None:
    """Test media next/previous track services."""
    await setup_webostv(menuai)

    # check channel up/down for live TV channels
    data = {ATTR_ENTITY_ID: ENTITY_ID}
    await menuai.services.async_call(MP_DOMAIN, service, data, True)

    getattr(client, client_call[0]).assert_not_called()
    getattr(client, client_call[1]).assert_called_once()

    # check next/previous for not Live TV channels
    client.tv_state.current_app_id = "in1"
    data = {ATTR_ENTITY_ID: ENTITY_ID}
    await menuai.services.async_call(MP_DOMAIN, service, data, True)

    getattr(client, client_call[0]).assert_called_once()
    getattr(client, client_call[1]).assert_called_once()


async def test_select_source_with_empty_source_list(
    menuai: menuai, client
) -> None:
    """Ensure we don't call client methods when we don't have sources."""
    await setup_webostv(menuai)
    await client.mock_state_update()

    data = {
        ATTR_ENTITY_ID: ENTITY_ID,
        ATTR_INPUT_SOURCE: "nonexistent",
    }
    with pytest.raises(
        menuaiError,
        match=f"Source nonexistent not found in the sources list for {TV_NAME}",
    ):
        await menuai.services.async_call(MP_DOMAIN, SERVICE_SELECT_SOURCE, data, True)

    client.launch_app.assert_not_called()
    client.set_input.assert_not_called()


async def test_select_app_source(menuai: menuai, client) -> None:
    """Test select app source."""
    await setup_webostv(menuai)
    await client.mock_state_update()

    data = {
        ATTR_ENTITY_ID: ENTITY_ID,
        ATTR_INPUT_SOURCE: "Live TV",
    }
    await menuai.services.async_call(MP_DOMAIN, SERVICE_SELECT_SOURCE, data, True)

    client.launch_app.assert_called_once_with(LIVE_TV_APP_ID)
    client.set_input.assert_not_called()


async def test_select_input_source(menuai: menuai, client) -> None:
    """Test select input source."""
    await setup_webostv(menuai)
    await client.mock_state_update()

    data = {
        ATTR_ENTITY_ID: ENTITY_ID,
        ATTR_INPUT_SOURCE: "Input01",
    }
    await menuai.services.async_call(MP_DOMAIN, SERVICE_SELECT_SOURCE, data, True)

    client.launch_app.assert_not_called()
    client.set_input.assert_called_once_with("in1")


async def test_button(menuai: menuai, client) -> None:
    """Test generic button functionality."""
    await setup_webostv(menuai)

    data = {
        ATTR_ENTITY_ID: ENTITY_ID,
        ATTR_BUTTON: "test",
    }
    await menuai.services.async_call(DOMAIN, SERVICE_BUTTON, data, True)
    await menuai.async_block_till_done()
    client.button.assert_called_once()
    client.button.assert_called_with("test")


async def test_command(
    menuai: menuai,
    client,
    snapshot: SnapshotAssertion,
) -> None:
    """Test generic command functionality."""
    await setup_webostv(menuai)
    client.request.return_value = {
        "returnValue": True,
        "scenario": "mastervolume_tv_speaker_ext",
        "volume": 1,
        "muted": False,
    }

    data = {
        ATTR_ENTITY_ID: ENTITY_ID,
        ATTR_COMMAND: "audio/getVolume",
    }
    response = await menuai.services.async_call(
        DOMAIN, SERVICE_COMMAND, data, True, return_response=True
    )
    await menuai.async_block_till_done()
    client.request.assert_called_with("audio/getVolume", payload=None)
    assert response == snapshot


async def test_command_with_optional_arg(menuai: menuai, client) -> None:
    """Test generic command functionality."""
    await setup_webostv(menuai)

    data = {
        ATTR_ENTITY_ID: ENTITY_ID,
        ATTR_COMMAND: "test",
        ATTR_PAYLOAD: {"target": "https://www.google.com"},
    }
    await menuai.services.async_call(DOMAIN, SERVICE_COMMAND, data, True)
    await menuai.async_block_till_done()
    client.request.assert_called_with(
        "test", payload={"target": "https://www.google.com"}
    )


async def test_select_sound_output(
    menuai: menuai,
    client,
    snapshot: SnapshotAssertion,
) -> None:
    """Test select sound output service."""
    await setup_webostv(menuai)
    client.change_sound_output.return_value = {
        "returnValue": True,
        "method": "setSystemSettings",
    }

    data = {
        ATTR_ENTITY_ID: ENTITY_ID,
        ATTR_SOUND_OUTPUT: "external_speaker",
    }
    response = await menuai.services.async_call(
        DOMAIN,
        SERVICE_SELECT_SOUND_OUTPUT,
        data,
        True,
        return_response=True,
    )
    await menuai.async_block_till_done()
    client.change_sound_output.assert_called_once_with("external_speaker")
    assert response == snapshot


async def test_device_info_startup_off(
    menuai: menuai, client, device_registry: dr.DeviceRegistry
) -> None:
    """Test device info when device is off at startup."""
    client.tv_info.system = {}
    client.tv_state.is_on = False
    entry = await setup_webostv(menuai)
    await client.mock_state_update()

    assert menuai.states.get(ENTITY_ID).state == STATE_OFF

    device = device_registry.async_get_device(identifiers={(DOMAIN, entry.unique_id)})

    assert device
    assert device.identifiers == {(DOMAIN, entry.unique_id)}
    assert device.manufacturer == "LG"
    assert device.name == TV_NAME
    assert device.sw_version is None
    assert device.model is None


async def test_entity_attributes(
    menuai: menuai,
    client,
    device_registry: dr.DeviceRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test entity attributes."""
    entry = await setup_webostv(menuai)
    await client.mock_state_update()

    # Attributes when device is on
    state = menuai.states.get(ENTITY_ID)
    assert state == snapshot(exclude=props("entity_picture"))

    # Volume level not available
    client.tv_state.volume = None
    await client.mock_state_update()
    attrs = menuai.states.get(ENTITY_ID).attributes

    assert attrs.get(ATTR_MEDIA_VOLUME_LEVEL) is None

    # Channel change
    client.tv_state.current_channel = CHANNEL_2
    await client.mock_state_update()
    attrs = menuai.states.get(ENTITY_ID).attributes

    assert attrs[ATTR_MEDIA_TITLE] == "Channel Name 2"

    # Device Info
    device = device_registry.async_get_device(identifiers={(DOMAIN, entry.unique_id)})
    assert device == snapshot

    # Sound output when off
    client.tv_state.sound_output = None
    client.tv_state.is_on = False
    await client.mock_state_update()
    state = menuai.states.get(ENTITY_ID)

    assert state.state == STATE_OFF
    assert state.attributes.get(ATTR_SOUND_OUTPUT) is None


async def test_service_entity_id_none(menuai: menuai, client) -> None:
    """Test service call with none as entity id."""
    await setup_webostv(menuai)

    data = {
        ATTR_ENTITY_ID: ENTITY_MATCH_NONE,
        ATTR_SOUND_OUTPUT: "external_speaker",
    }
    await menuai.services.async_call(DOMAIN, SERVICE_SELECT_SOUND_OUTPUT, data, True)

    client.change_sound_output.assert_not_called()


@pytest.mark.parametrize(
    ("media_id", "ch_id"),
    [
        ("Channel 1", "ch1id"),  # Perfect Match by channel name
        ("Name 2", "ch2id"),  # Partial Match by channel name
        ("20", "ch2id"),  # Perfect Match by channel number
    ],
)
async def test_play_media(menuai: menuai, client, media_id, ch_id) -> None:
    """Test play media service."""
    await setup_webostv(menuai)
    await client.mock_state_update()

    data = {
        ATTR_ENTITY_ID: ENTITY_ID,
        ATTR_MEDIA_CONTENT_TYPE: MediaType.CHANNEL,
        ATTR_MEDIA_CONTENT_ID: media_id,
    }
    await menuai.services.async_call(MP_DOMAIN, SERVICE_PLAY_MEDIA, data, True)

    client.set_channel.assert_called_once_with(ch_id)


async def test_update_sources_live_tv_find(menuai: menuai, client) -> None:
    """Test finding live TV app id in update sources."""
    await setup_webostv(menuai)
    await client.mock_state_update()

    # Live TV found in app list
    sources = menuai.states.get(ENTITY_ID).attributes[ATTR_INPUT_SOURCE_LIST]

    assert "Live TV" in sources
    assert len(sources) == 3

    # Live TV is current app
    client.tv_state.apps = {
        LIVE_TV_APP_ID: {
            "title": "Live TV",
            "id": "some_id",
        },
    }
    client.tv_state.current_app_id = "some_id"
    await client.mock_state_update()
    sources = menuai.states.get(ENTITY_ID).attributes[ATTR_INPUT_SOURCE_LIST]

    assert "Live TV" in sources
    assert len(sources) == 3

    # Live TV is is in inputs
    client.tv_state.inputs = {
        LIVE_TV_APP_ID: {
            "label": "Live TV",
            "id": "some_id",
            "appId": LIVE_TV_APP_ID,
        },
    }
    await client.mock_state_update()
    sources = menuai.states.get(ENTITY_ID).attributes[ATTR_INPUT_SOURCE_LIST]

    assert "Live TV" in sources
    assert len(sources) == 1

    # Live TV is current input
    client.tv_state.inputs = {
        LIVE_TV_APP_ID: {
            "label": "Live TV",
            "id": "some_id",
            "appId": "some_id",
        },
    }
    await client.mock_state_update()
    sources = menuai.states.get(ENTITY_ID).attributes[ATTR_INPUT_SOURCE_LIST]

    assert "Live TV" in sources
    assert len(sources) == 1

    # Live TV not found
    client.tv_state.current_app_id = "other_id"
    await client.mock_state_update()
    sources = menuai.states.get(ENTITY_ID).attributes[ATTR_INPUT_SOURCE_LIST]

    assert "Live TV" in sources
    assert len(sources) == 1

    # Live TV not found in sources/apps but is current app
    client.tv_state.apps = {}
    client.tv_state.current_app_id = LIVE_TV_APP_ID
    await client.mock_state_update()
    sources = menuai.states.get(ENTITY_ID).attributes[ATTR_INPUT_SOURCE_LIST]

    assert "Live TV" in sources
    assert len(sources) == 1

    # Bad update, keep old update
    client.tv_state.inputs = {}
    await client.mock_state_update()
    sources = menuai.states.get(ENTITY_ID).attributes[ATTR_INPUT_SOURCE_LIST]

    assert "Live TV" in sources
    assert len(sources) == 1


async def test_client_disconnected(
    menuai: menuai,
    client,
    caplog: pytest.LogCaptureFixture,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test error not raised when client is disconnected."""
    await setup_webostv(menuai)
    client.is_connected.return_value = False
    client.connect.side_effect = TimeoutError

    freezer.tick(timedelta(seconds=20))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert "TimeoutError" not in caplog.text


async def test_client_key_update_on_connect(
    menuai: menuai, client, freezer: FrozenDateTimeFactory
) -> None:
    """Test client key update upon connect."""
    config_entry = await setup_webostv(menuai)

    assert config_entry.data[CONF_CLIENT_SECRET] == client.client_key

    client.is_connected.return_value = False
    client.client_key = "new_key"

    freezer.tick(timedelta(seconds=20))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert config_entry.data[CONF_CLIENT_SECRET] == client.client_key


@pytest.mark.parametrize(
    ("is_on", "exception", "error_message"),
    [
        (
            True,
            WebOsTvCommandError("Some error"),
            f"Communication error while calling async_media_play for device {TV_NAME}: Some error",
        ),
        (
            True,
            WebOsTvCommandError("Some other error"),
            f"Communication error while calling async_media_play for device {TV_NAME}: Some other error",
        ),
        (
            False,
            None,
            f"Error calling async_media_play for device {TV_NAME}: Device is off and cannot be controlled",
        ),
    ],
)
async def test_control_error_handling(
    menuai: menuai,
    client,
    is_on: bool,
    exception: Exception,
    error_message: str,
) -> None:
    """Test control errors handling."""
    await setup_webostv(menuai)
    client.play.side_effect = exception
    client.tv_state.is_on = is_on
    await client.mock_state_update()

    data = {ATTR_ENTITY_ID: ENTITY_ID}
    with pytest.raises(menuaiError, match=error_message):
        await menuai.services.async_call(MP_DOMAIN, SERVICE_MEDIA_PLAY, data, True)

    assert client.play.call_count == int(is_on)


async def test_turn_off_when_device_is_off(menuai: menuai, client) -> None:
    """Test no error when turning off device that is already off."""
    await setup_webostv(menuai)
    client.is_on = False
    await client.mock_state_update()

    data = {ATTR_ENTITY_ID: ENTITY_ID}
    await menuai.services.async_call(MP_DOMAIN, SERVICE_TURN_OFF, data, True)
    assert client.power_off.call_count == 1


async def test_supported_features(menuai: menuai, client) -> None:
    """Test test supported features."""
    client.tv_state.sound_output = "lineout"
    await setup_webostv(menuai)
    await client.mock_state_update()

    # No sound control support
    supported = SUPPORT_WEBOSTV
    attrs = menuai.states.get(ENTITY_ID).attributes

    assert attrs[ATTR_SUPPORTED_FEATURES] == supported

    # Support volume mute, step
    client.tv_state.sound_output = "external_speaker"
    await client.mock_state_update()
    supported = supported | SUPPORT_WEBOSTV_VOLUME
    attrs = menuai.states.get(ENTITY_ID).attributes

    assert attrs[ATTR_SUPPORTED_FEATURES] == supported

    # Support volume mute, step, set
    client.tv_state.sound_output = "speaker"
    await client.mock_state_update()
    supported = supported | SUPPORT_WEBOSTV_VOLUME | MediaPlayerEntityFeature.VOLUME_SET
    attrs = menuai.states.get(ENTITY_ID).attributes

    assert attrs[ATTR_SUPPORTED_FEATURES] == supported

    # Support turn on
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {
                        "platform": "webostv.turn_on",
                        "entity_id": ENTITY_ID,
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": ENTITY_ID,
                            "id": "{{ trigger.id }}",
                        },
                    },
                },
            ],
        },
    )
    supported |= MediaPlayerEntityFeature.TURN_ON
    await client.mock_state_update()
    attrs = menuai.states.get(ENTITY_ID).attributes

    assert attrs[ATTR_SUPPORTED_FEATURES] == supported


async def test_cached_supported_features(menuai: menuai, client) -> None:
    """Test test supported features."""
    client.tv_state.is_on = False
    client.tv_state.sound_output = None
    supported = (
        SUPPORT_WEBOSTV | SUPPORT_WEBOSTV_VOLUME | MediaPlayerEntityFeature.TURN_ON
    )
    mock_restore_cache(
        menuai,
        [
            State(
                ENTITY_ID,
                STATE_OFF,
                attributes={
                    ATTR_SUPPORTED_FEATURES: supported,
                },
            )
        ],
    )
    await setup_webostv(menuai)
    await client.mock_state_update()

    # TV off, restored state supports mute, step
    # validate MediaPlayerEntityFeature.TURN_ON is not cached
    attrs = menuai.states.get(ENTITY_ID).attributes

    assert (
        attrs[ATTR_SUPPORTED_FEATURES] == supported & ~MediaPlayerEntityFeature.TURN_ON
    )

    # TV on, support volume mute, step
    client.tv_state.is_on = True
    client.tv_state.sound_output = "external_speaker"
    await client.mock_state_update()

    supported = SUPPORT_WEBOSTV | SUPPORT_WEBOSTV_VOLUME
    attrs = menuai.states.get(ENTITY_ID).attributes

    assert attrs[ATTR_SUPPORTED_FEATURES] == supported

    # TV off, support volume mute, step
    client.tv_state.is_on = False
    client.tv_state.sound_output = None
    await client.mock_state_update()

    supported = SUPPORT_WEBOSTV | SUPPORT_WEBOSTV_VOLUME
    attrs = menuai.states.get(ENTITY_ID).attributes

    assert attrs[ATTR_SUPPORTED_FEATURES] == supported

    # TV on, support volume mute, step, set
    client.tv_state.is_on = True
    client.tv_state.sound_output = "speaker"
    await client.mock_state_update()

    supported = (
        SUPPORT_WEBOSTV | SUPPORT_WEBOSTV_VOLUME | MediaPlayerEntityFeature.VOLUME_SET
    )
    attrs = menuai.states.get(ENTITY_ID).attributes

    assert attrs[ATTR_SUPPORTED_FEATURES] == supported

    # TV off, support volume mute, step, set
    client.tv_state.is_on = False
    client.tv_state.sound_output = None
    await client.mock_state_update()

    supported = (
        SUPPORT_WEBOSTV | SUPPORT_WEBOSTV_VOLUME | MediaPlayerEntityFeature.VOLUME_SET
    )
    attrs = menuai.states.get(ENTITY_ID).attributes

    assert attrs[ATTR_SUPPORTED_FEATURES] == supported

    # Test support turn on is updated on cached state
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {
                        "platform": "webostv.turn_on",
                        "entity_id": ENTITY_ID,
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": ENTITY_ID,
                            "id": "{{ trigger.id }}",
                        },
                    },
                },
            ],
        },
    )
    await client.mock_state_update()

    attrs = menuai.states.get(ENTITY_ID).attributes

    assert (
        attrs[ATTR_SUPPORTED_FEATURES] == supported | MediaPlayerEntityFeature.TURN_ON
    )


async def test_supported_features_no_cache(menuai: menuai, client) -> None:
    """Test supported features if device is off and no cache."""
    client.tv_state.is_on = False
    client.tv_state.sound_output = None
    await setup_webostv(menuai)

    supported = (
        SUPPORT_WEBOSTV | SUPPORT_WEBOSTV_VOLUME | MediaPlayerEntityFeature.VOLUME_SET
    )
    attrs = menuai.states.get(ENTITY_ID).attributes

    assert attrs[ATTR_SUPPORTED_FEATURES] == supported


async def test_supported_features_ignore_cache(menuai: menuai, client) -> None:
    """Test ignore cached supported features if device is on at startup."""
    mock_restore_cache(
        menuai,
        [
            State(
                ENTITY_ID,
                STATE_OFF,
                attributes={
                    ATTR_SUPPORTED_FEATURES: SUPPORT_WEBOSTV | SUPPORT_WEBOSTV_VOLUME,
                },
            )
        ],
    )
    await setup_webostv(menuai)

    supported = (
        SUPPORT_WEBOSTV | SUPPORT_WEBOSTV_VOLUME | MediaPlayerEntityFeature.VOLUME_SET
    )
    attrs = menuai.states.get(ENTITY_ID).attributes

    assert attrs[ATTR_SUPPORTED_FEATURES] == supported


async def test_get_image_http(
    menuai: menuai,
    client,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test get image via http."""
    url = "http://something/valid_icon"
    client.tv_state.apps[LIVE_TV_APP_ID]["icon"] = url
    await setup_webostv(menuai)
    await client.mock_state_update()

    attrs = menuai.states.get(ENTITY_ID).attributes
    assert "entity_picture_local" not in attrs

    aioclient_mock.get(url, text="image")
    client = await menuai_client_no_auth()

    resp = await client.get(attrs["entity_picture"])
    content = await resp.read()

    assert content == b"image"


async def test_get_image_http_error(
    menuai: menuai,
    client,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test get image via http error."""
    url = "http://something/icon_error"
    client.tv_state.apps[LIVE_TV_APP_ID]["icon"] = url
    await setup_webostv(menuai)
    await client.mock_state_update()

    attrs = menuai.states.get(ENTITY_ID).attributes
    assert "entity_picture_local" not in attrs

    aioclient_mock.get(url, exc=TimeoutError())
    client = await menuai_client_no_auth()

    resp = await client.get(attrs["entity_picture"])
    content = await resp.read()

    assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert f"Error retrieving proxied image from {url}" in caplog.text
    assert content == b""


async def test_get_image_https(
    menuai: menuai,
    client,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test get image via http."""
    url = "https://something/valid_icon_https"
    client.tv_state.apps[LIVE_TV_APP_ID]["icon"] = url
    await setup_webostv(menuai)
    await client.mock_state_update()

    attrs = menuai.states.get(ENTITY_ID).attributes
    assert "entity_picture_local" not in attrs

    aioclient_mock.get(url, text="https_image")
    client = await menuai_client_no_auth()

    resp = await client.get(attrs["entity_picture"])
    content = await resp.read()

    assert content == b"https_image"


async def test_reauth_reconnect(
    menuai: menuai, client, freezer: FrozenDateTimeFactory
) -> None:
    """Test reauth flow triggered by reconnect."""
    entry = await setup_webostv(menuai)
    client.is_connected.return_value = False
    client.connect.side_effect = WebOsTvPairError

    assert entry.state is ConfigEntryState.LOADED

    freezer.tick(timedelta(seconds=20))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1

    flow = flows[0]
    assert flow.get("step_id") == "reauth_confirm"
    assert flow.get("handler") == DOMAIN

    assert "context" in flow
    assert flow["context"].get("source") == SOURCE_REAUTH
    assert flow["context"].get("entry_id") == entry.entry_id


async def test_update_media_state(menuai: menuai, client) -> None:
    """Test updating media state."""
    await setup_webostv(menuai)

    client.tv_state.media_state = [{"playState": "playing"}]
    await client.mock_state_update()
    assert menuai.states.get(ENTITY_ID).state == MediaPlayerState.PLAYING

    client.tv_state.media_state = [{"playState": "paused"}]
    await client.mock_state_update()
    assert menuai.states.get(ENTITY_ID).state == MediaPlayerState.PAUSED

    client.tv_state.media_state = [{"playState": "unloaded"}]
    await client.mock_state_update()
    assert menuai.states.get(ENTITY_ID).state == MediaPlayerState.IDLE

    client.tv_state.is_on = False
    await client.mock_state_update()
    assert menuai.states.get(ENTITY_ID).state == STATE_OFF
