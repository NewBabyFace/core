"""Tests for samsungtv component."""

from copy import deepcopy
from datetime import timedelta
import logging
from unittest.mock import DEFAULT as DEFAULT_MOCK, AsyncMock, Mock, call, patch

from async_upnp_client.exceptions import (
    UpnpActionResponseError,
    UpnpCommunicationError,
    UpnpConnectionError,
    UpnpError,
    UpnpResponseError,
)
from freezegun.api import FrozenDateTimeFactory
import pytest
from samsungctl import exceptions
from samsungtvws.async_remote import SamsungTVWSAsyncRemote
from samsungtvws.command import SamsungTVSleepCommand
from samsungtvws.encrypted.remote import (
    SamsungTVEncryptedCommand,
    SamsungTVEncryptedWSAsyncRemote,
)
from samsungtvws.exceptions import ConnectionFailure, HttpApiError, UnauthorizedError
from samsungtvws.remote import ChannelEmitCommand, SendRemoteKey
from websockets.exceptions import ConnectionClosedError, WebSocketException

from menuai.components.media_player import (
    ATTR_INPUT_SOURCE,
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    ATTR_MEDIA_VOLUME_LEVEL,
    ATTR_MEDIA_VOLUME_MUTED,
    DOMAIN as MP_DOMAIN,
    SERVICE_PLAY_MEDIA,
    SERVICE_SELECT_SOURCE,
    MediaPlayerDeviceClass,
    MediaType,
)
from menuai.components.samsungtv.const import (
    CONF_SSDP_RENDERING_CONTROL_LOCATION,
    DOMAIN,
    ENCRYPTED_WEBSOCKET_PORT,
    ENTRY_RELOAD_COOLDOWN,
    METHOD_ENCRYPTED_WEBSOCKET,
    METHOD_WEBSOCKET,
    TIMEOUT_WEBSOCKET,
)
from menuai.components.samsungtv.media_player import SUPPORT_SAMSUNGTV
from menuai.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    ATTR_FRIENDLY_NAME,
    ATTR_SUPPORTED_FEATURES,
    CONF_HOST,
    CONF_MAC,
    CONF_METHOD,
    CONF_MODEL,
    CONF_NAME,
    CONF_PORT,
    CONF_TIMEOUT,
    CONF_TOKEN,
    SERVICE_MEDIA_NEXT_TRACK,
    SERVICE_MEDIA_PAUSE,
    SERVICE_MEDIA_PLAY,
    SERVICE_MEDIA_PLAY_PAUSE,
    SERVICE_MEDIA_PREVIOUS_TRACK,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    SERVICE_VOLUME_DOWN,
    SERVICE_VOLUME_MUTE,
    SERVICE_VOLUME_SET,
    SERVICE_VOLUME_UP,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError, ServiceNotSupported
from menuai.setup import async_setup_component

from . import setup_samsungtv_entry
from .const import (
    ENTRYDATA_ENCRYPTED_WEBSOCKET,
    ENTRYDATA_LEGACY,
    ENTRYDATA_WEBSOCKET,
    SAMPLE_DEVICE_INFO_WIFI,
)

from tests.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_load_json_object_fixture,
)

ENTITY_ID = f"{MP_DOMAIN}.mock_title"
MOCK_CONFIGWS = {
    CONF_HOST: "fake_host",
    CONF_NAME: "fake",
    CONF_PORT: 8001,
    CONF_TOKEN: "123456789",
    CONF_METHOD: METHOD_WEBSOCKET,
}
MOCK_CALLS_WS = {
    CONF_HOST: "fake_host",
    CONF_PORT: 8001,
    CONF_TOKEN: "123456789",
    CONF_TIMEOUT: TIMEOUT_WEBSOCKET,
    CONF_NAME: "menuai",
}

MOCK_ENTRY_WS = {
    CONF_HOST: "fake_host",
    CONF_METHOD: "websocket",
    CONF_NAME: "fake",
    CONF_PORT: 8001,
    CONF_TOKEN: "123456789",
    CONF_SSDP_RENDERING_CONTROL_LOCATION: "https://any",
}


@pytest.mark.usefixtures("remote_legacy")
async def test_setup(menuai: menuai) -> None:
    """Test setup of platform."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)
    assert menuai.states.get(ENTITY_ID)


@pytest.mark.usefixtures("remote_websocket", "rest_api")
async def test_setup_websocket(menuai: menuai) -> None:
    """Test setup of platform."""
    with patch(
        "menuai.components.samsungtv.bridge.SamsungTVWSAsyncRemote"
    ) as remote_class:
        remote = Mock(SamsungTVWSAsyncRemote)
        remote.__aenter__ = AsyncMock(return_value=remote)
        remote.__aexit__ = AsyncMock()
        remote.token = "123456789"
        remote_class.return_value = remote

        await setup_samsungtv_entry(menuai, MOCK_CONFIGWS)

        assert remote_class.call_count == 1
        assert remote_class.call_args_list == [call(**MOCK_CALLS_WS)]
        assert menuai.states.get(ENTITY_ID)

        await menuai.async_block_till_done()

        config_entries = menuai.config_entries.async_entries(DOMAIN)
        assert len(config_entries) == 1
        assert config_entries[0].data[CONF_MAC] == "aa:bb:aa:aa:aa:aa"


@pytest.mark.usefixtures("rest_api")
async def test_setup_websocket_2(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test setup of platform from config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_ENTRY_WS,
    )
    entry.add_to_menuai(menuai)

    config_entries = menuai.config_entries.async_entries(DOMAIN)
    assert len(config_entries) == 1
    assert entry is config_entries[0]

    with patch(
        "menuai.components.samsungtv.bridge.SamsungTVWSAsyncRemote"
    ) as remote_class:
        remote = Mock(SamsungTVWSAsyncRemote)
        remote.__aenter__ = AsyncMock(return_value=remote)
        remote.__aexit__ = AsyncMock()
        remote.token = "987654321"
        remote_class.return_value = remote
        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

        assert config_entries[0].data[CONF_MAC] == "aa:bb:aa:aa:aa:aa"

        freezer.tick(timedelta(minutes=5))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get(ENTITY_ID)
    assert state
    remote_class.assert_called_once_with(**MOCK_CALLS_WS)


@pytest.mark.usefixtures("rest_api")
async def test_setup_encrypted_websocket(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test setup of platform from config entry."""
    with patch(
        "menuai.components.samsungtv.bridge.SamsungTVEncryptedWSAsyncRemote"
    ) as remote_class:
        remote = Mock(SamsungTVEncryptedWSAsyncRemote)
        remote.__aenter__ = AsyncMock(return_value=remote)
        remote.__aexit__ = AsyncMock()
        remote_class.return_value = remote

        await setup_samsungtv_entry(menuai, ENTRYDATA_ENCRYPTED_WEBSOCKET)

        freezer.tick(timedelta(minutes=5))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get(ENTITY_ID)
    assert state
    remote_class.assert_called_once()


