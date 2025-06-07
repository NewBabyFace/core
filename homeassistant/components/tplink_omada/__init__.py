"""The TP-Link Omada integration."""

from __future__ import annotations

from tplink_omada_client import OmadaSite
from tplink_omada_client.devices import OmadaListDevice
from tplink_omada_client.exceptions import (
    ConnectionFailed,
    LoginFailed,
    OmadaClientException,
    UnsupportedControllerVersion,
)

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai, ServiceCall
from menuai.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from menuai.helpers import device_registry as dr

from .config_flow import CONF_SITE, create_omada_client
from .const import DOMAIN
from .controller import OmadaSiteController

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.DEVICE_TRACKER,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.UPDATE,
]


type OmadaConfigEntry = ConfigEntry[OmadaSiteController]


async def async_setup_entry(menuai: menuai, entry: OmadaConfigEntry) -> bool:
    """Set up TP-Link Omada from a config entry."""

    try:
        client = await create_omada_client(menuai, entry.data)
        await client.login()

    except (LoginFailed, UnsupportedControllerVersion) as ex:
        raise ConfigEntryAuthFailed(
            f"Omada controller refused login attempt: {ex}"
        ) from ex
    except ConnectionFailed as ex:
        raise ConfigEntryNotReady(
            f"Omada controller could not be reached: {ex}"
        ) from ex

    except OmadaClientException as ex:
        raise ConfigEntryNotReady(
            f"Unexpected error connecting to Omada controller: {ex}"
        ) from ex

    site_client = await client.get_site_client(OmadaSite("", entry.data[CONF_SITE]))
    controller = OmadaSiteController(menuai, entry, site_client)
    await controller.initialize_first_refresh()

    entry.runtime_data = controller

    async def handle_reconnect_client(call: ServiceCall) -> None:
        """Handle the service action call."""
        mac: str | None = call.data.get("mac")
        if not mac:
            return

        await site_client.reconnect_client(mac)

    menuai.services.async_register(DOMAIN, "reconnect_client", handle_reconnect_client)

    _remove_old_devices(menuai, entry, controller.devices_coordinator.data)

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: OmadaConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not menuai.config_entries.async_loaded_entries(DOMAIN):
        # This is the last loaded instance of Omada, deregister any services
        menuai.services.async_remove(DOMAIN, "reconnect_client")

    return unload_ok


def _remove_old_devices(
    menuai: menuai,
    entry: OmadaConfigEntry,
    omada_devices: dict[str, OmadaListDevice],
) -> None:
    device_registry = dr.async_get(menuai)

    for registered_device in device_registry.devices.get_devices_for_config_entry_id(
        entry.entry_id
    ):
        mac = next(
            (i[1] for i in registered_device.identifiers if i[0] == DOMAIN), None
        )
        if mac and mac not in omada_devices:
            device_registry.async_update_device(
                registered_device.id, remove_config_entry_id=entry.entry_id
            )
