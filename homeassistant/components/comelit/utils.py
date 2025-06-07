"""Utils for Comelit."""

from collections.abc import Awaitable, Callable, Coroutine
from functools import wraps
from typing import Any, Concatenate

from aiocomelit import ComelitSerialBridgeObject
from aiocomelit.exceptions import CannotAuthenticate, CannotConnect, CannotRetrieveData
from aiohttp import ClientSession, CookieJar

from menuai.components.climate import DOMAIN as CLIMATE_DOMAIN
from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import (
    aiohttp_client,
    device_registry as dr,
    entity_registry as er,
)

from .const import _LOGGER, DOMAIN
from .entity import ComelitBridgeBaseEntity


async def async_client_session(menuai: menuai) -> ClientSession:
    """Return a new aiohttp session."""
    return aiohttp_client.async_create_clientsession(
        menuai, verify_ssl=False, cookie_jar=CookieJar(unsafe=True)
    )


def load_api_data(device: ComelitSerialBridgeObject, domain: str) -> list[Any]:
    """Load data from the API."""
    # This function is called when the data is loaded from the API
    if not isinstance(device.val, list):
        raise menuaiError(
            translation_domain=domain, translation_key="invalid_clima_data"
        )
    # CLIMATE has a 2 item tuple:
    # - first  for Clima
    # - second for Humidifier
    return device.val[0] if domain == CLIMATE_DOMAIN else device.val[1]


async def cleanup_stale_entity(
    menuai: menuai,
    config_entry: ConfigEntry,
    entry_unique_id: str,
    device: ComelitSerialBridgeObject,
) -> None:
    """Cleanup stale entity."""
    entity_reg: er.EntityRegistry = er.async_get(menuai)

    identifiers: list[str] = []

    for entry in er.async_entries_for_config_entry(entity_reg, config_entry.entry_id):
        if entry.unique_id == entry_unique_id:
            entry_name = entry.name or entry.original_name
            _LOGGER.info("Removing entity: %s [%s]", entry.entity_id, entry_name)
            entity_reg.async_remove(entry.entity_id)
            identifiers.append(f"{config_entry.entry_id}-{device.type}-{device.index}")

    if len(identifiers) > 0:
        _async_remove_state_config_entry_from_devices(menuai, identifiers, config_entry)


def _async_remove_state_config_entry_from_devices(
    menuai: menuai, identifiers: list[str], config_entry: ConfigEntry
) -> None:
    """Remove config entry from device."""

    device_registry = dr.async_get(menuai)
    for identifier in identifiers:
        device = device_registry.async_get_device(identifiers={(DOMAIN, identifier)})
        if device:
            _LOGGER.info(
                "Removing config entry %s from device %s",
                config_entry.title,
                device.name,
            )
            device_registry.async_update_device(
                device_id=device.id,
                remove_config_entry_id=config_entry.entry_id,
            )


def bridge_api_call[_T: ComelitBridgeBaseEntity, **_P](
    func: Callable[Concatenate[_T, _P], Awaitable[None]],
) -> Callable[Concatenate[_T, _P], Coroutine[Any, Any, None]]:
    """Catch Bridge API call exceptions."""

    @wraps(func)
    async def cmd_wrapper(self: _T, *args: _P.args, **kwargs: _P.kwargs) -> None:
        """Wrap all command methods."""
        try:
            await func(self, *args, **kwargs)
        except CannotConnect as err:
            self.coordinator.last_update_success = False
            raise menuaiError(
                translation_domain=DOMAIN,
                translation_key="cannot_connect",
                translation_placeholders={"error": repr(err)},
            ) from err
        except CannotRetrieveData as err:
            self.coordinator.last_update_success = False
            raise menuaiError(
                translation_domain=DOMAIN,
                translation_key="cannot_retrieve_data",
                translation_placeholders={"error": repr(err)},
            ) from err
        except CannotAuthenticate:
            self.coordinator.last_update_success = False
            self.coordinator.config_entry.async_start_reauth(self.menuai)

    return cmd_wrapper