@pytest.mark.usefixtures("remote_legacy")
async def test_update_on(menuai: menuai, freezer: FrozenDateTimeFactory) -> None:
    """Testing update tv on."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)

    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("remote_legacy")
async def test_update_off(menuai: menuai, freezer: FrozenDateTimeFactory) -> None:
    """Testing update tv off."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)

    with patch(
        "menuai.components.samsungtv.bridge.Remote",
        side_effect=[OSError("Boom"), DEFAULT_MOCK],
    ):
        freezer.tick(timedelta(minutes=5))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

        state = menuai.states.get(ENTITY_ID)
        assert state.state == STATE_UNAVAILABLE


async def test_update_off_ws_no_power_state(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    remote_websocket: Mock,
    rest_api: Mock,
) -> None:
    """Testing update tv off."""
    await setup_samsungtv_entry(menuai, MOCK_CONFIGWS)
    # device_info should only get called once, as part of the setup
    rest_api.rest_device_info.assert_called_once()
    rest_api.rest_device_info.reset_mock()

    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_ON

    remote_websocket.start_listening = Mock(side_effect=WebSocketException("Boom"))
    remote_websocket.is_alive.return_value = False

    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_OFF
    rest_api.rest_device_info.assert_not_called()


@pytest.mark.usefixtures("remote_websocket")
async def test_update_off_ws_with_power_state(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    remote_websocket: Mock,
    rest_api: Mock,
) -> None:
    """Testing update tv off."""
    with (
        patch.object(
            rest_api, "rest_device_info", side_effect=HttpApiError
        ) as mock_device_info,
        patch.object(
            remote_websocket, "start_listening", side_effect=WebSocketException("Boom")
        ) as mock_start_listening,
    ):
        await setup_samsungtv_entry(menuai, MOCK_CONFIGWS)

        mock_device_info.assert_called_once()
        mock_start_listening.assert_called_once()

    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_UNAVAILABLE

    # First update uses start_listening once, and initialises device_info
    device_info = deepcopy(SAMPLE_DEVICE_INFO_WIFI)
    device_info["device"]["PowerState"] = "on"
    rest_api.rest_device_info.return_value = device_info

    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    remote_websocket.start_listening.assert_called_once()
    rest_api.rest_device_info.assert_called_once()

    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_ON

    # After initial update, start_listening shouldn't be called
    remote_websocket.start_listening.reset_mock()

    # Second update uses device_info(ON)
    rest_api.rest_device_info.reset_mock()

    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    rest_api.rest_device_info.assert_called_once()

    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_ON

    # Third update uses device_info (OFF)
    rest_api.rest_device_info.reset_mock()
    device_info["device"]["PowerState"] = "off"

    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    rest_api.rest_device_info.assert_called_once()

    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_UNAVAILABLE

    remote_websocket.start_listening.assert_not_called()


async def test_update_off_encryptedws(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    remote_encrypted_websocket: Mock,
    rest_api: Mock,
) -> None:
    """Testing update tv off."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_ENCRYPTED_WEBSOCKET)

    rest_api.rest_device_info.assert_called_once()

    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_ON

    remote_encrypted_websocket.start_listening = Mock(
        side_effect=WebSocketException("Boom")
    )
    remote_encrypted_websocket.is_alive.return_value = False

    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_OFF
    rest_api.rest_device_info.assert_called_once()


@pytest.mark.usefixtures("remote_legacy")
async def test_update_access_denied(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Testing update tv access denied exception."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)

    with patch(
        "menuai.components.samsungtv.bridge.Remote",
        side_effect=exceptions.AccessDenied("Boom"),
    ):
        freezer.tick(timedelta(minutes=5))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

        freezer.tick(timedelta(minutes=5))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    assert [
        flow
        for flow in menuai.config_entries.flow.async_progress()
        if flow["context"]["source"] == "reauth"
    ]
    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_UNAVAILABLE


@pytest.mark.usefixtures("rest_api")
async def test_update_ws_connection_failure(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    remote_websocket: Mock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Testing update tv connection failure exception."""
    await setup_samsungtv_entry(menuai, MOCK_CONFIGWS)

    with (
        patch.object(
            remote_websocket,
            "start_listening",
            side_effect=ConnectionFailure({"event": "ms.voiceApp.hide"}),
        ),
        patch.object(remote_websocket, "is_alive", return_value=False),
    ):
        freezer.tick(timedelta(minutes=5))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    assert (
        "Unexpected ConnectionFailure trying to get remote for fake_host, please "
        "report this issue: ConnectionFailure({'event': 'ms.voiceApp.hide'})"
        in caplog.text
    )

    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_OFF


