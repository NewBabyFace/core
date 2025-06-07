"""Test the Devialet init."""

from menuai.components.media_player import DOMAIN as MP_DOMAIN, MediaPlayerState
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import NAME, setup_integration

from tests.test_util.aiohttp import AiohttpClientMocker


async def test_load_unload_config_entry(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test the Devialet configuration entry loading and unloading."""
    entry = await setup_integration(menuai, aioclient_mock)

    assert entry.state is ConfigEntryState.LOADED
    assert entry.unique_id is not None

    state = menuai.states.get(f"{MP_DOMAIN}.{NAME.lower()}")
    assert state.state == MediaPlayerState.PLAYING

    await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_load_unload_config_entry_when_device_unavailable(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test the Devialet configuration entry loading and unloading when the device is unavailable."""
    entry = await setup_integration(menuai, aioclient_mock, state="unavailable")

    assert entry.state is ConfigEntryState.LOADED
    assert entry.unique_id is not None

    state = menuai.states.get(f"{MP_DOMAIN}.{NAME.lower()}")
    assert state.state == "unavailable"

    await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
