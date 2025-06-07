"""The ElevenLabs text-to-speech integration."""

from __future__ import annotations

from dataclasses import dataclass

from elevenlabs import AsyncElevenLabs, Model
from elevenlabs.core import ApiError
from httpx import ConnectError

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_API_KEY, Platform
from menuai.core import menuai
from menuai.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryError,
    ConfigEntryNotReady,
)
from menuai.helpers.httpx_client import get_async_client

from .const import CONF_MODEL

PLATFORMS: list[Platform] = [Platform.TTS]


async def get_model_by_id(client: AsyncElevenLabs, model_id: str) -> Model | None:
    """Get ElevenLabs model from their API by the model_id."""
    models = await client.models.get_all()
    for maybe_model in models:
        if maybe_model.model_id == model_id:
            return maybe_model
    return None


@dataclass(kw_only=True, slots=True)
class ElevenLabsData:
    """ElevenLabs data type."""

    client: AsyncElevenLabs
    model: Model


type ElevenLabsConfigEntry = ConfigEntry[ElevenLabsData]


async def async_setup_entry(menuai: menuai, entry: ElevenLabsConfigEntry) -> bool:
    """Set up ElevenLabs text-to-speech from a config entry."""
    entry.add_update_listener(update_listener)
    httpx_client = get_async_client(menuai)
    client = AsyncElevenLabs(
        api_key=entry.data[CONF_API_KEY], httpx_client=httpx_client
    )
    model_id = entry.options[CONF_MODEL]
    try:
        model = await get_model_by_id(client, model_id)
    except ConnectError as err:
        raise ConfigEntryNotReady("Failed to connect") from err
    except ApiError as err:
        raise ConfigEntryAuthFailed("Auth failed") from err

    if model is None or (not model.languages):
        raise ConfigEntryError("Model could not be resolved")

    entry.runtime_data = ElevenLabsData(client=client, model=model)
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ElevenLabsConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def update_listener(
    menuai: menuai, config_entry: ElevenLabsConfigEntry
) -> None:
    """Handle options update."""
    await menuai.config_entries.async_reload(config_entry.entry_id)