@pytest.mark.usefixtures("rest_api")
async def test_update_ws_connection_failure_channel_timeout(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    remote_websocket: Mock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Testing update tv connection failure exception."""
    await setup_samsungtv_entry(menuai, MOCK_CONFIGWS)

    with (
        patch.object(
            remote_websocket,
            "start_listening",
            side_effect=ConnectionFailure({"event": "ms.channel.timeOut"}),
        ),
        patch.object(remote_websocket, "is_alive", return_value=False),
    ):
        freezer.tick(timedelta(minutes=5))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    assert (
        "Channel timeout occurred trying to get remote for fake_host: "
        "ConnectionFailure({'event': 'ms.channel.timeOut'})" in caplog.text
    )

    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_OFF


@pytest.mark.usefixtures("rest_api")
async def test_update_ws_connection_closed(
    menuai: menuai, freezer: FrozenDateTimeFactory, remote_websocket: Mock
) -> None:
    """Testing update tv connection failure exception."""
    await setup_samsungtv_entry(menuai, MOCK_CONFIGWS)

    with (
        patch.object(
            remote_websocket,
            "start_listening",
            side_effect=ConnectionClosedError(None, None),
        ),
        patch.object(remote_websocket, "is_alive", return_value=False),
    ):
        freezer.tick(timedelta(minutes=5))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_OFF


@pytest.mark.usefixtures("rest_api")
async def test_update_ws_unauthorized_error(
    menuai: menuai, freezer: FrozenDateTimeFactory, remote_websocket: Mock
) -> None:
    """Testing update tv unauthorized failure exception."""
    await setup_samsungtv_entry(menuai, MOCK_CONFIGWS)

    with (
        patch.object(
            remote_websocket, "start_listening", side_effect=UnauthorizedError
        ),
        patch.object(remote_websocket, "is_alive", return_value=False),
    ):
        freezer.tick(timedelta(minutes=5))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    assert [
        flow
        for flow in menuai.config_entries.flow.async_progress()
        if flow["context"]["source"] == "reauth"
    ]
    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_UNAVAILABLE


@pytest.mark.usefixtures("remote_legacy")
async def test_update_unhandled_response(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Testing update tv unhandled response exception."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)

    with patch(
        "menuai.components.samsungtv.bridge.Remote",
        side_effect=[exceptions.UnhandledResponse("Boom"), DEFAULT_MOCK],
    ):
        freezer.tick(timedelta(minutes=5))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

        state = menuai.states.get(ENTITY_ID)
        assert state.state == STATE_ON


@pytest.mark.usefixtures("remote_legacy")
async def test_connection_closed_during_update_can_recover(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Testing update tv connection closed exception can recover."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)

    with patch(
        "menuai.components.samsungtv.bridge.Remote",
        side_effect=[exceptions.ConnectionClosed(), DEFAULT_MOCK],
    ):
        freezer.tick(timedelta(minutes=5))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

        state = menuai.states.get(ENTITY_ID)
        assert state.state == STATE_UNAVAILABLE

        freezer.tick(timedelta(minutes=5))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

        state = menuai.states.get(ENTITY_ID)
        assert state.state == STATE_ON


async def test_send_key(menuai: menuai, remote_legacy: Mock) -> None:
    """Test for send key."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)
    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_VOLUME_UP, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    state = menuai.states.get(ENTITY_ID)
    # key called
    assert remote_legacy.control.call_count == 1
    assert remote_legacy.control.call_args_list == [call("KEY_VOLUP")]
    assert state.state == STATE_ON


async def test_send_key_broken_pipe(menuai: menuai, remote_legacy: Mock) -> None:
    """Testing broken pipe Exception."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)
    remote_legacy.control = Mock(side_effect=BrokenPipeError("Boom"))
    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_VOLUME_UP, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_ON


async def test_send_key_connection_closed_retry_succeed(
    menuai: menuai, remote_legacy: Mock
) -> None:
    """Test retry on connection closed."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)
    remote_legacy.control = Mock(
        side_effect=[exceptions.ConnectionClosed("Boom"), DEFAULT_MOCK, DEFAULT_MOCK]
    )
    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_VOLUME_UP, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    state = menuai.states.get(ENTITY_ID)
    # key because of retry two times
    assert remote_legacy.control.call_count == 2
    assert remote_legacy.control.call_args_list == [
        call("KEY_VOLUP"),
        call("KEY_VOLUP"),
    ]
    assert state.state == STATE_ON


async def test_send_key_unhandled_response(
    menuai: menuai, remote_legacy: Mock
) -> None:
    """Testing unhandled response exception."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)
    remote_legacy.control = Mock(side_effect=exceptions.UnhandledResponse("Boom"))
    with pytest.raises(menuaiError) as err:
        await menuai.services.async_call(
            MP_DOMAIN, SERVICE_VOLUME_UP, {ATTR_ENTITY_ID: ENTITY_ID}, True
        )
    assert err.value.translation_key == "error_sending_command"
    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("rest_api")
async def test_send_key_websocketexception(
    menuai: menuai, remote_websocket: Mock
) -> None:
    """Testing unhandled response exception."""
    await setup_samsungtv_entry(menuai, MOCK_CONFIGWS)
    remote_websocket.send_commands = Mock(side_effect=WebSocketException("Boom"))
    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_VOLUME_UP, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("rest_api")
async def test_send_key_websocketexception_encrypted(
    menuai: menuai, remote_encrypted_websocket: Mock
) -> None:
    """Testing unhandled response exception."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_ENCRYPTED_WEBSOCKET)
    remote_encrypted_websocket.send_commands = Mock(
        side_effect=WebSocketException("Boom")
    )
    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_VOLUME_UP, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("rest_api")
async def test_send_key_os_error_ws(
    menuai: menuai, remote_websocket: Mock
) -> None:
    """Testing unhandled response exception."""
    await setup_samsungtv_entry(menuai, MOCK_CONFIGWS)
    remote_websocket.send_commands = Mock(side_effect=OSError("Boom"))
    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_VOLUME_UP, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("rest_api")
async def test_send_key_os_error_ws_encrypted(
    menuai: menuai, remote_encrypted_websocket: Mock
) -> None:
    """Testing unhandled response exception."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_ENCRYPTED_WEBSOCKET)
    remote_encrypted_websocket.send_commands = Mock(side_effect=OSError("Boom"))
    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_VOLUME_UP, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_ON


async def test_send_key_os_error(menuai: menuai, remote_legacy: Mock) -> None:
    """Testing broken pipe Exception."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)
    remote_legacy.control = Mock(side_effect=OSError("Boom"))
    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_VOLUME_UP, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_ON


@pytest.mark.usefixtures("remote_legacy")
async def test_name(menuai: menuai) -> None:
    """Test for name property."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)
    state = menuai.states.get(ENTITY_ID)
    assert state.attributes[ATTR_FRIENDLY_NAME] == "Mock Title"


@pytest.mark.usefixtures("remote_legacy")
async def test_state(menuai: menuai, freezer: FrozenDateTimeFactory) -> None:
    """Test for state property."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)
    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_VOLUME_UP, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_ON
    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    state = menuai.states.get(ENTITY_ID)
    # Should be STATE_UNAVAILABLE after the timer expires
    assert state.state == STATE_OFF

    with patch(
        "menuai.components.samsungtv.bridge.Remote",
        side_effect=OSError,
    ):
        freezer.tick(timedelta(seconds=20))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get(ENTITY_ID)
    # Should be STATE_UNAVAILABLE since there is no way to turn it back on
    assert state.state == STATE_UNAVAILABLE


@pytest.mark.usefixtures("remote_legacy")
async def test_supported_features(menuai: menuai) -> None:
    """Test for supported_features property."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)
    state = menuai.states.get(ENTITY_ID)
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == SUPPORT_SAMSUNGTV


@pytest.mark.usefixtures("remote_legacy")
async def test_device_class(menuai: menuai) -> None:
    """Test for device_class property."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)
    state = menuai.states.get(ENTITY_ID)
    assert state.attributes[ATTR_DEVICE_CLASS] == MediaPlayerDeviceClass.TV


@pytest.mark.usefixtures("rest_api")
async def test_turn_off_websocket(
    menuai: menuai, remote_websocket: Mock, caplog: pytest.LogCaptureFixture
) -> None:
    """Test for turn_off."""
    remote_websocket.app_list_data = await async_load_json_object_fixture(
        menuai, "ws_installed_app_event.json", DOMAIN
    )
    with patch(
        "menuai.components.samsungtv.bridge.Remote",
        side_effect=[OSError("Boom"), DEFAULT_MOCK],
    ):
        await setup_samsungtv_entry(menuai, MOCK_CONFIGWS)

    remote_websocket.send_commands.reset_mock()

    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    # key called
    assert remote_websocket.send_commands.call_count == 1
    commands = remote_websocket.send_commands.call_args_list[0].args[0]
    assert len(commands) == 1
    assert isinstance(commands[0], SendRemoteKey)
    assert commands[0].params["DataOfCmd"] == "KEY_POWER"

    # commands not sent : power off in progress
    remote_websocket.send_commands.reset_mock()
    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_VOLUME_UP, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    assert "TV is powering off, not sending keys: ['KEY_VOLUP']" in caplog.text
    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_SELECT_SOURCE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_INPUT_SOURCE: "Deezer"},
        True,
    )
    assert "TV is powering off, not sending launch_app command" in caplog.text
    remote_websocket.send_commands.assert_not_called()


