"""Test ESPHome media_players."""

from unittest.mock import AsyncMock, Mock, call, patch

from aioesphomeapi import (
    APIClient,
    MediaPlayerCommand,
    MediaPlayerEntityState,
    MediaPlayerFormatPurpose,
    MediaPlayerInfo,
    MediaPlayerState,
    MediaPlayerSupportedFormat,
    UserService,
)
import pytest

from menuai.components import media_source
from menuai.components.media_player import (
    ATTR_MEDIA_ANNOUNCE,
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    ATTR_MEDIA_EXTRA,
    ATTR_MEDIA_VOLUME_LEVEL,
    ATTR_MEDIA_VOLUME_MUTED,
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    SERVICE_MEDIA_PAUSE,
    SERVICE_MEDIA_PLAY,
    SERVICE_MEDIA_STOP,
    SERVICE_PLAY_MEDIA,
    SERVICE_VOLUME_MUTE,
    SERVICE_VOLUME_SET,
    BrowseMedia,
    MediaClass,
    MediaType,
)
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai
from menuai.helpers import device_registry as dr
from menuai.setup import async_setup_component

from .conftest import MockESPHomeDeviceType, MockGenericDeviceEntryType

from tests.common import mock_platform
from tests.typing import WebSocketGenerator


async def test_media_player_entity(
    menuai: menuai,
    mock_client: APIClient,
    mock_generic_device_entry: MockGenericDeviceEntryType,
) -> None:
    """Test a generic media_player entity."""
    entity_info = [
        MediaPlayerInfo(
            object_id="mymedia_player",
            key=1,
            name="my media_player",
            unique_id="my_media_player",
            supports_pause=True,
        )
    ]
    states = [
        MediaPlayerEntityState(
            key=1, volume=50, muted=True, state=MediaPlayerState.PAUSED
        )
    ]
    user_service: list[UserService] = []
    await mock_generic_device_entry(
        mock_client=mock_client,
        entity_info=entity_info,
        user_service=user_service,
        states=states,
    )
    state = menuai.states.get("media_player.test_mymedia_player")
    assert state is not None
    assert state.state == "paused"

    await menuai.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_MUTE,
        {
            ATTR_ENTITY_ID: "media_player.test_mymedia_player",
            ATTR_MEDIA_VOLUME_MUTED: True,
        },
        blocking=True,
    )
    mock_client.media_player_command.assert_has_calls(
        [call(1, command=MediaPlayerCommand.MUTE)]
    )
    mock_client.media_player_command.reset_mock()

    await menuai.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_MUTE,
        {
            ATTR_ENTITY_ID: "media_player.test_mymedia_player",
            ATTR_MEDIA_VOLUME_MUTED: True,
        },
        blocking=True,
    )
    mock_client.media_player_command.assert_has_calls(
        [call(1, command=MediaPlayerCommand.MUTE)]
    )
    mock_client.media_player_command.reset_mock()

    await menuai.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_SET,
        {
            ATTR_ENTITY_ID: "media_player.test_mymedia_player",
            ATTR_MEDIA_VOLUME_LEVEL: 0.5,
        },
        blocking=True,
    )
    mock_client.media_player_command.assert_has_calls([call(1, volume=0.5)])
    mock_client.media_player_command.reset_mock()

    await menuai.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_MEDIA_PAUSE,
        {
            ATTR_ENTITY_ID: "media_player.test_mymedia_player",
        },
        blocking=True,
    )
    mock_client.media_player_command.assert_has_calls(
        [call(1, command=MediaPlayerCommand.PAUSE)]
    )
    mock_client.media_player_command.reset_mock()

    await menuai.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_MEDIA_PLAY,
        {
            ATTR_ENTITY_ID: "media_player.test_mymedia_player",
        },
        blocking=True,
    )
    mock_client.media_player_command.assert_has_calls(
        [call(1, command=MediaPlayerCommand.PLAY)]
    )
    mock_client.media_player_command.reset_mock()

    await menuai.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_MEDIA_STOP,
        {
            ATTR_ENTITY_ID: "media_player.test_mymedia_player",
        },
        blocking=True,
    )
    mock_client.media_player_command.assert_has_calls(
        [call(1, command=MediaPlayerCommand.STOP)]
    )
    mock_client.media_player_command.reset_mock()


