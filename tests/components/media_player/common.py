"""Collection of helper methods.

All containing methods are legacy helpers that should not be used by new
components. Instead call the service directly.
"""

from menuai.components.media_player import (
    ATTR_INPUT_SOURCE,
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    ATTR_MEDIA_ENQUEUE,
    ATTR_MEDIA_SEEK_POSITION,
    ATTR_MEDIA_VOLUME_LEVEL,
    ATTR_MEDIA_VOLUME_MUTED,
    DOMAIN,
    SERVICE_CLEAR_PLAYLIST,
    SERVICE_PLAY_MEDIA,
    SERVICE_SELECT_SOURCE,
    MediaPlayerEnqueue,
)
from menuai.const import (
    ATTR_ENTITY_ID,
    ENTITY_MATCH_ALL,
    SERVICE_MEDIA_NEXT_TRACK,
    SERVICE_MEDIA_PAUSE,
    SERVICE_MEDIA_PLAY,
    SERVICE_MEDIA_PLAY_PAUSE,
    SERVICE_MEDIA_PREVIOUS_TRACK,
    SERVICE_MEDIA_SEEK,
    SERVICE_MEDIA_STOP,
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    SERVICE_VOLUME_DOWN,
    SERVICE_VOLUME_MUTE,
    SERVICE_VOLUME_SET,
    SERVICE_VOLUME_UP,
)
from menuai.core import menuai
from menuai.loader import bind_menuai