async def test_turn_off_websocket_frame(
    menuai: menuai, remote_websocket: Mock, rest_api: Mock
) -> None:
    """Test for turn_off."""
    rest_api.rest_device_info.return_value = await async_load_json_object_fixture(
        menuai, "device_info_UE43LS003.json", DOMAIN
    )
    with patch(
        "menuai.components.samsungtv.bridge.Remote",
        side_effect=[OSError("Boom"), DEFAULT_MOCK],
    ):
        await setup_samsungtv_entry(menuai, MOCK_CONFIGWS)

    remote_websocket.send_commands.reset_mock()

    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    # key called
    assert remote_websocket.send_commands.call_count == 1
    commands = remote_websocket.send_commands.call_args_list[0].args[0]
    assert len(commands) == 3
    assert isinstance(commands[0], SendRemoteKey)
    assert commands[0].params["Cmd"] == "Press"
    assert commands[0].params["DataOfCmd"] == "KEY_POWER"
    assert isinstance(commands[1], SamsungTVSleepCommand)
    assert commands[1].delay == 3
    assert isinstance(commands[2], SendRemoteKey)
    assert commands[2].params["Cmd"] == "Release"
    assert commands[2].params["DataOfCmd"] == "KEY_POWER"


async def test_turn_off_encrypted_websocket(
    menuai: menuai,
    remote_encrypted_websocket: Mock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test for turn_off."""
    entry_data = deepcopy(ENTRYDATA_ENCRYPTED_WEBSOCKET)
    entry_data[CONF_MODEL] = "UE48UNKNOWN"
    await setup_samsungtv_entry(menuai, entry_data)

    remote_encrypted_websocket.send_commands.reset_mock()

    caplog.clear()
    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    # key called
    assert remote_encrypted_websocket.send_commands.call_count == 1
    commands = remote_encrypted_websocket.send_commands.call_args_list[0].args[0]
    assert len(commands) == 2
    assert isinstance(command := commands[0], SamsungTVEncryptedCommand)
    assert command.body["param3"] == "KEY_POWEROFF"
    assert isinstance(command := commands[1], SamsungTVEncryptedCommand)
    assert command.body["param3"] == "KEY_POWER"
    assert "Unknown power_off command for UE48UNKNOWN (10.10.12.34)" in caplog.text

    # commands not sent : power off in progress
    remote_encrypted_websocket.send_commands.reset_mock()
    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_VOLUME_UP, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    assert "TV is powering off, not sending keys: ['KEY_VOLUP']" in caplog.text
    remote_encrypted_websocket.send_commands.assert_not_called()


@pytest.mark.parametrize(
    ("model", "expected_key_type"),
    [("UE50H6400", "KEY_POWEROFF"), ("UN75JU641D", "KEY_POWER")],
)
async def test_turn_off_encrypted_websocket_key_type(
    menuai: menuai,
    remote_encrypted_websocket: Mock,
    caplog: pytest.LogCaptureFixture,
    model: str,
    expected_key_type: str,
) -> None:
    """Test for turn_off."""
    entry_data = deepcopy(ENTRYDATA_ENCRYPTED_WEBSOCKET)
    entry_data[CONF_MODEL] = model
    await setup_samsungtv_entry(menuai, entry_data)

    remote_encrypted_websocket.send_commands.reset_mock()

    caplog.clear()
    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    # key called
    assert remote_encrypted_websocket.send_commands.call_count == 1
    commands = remote_encrypted_websocket.send_commands.call_args_list[0].args[0]
    assert len(commands) == 1
    assert isinstance(command := commands[0], SamsungTVEncryptedCommand)
    assert command.body["param3"] == expected_key_type
    assert "Unknown power_off command for" not in caplog.text


async def test_turn_off_legacy(menuai: menuai, remote_legacy: Mock) -> None:
    """Test for turn_off."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)
    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    # key called
    assert remote_legacy.control.call_count == 1
    assert remote_legacy.control.call_args_list == [call("KEY_POWEROFF")]


async def test_turn_off_os_error(
    menuai: menuai, remote_legacy: Mock, caplog: pytest.LogCaptureFixture
) -> None:
    """Test for turn_off with OSError."""
    caplog.set_level(logging.DEBUG)
    await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)
    remote_legacy.close = Mock(side_effect=OSError("BOOM"))
    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    assert "Could not establish connection" in caplog.text