async def test_media_player_entity_with_source(
    menuai: menuai,
    mock_client: APIClient,
    menuai_ws_client: WebSocketGenerator,
    mock_generic_device_entry: MockGenericDeviceEntryType,
) -> None:
    """Test a generic media_player entity media source."""
    await async_setup_component(menuai, "media_source", {"media_source": {}})
    await menuai.async_block_till_done()
    esphome_platform_mock = Mock(
        async_get_media_browser_root_object=AsyncMock(
            return_value=[
                BrowseMedia(
                    title="Spotify",
                    media_class=MediaClass.APP,
                    media_content_id="",
                    media_content_type="spotify",
                    thumbnail="https://brands.home-assistant.io/_/spotify/logo.png",
                    can_play=False,
                    can_expand=True,
                )
            ]
        ),
        async_browse_media=AsyncMock(
            return_value=BrowseMedia(
                title="Spotify Favourites",
                media_class=MediaClass.PLAYLIST,
                media_content_id="",
                media_content_type="spotify",
                can_play=True,
                can_expand=False,
            )
        ),
        async_play_media=AsyncMock(return_value=False),
    )
    mock_platform(menuai, "test.esphome", esphome_platform_mock)
    await async_setup_component(menuai, "test", {"test": {}})
    await async_setup_component(menuai, "media_source", {"media_source": {}})
    await menuai.async_block_till_done()

    entity_info = [
        MediaPlayerInfo(
            object_id="mymedia_player",
            key=1,
            name="my media_player",
            unique_id="my_media_player",
            supports_pause=True,
        )
    ]
    states = [
        MediaPlayerEntityState(
            key=1, volume=50, muted=True, state=MediaPlayerState.PLAYING
        )
    ]
    user_service: list[UserService] = []
    await mock_generic_device_entry(
        mock_client=mock_client,
        entity_info=entity_info,
        user_service=user_service,
        states=states,
    )
    state = menuai.states.get("media_player.test_mymedia_player")
    assert state is not None
    assert state.state == "playing"

    with pytest.raises(media_source.error.Unresolvable):
        await menuai.services.async_call(
            MEDIA_PLAYER_DOMAIN,
            SERVICE_PLAY_MEDIA,
            {
                ATTR_ENTITY_ID: "media_player.test_mymedia_player",
                ATTR_MEDIA_CONTENT_TYPE: MediaType.MUSIC,
                ATTR_MEDIA_CONTENT_ID: "media-source://local/xz",
            },
            blocking=True,
        )

    mock_client.media_player_command.reset_mock()

    play_media = media_source.PlayMedia(
        url="http://www.example.com/xy.mp3",
        mime_type="audio/mp3",
    )

    await menuai.async_block_till_done()

    with patch(
        "menuai.components.media_source.async_resolve_media",
        return_value=play_media,
    ):
        await menuai.services.async_call(
            MEDIA_PLAYER_DOMAIN,
            SERVICE_PLAY_MEDIA,
            {
                ATTR_ENTITY_ID: "media_player.test_mymedia_player",
                ATTR_MEDIA_CONTENT_TYPE: "audio/mp3",
                ATTR_MEDIA_CONTENT_ID: "media-source://local/xy",
            },
            blocking=True,
        )

    mock_client.media_player_command.assert_has_calls(
        [call(1, media_url="http://www.example.com/xy.mp3", announcement=None)]
    )

    client = await menuai_ws_client()
    await client.send_json(
        {
            "id": 1,
            "type": "media_player/browse_media",
            "entity_id": "media_player.test_mymedia_player",
        }
    )
    response = await client.receive_json()
    assert response["success"]

    await menuai.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_PLAY_MEDIA,
        {
            ATTR_ENTITY_ID: "media_player.test_mymedia_player",
            ATTR_MEDIA_CONTENT_TYPE: MediaType.URL,
            ATTR_MEDIA_CONTENT_ID: "media-source://tts?message=hello",
            ATTR_MEDIA_ANNOUNCE: True,
        },
        blocking=True,
    )

    mock_client.media_player_command.assert_has_calls(
        [call(1, media_url="media-source://tts?message=hello", announcement=True)]
    )