async def async_turn_on(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Turn on specified media player or all."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    await menuai.services.async_call(DOMAIN, SERVICE_TURN_ON, data, blocking=True)


@bind_menuai
def turn_on(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Turn on specified media player or all."""
    menuai.add_job(async_turn_on, menuai, entity_id)


async def async_turn_off(
    menuai: menuai, entity_id: str = ENTITY_MATCH_ALL
) -> None:
    """Turn off specified media player or all."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    await menuai.services.async_call(DOMAIN, SERVICE_TURN_OFF, data, blocking=True)


@bind_menuai
def turn_off(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Turn off specified media player or all."""
    menuai.add_job(async_turn_off, menuai, entity_id)


async def async_toggle(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Toggle specified media player or all."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    await menuai.services.async_call(DOMAIN, SERVICE_TOGGLE, data, blocking=True)


@bind_menuai
def toggle(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Toggle specified media player or all."""
    menuai.add_job(async_toggle, menuai, entity_id)


async def async_volume_up(
    menuai: menuai, entity_id: str = ENTITY_MATCH_ALL
) -> None:
    """Send the media player the command for volume up."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    await menuai.services.async_call(DOMAIN, SERVICE_VOLUME_UP, data, blocking=True)


@bind_menuai
def volume_up(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Send the media player the command for volume up."""
    menuai.add_job(async_volume_up, menuai, entity_id)


async def async_volume_down(
    menuai: menuai, entity_id: str = ENTITY_MATCH_ALL
) -> None:
    """Send the media player the command for volume down."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    await menuai.services.async_call(DOMAIN, SERVICE_VOLUME_DOWN, data, blocking=True)


@bind_menuai
def volume_down(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Send the media player the command for volume down."""
    menuai.add_job(async_volume_down, menuai, entity_id)


async def async_mute_volume(
    menuai: menuai, mute: bool, entity_id: str = ENTITY_MATCH_ALL
) -> None:
    """Send the media player the command for muting the volume."""
    data = {ATTR_MEDIA_VOLUME_MUTED: mute}

    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id

    await menuai.services.async_call(DOMAIN, SERVICE_VOLUME_MUTE, data, blocking=True)


@bind_menuai
def mute_volume(
    menuai: menuai, mute: bool, entity_id: str = ENTITY_MATCH_ALL
) -> None:
    """Send the media player the command for muting the volume."""
    menuai.add_job(async_mute_volume, menuai, mute, entity_id)


async def async_set_volume_level(
    menuai: menuai, volume: float, entity_id: str = ENTITY_MATCH_ALL
) -> None:
    """Send the media player the command for setting the volume."""
    data = {ATTR_MEDIA_VOLUME_LEVEL: volume}

    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id

    await menuai.services.async_call(DOMAIN, SERVICE_VOLUME_SET, data, blocking=True)


@bind_menuai
def set_volume_level(
    menuai: menuai, volume: float, entity_id: str = ENTITY_MATCH_ALL
) -> None:
    """Send the media player the command for setting the volume."""
    menuai.add_job(async_set_volume_level, menuai, volume, entity_id)


async def async_media_play_pause(
    menuai: menuai, entity_id: str = ENTITY_MATCH_ALL
) -> None:
    """Send the media player the command for play/pause."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    await menuai.services.async_call(
        DOMAIN, SERVICE_MEDIA_PLAY_PAUSE, data, blocking=True
    )


@bind_menuai
def media_play_pause(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Send the media player the command for play/pause."""
    menuai.add_job(async_media_play_pause, menuai, entity_id)


async def async_media_play(
    menuai: menuai, entity_id: str = ENTITY_MATCH_ALL
) -> None:
    """Send the media player the command for play/pause."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    await menuai.services.async_call(DOMAIN, SERVICE_MEDIA_PLAY, data, blocking=True)


@bind_menuai
def media_play(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Send the media player the command for play/pause."""
    menuai.add_job(async_media_play, menuai, entity_id)


async def async_media_pause(
    menuai: menuai, entity_id: str = ENTITY_MATCH_ALL
) -> None:
    """Send the media player the command for pause."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    await menuai.services.async_call(DOMAIN, SERVICE_MEDIA_PAUSE, data, blocking=True)


@bind_menuai
def media_pause(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Send the media player the command for pause."""
    menuai.add_job(async_media_pause, menuai, entity_id)


async def async_media_stop(
    menuai: menuai, entity_id: str = ENTITY_MATCH_ALL
) -> None:
    """Send the media player the command for stop."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    await menuai.services.async_call(DOMAIN, SERVICE_MEDIA_STOP, data, blocking=True)


@bind_menuai
def media_stop(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Send the media player the command for stop."""
    menuai.add_job(async_media_stop, menuai, entity_id)


async def async_media_next_track(
    menuai: menuai, entity_id: str = ENTITY_MATCH_ALL
) -> None:
    """Send the media player the command for next track."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    await menuai.services.async_call(
        DOMAIN, SERVICE_MEDIA_NEXT_TRACK, data, blocking=True
    )


@bind_menuai
def media_next_track(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Send the media player the command for next track."""
    menuai.add_job(async_media_next_track, menuai, entity_id)


async def async_media_previous_track(
    menuai: menuai, entity_id: str = ENTITY_MATCH_ALL
) -> None:
    """Send the media player the command for prev track."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    await menuai.services.async_call(
        DOMAIN, SERVICE_MEDIA_PREVIOUS_TRACK, data, blocking=True
    )


@bind_menuai
def media_previous_track(
    menuai: menuai, entity_id: str = ENTITY_MATCH_ALL
) -> None:
    """Send the media player the command for prev track."""
    menuai.add_job(async_media_previous_track, menuai, entity_id)


async def async_media_seek(
    menuai: menuai, position: float, entity_id: str = ENTITY_MATCH_ALL
) -> None:
    """Send the media player the command to seek in current playing media."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    data[ATTR_MEDIA_SEEK_POSITION] = position
    await menuai.services.async_call(DOMAIN, SERVICE_MEDIA_SEEK, data, blocking=True)


@bind_menuai
def media_seek(
    menuai: menuai, position: float, entity_id: str = ENTITY_MATCH_ALL
) -> None:
    """Send the media player the command to seek in current playing media."""
    menuai.add_job(async_media_seek, menuai, position, entity_id)


async def async_play_media(
    menuai: menuai,
    media_type: str,
    media_id: str,
    entity_id: str = ENTITY_MATCH_ALL,
    enqueue: MediaPlayerEnqueue | bool | None = None,
) -> None:
    """Send the media player the command for playing media."""
    data = {ATTR_MEDIA_CONTENT_TYPE: media_type, ATTR_MEDIA_CONTENT_ID: media_id}

    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id

    if enqueue:
        data[ATTR_MEDIA_ENQUEUE] = enqueue

    await menuai.services.async_call(DOMAIN, SERVICE_PLAY_MEDIA, data, blocking=True)


@bind_menuai
def play_media(
    menuai: menuai,
    media_type: str,
    media_id: str,
    entity_id: str = ENTITY_MATCH_ALL,
    enqueue: MediaPlayerEnqueue | bool | None = None,
) -> None:
    """Send the media player the command for playing media."""
    menuai.add_job(async_play_media, menuai, media_type, media_id, entity_id, enqueue)


async def async_select_source(
    menuai: menuai, source: str, entity_id: str = ENTITY_MATCH_ALL
) -> None:
    """Send the media player the command to select input source."""
    data = {ATTR_INPUT_SOURCE: source}

    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id

    await menuai.services.async_call(DOMAIN, SERVICE_SELECT_SOURCE, data, blocking=True)


@bind_menuai
def select_source(
    menuai: menuai, source: str, entity_id: str = ENTITY_MATCH_ALL
) -> None:
    """Send the media player the command to select input source."""
    menuai.add_job(async_select_source, menuai, source, entity_id)


async def async_clear_playlist(
    menuai: menuai, entity_id: str = ENTITY_MATCH_ALL
) -> None:
    """Send the media player the command for clear playlist."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    await menuai.services.async_call(DOMAIN, SERVICE_CLEAR_PLAYLIST, data, blocking=True)


@bind_menuai
def clear_playlist(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Send the media player the command for clear playlist."""
    menuai.add_job(async_clear_playlist, menuai, entity_id)