@pytest.mark.usefixtures("rest_api")
async def test_turn_off_ws_os_error(
    menuai: menuai, remote_websocket: Mock, caplog: pytest.LogCaptureFixture
) -> None:
    """Test for turn_off with OSError."""
    caplog.set_level(logging.DEBUG)
    await setup_samsungtv_entry(menuai, MOCK_CONFIGWS)
    remote_websocket.close = Mock(side_effect=OSError("BOOM"))
    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    assert "Error closing connection" in caplog.text


@pytest.mark.usefixtures("rest_api")
async def test_turn_off_encryptedws_os_error(
    menuai: menuai,
    remote_encrypted_websocket: Mock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test for turn_off with OSError."""
    caplog.set_level(logging.DEBUG)
    await setup_samsungtv_entry(menuai, ENTRYDATA_ENCRYPTED_WEBSOCKET)
    remote_encrypted_websocket.close = Mock(side_effect=OSError("BOOM"))
    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    assert "Error closing connection" in caplog.text


async def test_volume_up(menuai: menuai, remote_legacy: Mock) -> None:
    """Test for volume_up."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)
    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_VOLUME_UP, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    # key called
    assert remote_legacy.control.call_count == 1
    assert remote_legacy.control.call_args_list == [call("KEY_VOLUP")]


async def test_volume_down(menuai: menuai, remote_legacy: Mock) -> None:
    """Test for volume_down."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)
    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_VOLUME_DOWN, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    # key called
    assert remote_legacy.control.call_count == 1
    assert remote_legacy.control.call_args_list == [call("KEY_VOLDOWN")]


async def test_mute_volume(menuai: menuai, remote_legacy: Mock) -> None:
    """Test for mute_volume."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)
    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_VOLUME_MUTE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_MEDIA_VOLUME_MUTED: True},
        True,
    )
    # key called
    assert remote_legacy.control.call_count == 1
    assert remote_legacy.control.call_args_list == [call("KEY_MUTE")]


async def test_media_play(menuai: menuai, remote_legacy: Mock) -> None:
    """Test for media_play."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)
    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_MEDIA_PLAY, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    # key called
    assert remote_legacy.control.call_count == 1
    assert remote_legacy.control.call_args_list == [call("KEY_PLAY")]

    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_MEDIA_PLAY_PAUSE, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    # key called
    assert remote_legacy.control.call_count == 2
    assert remote_legacy.control.call_args_list == [call("KEY_PLAY"), call("KEY_PAUSE")]


async def test_media_pause(menuai: menuai, remote_legacy: Mock) -> None:
    """Test for media_pause."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)
    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_MEDIA_PAUSE, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    # key called
    assert remote_legacy.control.call_count == 1
    assert remote_legacy.control.call_args_list == [call("KEY_PAUSE")]

    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_MEDIA_PLAY_PAUSE, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    # key called
    assert remote_legacy.control.call_count == 2
    assert remote_legacy.control.call_args_list == [call("KEY_PAUSE"), call("KEY_PLAY")]