async def test_media_player_proxy(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:
    """Test a media_player entity with a proxy URL."""
    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        entity_info=[
            MediaPlayerInfo(
                object_id="mymedia_player",
                key=1,
                name="my media_player",
                unique_id="my_media_player",
                supports_pause=True,
                supported_formats=[
                    MediaPlayerSupportedFormat(
                        format="flac",
                        sample_rate=0,  # source rate
                        num_channels=0,  # source channels
                        purpose=MediaPlayerFormatPurpose.DEFAULT,
                        sample_bytes=0,  # source width
                    ),
                    MediaPlayerSupportedFormat(
                        format="wav",
                        sample_rate=16000,
                        num_channels=1,
                        purpose=MediaPlayerFormatPurpose.ANNOUNCEMENT,
                        sample_bytes=2,
                    ),
                    MediaPlayerSupportedFormat(
                        format="mp3",
                        sample_rate=48000,
                        num_channels=2,
                        purpose=MediaPlayerFormatPurpose.DEFAULT,
                    ),
                ],
            )
        ],
        states=[
            MediaPlayerEntityState(
                key=1, volume=50, muted=False, state=MediaPlayerState.PAUSED
            )
        ],
    )
    await menuai.async_block_till_done()
    dev = device_registry.async_get_device(
        connections={(dr.CONNECTION_NETWORK_MAC, mock_device.entry.unique_id)}
    )
    assert dev is not None
    state = menuai.states.get("media_player.test_mymedia_player")
    assert state is not None
    assert state.state == "paused"

    media_url = "http://127.0.0.1/test.mp3"
    proxy_url = f"/api/esphome/ffmpeg_proxy/{dev.id}/test-id.flac"

    with (
        patch(
            "menuai.components.esphome.media_player.async_create_proxy_url",
            return_value=proxy_url,
        ) as mock_async_create_proxy_url,
    ):
        await menuai.services.async_call(
            MEDIA_PLAYER_DOMAIN,
            SERVICE_PLAY_MEDIA,
            {
                ATTR_ENTITY_ID: "media_player.test_mymedia_player",
                ATTR_MEDIA_CONTENT_TYPE: MediaType.MUSIC,
                ATTR_MEDIA_CONTENT_ID: media_url,
            },
            blocking=True,
        )

        # Should be the default format
        mock_async_create_proxy_url.assert_called_once()
        device_id = mock_async_create_proxy_url.call_args[0][1]
        mock_async_create_proxy_url.assert_called_once_with(
            menuai,
            device_id,
            media_url,
            media_format="flac",
            rate=None,
            channels=None,
            width=None,
        )

        media_args = mock_client.media_player_command.call_args.kwargs
        assert not media_args["announcement"]

        # Reset
        mock_async_create_proxy_url.reset_mock()

        # Set announcement flag
        await menuai.services.async_call(
            MEDIA_PLAYER_DOMAIN,
            SERVICE_PLAY_MEDIA,
            {
                ATTR_ENTITY_ID: "media_player.test_mymedia_player",
                ATTR_MEDIA_CONTENT_TYPE: MediaType.MUSIC,
                ATTR_MEDIA_CONTENT_ID: media_url,
                ATTR_MEDIA_ANNOUNCE: True,
            },
            blocking=True,
        )

        # Should be the announcement format
        mock_async_create_proxy_url.assert_called_once()
        device_id = mock_async_create_proxy_url.call_args[0][1]
        mock_async_create_proxy_url.assert_called_once_with(
            menuai,
            device_id,
            media_url,
            media_format="wav",
            rate=16000,
            channels=1,
            width=2,
        )

        media_args = mock_client.media_player_command.call_args.kwargs
        assert media_args["announcement"]

        # test with bypass_proxy flag
        mock_async_create_proxy_url.reset_mock()
        await menuai.services.async_call(
            MEDIA_PLAYER_DOMAIN,
            SERVICE_PLAY_MEDIA,
            {
                ATTR_ENTITY_ID: "media_player.test_mymedia_player",
                ATTR_MEDIA_CONTENT_TYPE: MediaType.MUSIC,
                ATTR_MEDIA_CONTENT_ID: media_url,
                ATTR_MEDIA_EXTRA: {
                    "bypass_proxy": True,
                },
            },
            blocking=True,
        )
        mock_async_create_proxy_url.assert_not_called()
        media_args = mock_client.media_player_command.call_args.kwargs
        assert media_args["media_url"] == media_url