async def test_media_next_track(menuai: menuai, remote_legacy: Mock) -> None:
    """Test for media_next_track."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)
    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_MEDIA_NEXT_TRACK, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    # key  called
    assert remote_legacy.control.call_count == 1
    assert remote_legacy.control.call_args_list == [call("KEY_CHUP")]


async def test_media_previous_track(menuai: menuai, remote_legacy: Mock) -> None:
    """Test for media_previous_track."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)
    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_MEDIA_PREVIOUS_TRACK, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    # key called
    assert remote_legacy.control.call_count == 1
    assert remote_legacy.control.call_args_list == [call("KEY_CHDOWN")]


@pytest.mark.usefixtures("remote_websocket", "rest_api")
async def test_turn_on_wol(menuai: menuai) -> None:
    """Test turn on."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=ENTRYDATA_WEBSOCKET,
        unique_id="be9554b9-c9fb-41f4-8920-22da015376a4",
    )
    entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    with patch(
        "menuai.components.samsungtv.entity.send_magic_packet"
    ) as mock_send_magic_packet:
        await menuai.services.async_call(
            MP_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: ENTITY_ID}, True
        )
        await menuai.async_block_till_done()
    assert mock_send_magic_packet.called


async def test_turn_on_without_turnon(menuai: menuai, remote_legacy: Mock) -> None:
    """Test turn on."""
    await async_setup_component(menuai, "menuai", {})
    await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)
    with pytest.raises(ServiceNotSupported, match="does not support action"):
        await menuai.services.async_call(
            MP_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: ENTITY_ID}, True
        )
    # nothing called as not supported feature
    assert remote_legacy.control.call_count == 0


async def test_play_media(menuai: menuai, remote_legacy: Mock) -> None:
    """Test for play_media."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)
    with patch("menuai.components.samsungtv.bridge.asyncio.sleep") as sleep:
        await menuai.services.async_call(
            MP_DOMAIN,
            SERVICE_PLAY_MEDIA,
            {
                ATTR_ENTITY_ID: ENTITY_ID,
                ATTR_MEDIA_CONTENT_TYPE: MediaType.CHANNEL,
                ATTR_MEDIA_CONTENT_ID: "576",
            },
            True,
        )
    # keys and update called
    assert remote_legacy.control.call_count == 4
    assert remote_legacy.control.call_args_list == [
        call("KEY_5"),
        call("KEY_7"),
        call("KEY_6"),
        call("KEY_ENTER"),
    ]
    assert sleep.call_count == 3


async def test_play_media_invalid_type(menuai: menuai) -> None:
    """Test for play_media with invalid media type."""
    with patch("menuai.components.samsungtv.bridge.Remote") as remote:
        url = "https://example.com"
        await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)
        remote.reset_mock()
        await menuai.services.async_call(
            MP_DOMAIN,
            SERVICE_PLAY_MEDIA,
            {
                ATTR_ENTITY_ID: ENTITY_ID,
                ATTR_MEDIA_CONTENT_TYPE: MediaType.URL,
                ATTR_MEDIA_CONTENT_ID: url,
            },
            True,
        )
        # control not called
        assert remote.control.call_count == 0


async def test_play_media_channel_as_string(menuai: menuai) -> None:
    """Test for play_media with invalid channel as string."""
    with patch("menuai.components.samsungtv.bridge.Remote") as remote:
        url = "https://example.com"
        await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)
        remote.reset_mock()
        await menuai.services.async_call(
            MP_DOMAIN,
            SERVICE_PLAY_MEDIA,
            {
                ATTR_ENTITY_ID: ENTITY_ID,
                ATTR_MEDIA_CONTENT_TYPE: MediaType.CHANNEL,
                ATTR_MEDIA_CONTENT_ID: url,
            },
            True,
        )
        # control not called
        assert remote.control.call_count == 0


async def test_play_media_channel_as_non_positive(menuai: menuai) -> None:
    """Test for play_media with invalid channel as non positive integer."""
    with patch("menuai.components.samsungtv.bridge.Remote") as remote:
        await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)
        remote.reset_mock()
        await menuai.services.async_call(
            MP_DOMAIN,
            SERVICE_PLAY_MEDIA,
            {
                ATTR_ENTITY_ID: ENTITY_ID,
                ATTR_MEDIA_CONTENT_TYPE: MediaType.CHANNEL,
                ATTR_MEDIA_CONTENT_ID: "-4",
            },
            True,
        )
        # control not called
        assert remote.control.call_count == 0


async def test_select_source(menuai: menuai, remote_legacy: Mock) -> None:
    """Test for select_source."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)
    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_SELECT_SOURCE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_INPUT_SOURCE: "HDMI"},
        True,
    )
    # key called
    assert remote_legacy.control.call_count == 1
    assert remote_legacy.control.call_args_list == [call("KEY_HDMI")]


async def test_select_source_invalid_source(menuai: menuai) -> None:
    """Test for select_source with invalid source."""

    source = "INVALID"

    with patch("menuai.components.samsungtv.bridge.Remote") as remote:
        await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)
        remote.reset_mock()
        with pytest.raises(menuaiError) as exc_info:
            await menuai.services.async_call(
                MP_DOMAIN,
                SERVICE_SELECT_SOURCE,
                {ATTR_ENTITY_ID: ENTITY_ID, ATTR_INPUT_SOURCE: source},
                True,
            )
        # control not called
        assert remote.control.call_count == 0
        assert exc_info.value.translation_domain == DOMAIN
        assert exc_info.value.translation_key == "source_unsupported"
        assert exc_info.value.translation_placeholders == {
            "entity": ENTITY_ID,
            "source": source,
        }


@pytest.mark.usefixtures("rest_api")
async def test_play_media_app(menuai: menuai, remote_websocket: Mock) -> None:
    """Test for play_media."""
    await setup_samsungtv_entry(menuai, MOCK_CONFIGWS)
    remote_websocket.send_commands.reset_mock()

    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_PLAY_MEDIA,
        {
            ATTR_ENTITY_ID: ENTITY_ID,
            ATTR_MEDIA_CONTENT_TYPE: MediaType.APP,
            ATTR_MEDIA_CONTENT_ID: "3201608010191",
        },
        True,
    )
    assert remote_websocket.send_commands.call_count == 1
    commands = remote_websocket.send_commands.call_args_list[0].args[0]
    assert len(commands) == 1
    assert isinstance(commands[0], ChannelEmitCommand)
    assert commands[0].params["data"]["appId"] == "3201608010191"


@pytest.mark.usefixtures("rest_api")
async def test_select_source_app(menuai: menuai, remote_websocket: Mock) -> None:
    """Test for select_source."""
    remote_websocket.app_list_data = await async_load_json_object_fixture(
        menuai, "ws_installed_app_event.json", DOMAIN
    )
    await setup_samsungtv_entry(menuai, MOCK_CONFIGWS)
    remote_websocket.send_commands.reset_mock()

    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_SELECT_SOURCE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_INPUT_SOURCE: "Deezer"},
        True,
    )
    assert remote_websocket.send_commands.call_count == 1
    commands = remote_websocket.send_commands.call_args_list[0].args[0]
    assert len(commands) == 1
    assert isinstance(commands[0], ChannelEmitCommand)
    assert commands[0].params["data"]["appId"] == "3201608010191"


@pytest.mark.usefixtures("rest_api")
async def test_websocket_unsupported_remote_control(
    menuai: menuai,
    remote_websocket: Mock,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test for turn_off."""
    entry = await setup_samsungtv_entry(menuai, MOCK_ENTRY_WS)

    assert entry.data[CONF_METHOD] == METHOD_WEBSOCKET
    assert entry.data[CONF_PORT] == 8001

    remote_websocket.send_commands.reset_mock()

    await menuai.services.async_call(
        MP_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: ENTITY_ID}, True
    )
    remote_websocket.raise_mock_ws_event_callback(
        "ms.error",
        {
            "event": "ms.error",
            "data": {"message": "unrecognized method value : ms.remote.control"},
        },
    )

    # key called
    assert remote_websocket.send_commands.call_count == 1
    commands = remote_websocket.send_commands.call_args_list[0].args[0]
    assert len(commands) == 1
    assert isinstance(commands[0], SendRemoteKey)
    assert commands[0].params["DataOfCmd"] == "KEY_POWER"

    # error logged
    assert (
        "Your TV seems to be unsupported by SamsungTVWSBridge and needs a PIN: "
        "'unrecognized method value : ms.remote.control'" in caplog.text
    )

    # Wait config_entry reload
    await menuai.async_block_till_done()
    freezer.tick(timedelta(seconds=ENTRY_RELOAD_COOLDOWN))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    # ensure reauth triggered, and method/port updated
    assert [
        flow
        for flow in menuai.config_entries.flow.async_progress()
        if flow["context"]["source"] == "reauth"
    ]
    assert entry.data[CONF_METHOD] == METHOD_ENCRYPTED_WEBSOCKET
    assert entry.data[CONF_PORT] == ENCRYPTED_WEBSOCKET_PORT
    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_UNAVAILABLE


@pytest.mark.usefixtures("remote_websocket", "rest_api", "upnp_notify_server")
async def test_volume_control_upnp(menuai: menuai, dmr_device: Mock) -> None:
    """Test for Upnp volume control."""
    await setup_samsungtv_entry(menuai, MOCK_ENTRY_WS)

    state = menuai.states.get(ENTITY_ID)
    assert state.attributes[ATTR_MEDIA_VOLUME_LEVEL] == 0.44
    assert state.attributes[ATTR_MEDIA_VOLUME_MUTED] is False

    # Upnp action succeeds
    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_MEDIA_VOLUME_LEVEL: 0.5},
        True,
    )
    dmr_device.async_set_volume_level.assert_called_once_with(0.5)

    # Upnp action failed
    dmr_device.async_set_volume_level.reset_mock()
    dmr_device.async_set_volume_level.side_effect = UpnpActionResponseError(
        status=500, error_code=501, error_desc="Action Failed"
    )
    with pytest.raises(menuaiError) as err:
        await menuai.services.async_call(
            MP_DOMAIN,
            SERVICE_VOLUME_SET,
            {ATTR_ENTITY_ID: ENTITY_ID, ATTR_MEDIA_VOLUME_LEVEL: 0.6},
            True,
        )
    assert err.value.translation_key == "error_set_volume"
    dmr_device.async_set_volume_level.assert_called_once_with(0.6)


@pytest.mark.usefixtures("remote_websocket", "rest_api")
async def test_upnp_not_available(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test for volume control when Upnp is not available."""
    await setup_samsungtv_entry(menuai, MOCK_ENTRY_WS)
    assert "Unable to create Upnp DMR device" in caplog.text

    # Upnp action fails
    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_MEDIA_VOLUME_LEVEL: 0.6},
        True,
    )
    assert "Upnp services are not available" in caplog.text


@pytest.mark.usefixtures("remote_websocket", "rest_api", "upnp_factory")
async def test_upnp_missing_service(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test for volume control when Upnp is not available."""
    await setup_samsungtv_entry(menuai, MOCK_ENTRY_WS)
    assert "Unable to create Upnp DMR device" in caplog.text

    # Upnp action fails
    await menuai.services.async_call(
        MP_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_MEDIA_VOLUME_LEVEL: 0.6},
        True,
    )
    assert "Upnp services are not available" in caplog.text


@pytest.mark.usefixtures("remote_websocket", "rest_api")
async def test_upnp_shutdown(
    menuai: menuai,
    dmr_device: Mock,
    upnp_notify_server: Mock,
) -> None:
    """Ensure that Upnp cleanup takes effect."""
    entry = await setup_samsungtv_entry(menuai, MOCK_ENTRY_WS)

    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_ON

    assert await menuai.config_entries.async_unload(entry.entry_id)

    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_UNAVAILABLE

    dmr_device.async_unsubscribe_services.assert_called_once()
    upnp_notify_server.async_stop_server.assert_called_once()


@pytest.mark.usefixtures("remote_websocket", "rest_api", "upnp_notify_server")
async def test_upnp_subscribe_events(menuai: menuai, dmr_device: Mock) -> None:
    """Test for Upnp event feedback."""
    await setup_samsungtv_entry(menuai, MOCK_ENTRY_WS)

    state = menuai.states.get(ENTITY_ID)
    assert state.attributes[ATTR_MEDIA_VOLUME_LEVEL] == 0.44
    assert state.attributes[ATTR_MEDIA_VOLUME_MUTED] is False

    # DMR Devices gets updated, and raise event
    dmr_device.volume_level = 0
    dmr_device.is_volume_muted = True
    dmr_device.raise_event(None, None)

    # State gets updated without the need to wait for next update
    state = menuai.states.get(ENTITY_ID)
    assert state.attributes[ATTR_MEDIA_VOLUME_LEVEL] == 0
    assert state.attributes[ATTR_MEDIA_VOLUME_MUTED] is True


@pytest.mark.usefixtures("remote_websocket", "rest_api")
async def test_upnp_subscribe_events_upnperror(
    menuai: menuai,
    dmr_device: Mock,
    upnp_notify_server: Mock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test for failure to subscribe Upnp services."""
    with patch.object(dmr_device, "async_subscribe_services", side_effect=UpnpError):
        await setup_samsungtv_entry(menuai, MOCK_ENTRY_WS)

    upnp_notify_server.async_stop_server.assert_called_once()
    assert "Error while subscribing during device connect" in caplog.text


@pytest.mark.usefixtures("remote_websocket", "rest_api")
async def test_upnp_subscribe_events_upnpresponseerror(
    menuai: menuai,
    dmr_device: Mock,
    upnp_notify_server: Mock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test for failure to subscribe Upnp services."""
    with patch.object(
        dmr_device,
        "async_subscribe_services",
        side_effect=UpnpResponseError(status=501),
    ):
        await setup_samsungtv_entry(menuai, MOCK_ENTRY_WS)

    upnp_notify_server.async_stop_server.assert_not_called()
    assert "Device rejected subscription" in caplog.text


@pytest.mark.usefixtures("rest_api", "upnp_notify_server")
async def test_upnp_re_subscribe_events(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    remote_websocket: Mock,
    dmr_device: Mock,
) -> None:
    """Test for Upnp event feedback."""
    await setup_samsungtv_entry(menuai, MOCK_ENTRY_WS)

    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_ON
    assert dmr_device.async_subscribe_services.call_count == 1
    assert dmr_device.async_unsubscribe_services.call_count == 0

    with (
        patch.object(
            remote_websocket, "start_listening", side_effect=WebSocketException("Boom")
        ),
        patch.object(remote_websocket, "is_alive", return_value=False),
    ):
        freezer.tick(timedelta(minutes=5))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_OFF
    assert dmr_device.async_subscribe_services.call_count == 1
    assert dmr_device.async_unsubscribe_services.call_count == 1

    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_ON
    assert dmr_device.async_subscribe_services.call_count == 2
    assert dmr_device.async_unsubscribe_services.call_count == 1


@pytest.mark.usefixtures("rest_api", "upnp_notify_server")
@pytest.mark.parametrize(
    "error",
    {UpnpConnectionError(), UpnpCommunicationError(), UpnpResponseError(status=400)},
)
async def test_upnp_failed_re_subscribe_events(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    remote_websocket: Mock,
    dmr_device: Mock,
    caplog: pytest.LogCaptureFixture,
    error: Exception,
) -> None:
    """Test for Upnp event feedback."""
    await setup_samsungtv_entry(menuai, MOCK_ENTRY_WS)

    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_ON
    assert dmr_device.async_subscribe_services.call_count == 1
    assert dmr_device.async_unsubscribe_services.call_count == 0

    with (
        patch.object(
            remote_websocket, "start_listening", side_effect=WebSocketException("Boom")
        ),
        patch.object(remote_websocket, "is_alive", return_value=False),
    ):
        freezer.tick(timedelta(minutes=5))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_OFF
    assert dmr_device.async_subscribe_services.call_count == 1
    assert dmr_device.async_unsubscribe_services.call_count == 1

    with patch.object(dmr_device, "async_subscribe_services", side_effect=error):
        freezer.tick(timedelta(minutes=5))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_ON
    assert "Device rejected re-subscription" in caplog.text
