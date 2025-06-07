"""The nuki component."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from http import HTTPStatus
import logging

from aiohttp import web
from pynuki import NukiBridge, NukiLock, NukiOpener
from pynuki.bridge import InvalidCredentialsException
from requests.exceptions import RequestException

from menuai import exceptions
from menuai.components import webhook
from menuai.config_entries import ConfigEntry
from menuai.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_TOKEN,
    EVENT_menuai_STOP,
    Platform,
)
from menuai.core import Event, menuai
from menuai.helpers import device_registry as dr, issue_registry as ir
from menuai.helpers.network import NoURLAvailableError, get_url
from menuai.helpers.update_coordinator import UpdateFailed

from .const import CONF_ENCRYPT_TOKEN, DEFAULT_TIMEOUT, DOMAIN
from .coordinator import NukiCoordinator
from .helpers import NukiWebhookException, parse_id

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.LOCK, Platform.SENSOR]


@dataclass(slots=True)
class NukiEntryData:
    """Class to hold Nuki data."""

    coordinator: NukiCoordinator
    bridge: NukiBridge
    locks: list[NukiLock]
    openers: list[NukiOpener]


def _get_bridge_devices(bridge: NukiBridge) -> tuple[list[NukiLock], list[NukiOpener]]:
    return bridge.locks, bridge.openers


async def _create_webhook(
    menuai: menuai, entry: ConfigEntry, bridge: NukiBridge
) -> None:
    # Create menuai webhook
    async def handle_webhook(
        menuai: menuai, webhook_id: str, request: web.Request
    ) -> web.Response:
        """Handle webhook callback."""
        try:
            data = await request.json()
        except ValueError:
            return web.Response(status=HTTPStatus.BAD_REQUEST)

        entry_data: NukiEntryData = menuai.data[DOMAIN][entry.entry_id]
        locks = entry_data.locks
        openers = entry_data.openers

        devices = [x for x in locks + openers if x.nuki_id == data["nukiId"]]
        if len(devices) == 1:
            devices[0].update_from_callback(data)

        coordinator = entry_data.coordinator
        coordinator.async_set_updated_data(None)

        return web.Response(status=HTTPStatus.OK)

    webhook.async_register(
        menuai, DOMAIN, entry.title, entry.entry_id, handle_webhook, local_only=True
    )

    webhook_url = webhook.async_generate_path(entry.entry_id)

    try:
        menuai_url = get_url(
            menuai,
            allow_cloud=False,
            allow_external=False,
            allow_ip=True,
            require_ssl=False,
        )
    except NoURLAvailableError:
        webhook.async_unregister(menuai, entry.entry_id)
        raise NukiWebhookException(
            f"Error registering URL for webhook {entry.entry_id}: "
            "menuai URL is not available"
        ) from None

    url = f"{menuai_url}{webhook_url}"

    if menuai_url.startswith("https"):
        ir.async_create_issue(
            menuai,
            DOMAIN,
            "https_webhook",
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="https_webhook",
            translation_placeholders={
                "base_url": menuai_url,
                "network_link": "https://my.home-assistant.io/redirect/network/",
            },
        )
    else:
        ir.async_delete_issue(menuai, DOMAIN, "https_webhook")

        try:
            async with asyncio.timeout(10):
                await menuai.async_add_executor_job(
                    _register_webhook, bridge, entry.entry_id, url
                )
        except InvalidCredentialsException as err:
            webhook.async_unregister(menuai, entry.entry_id)
            raise NukiWebhookException(
                f"Invalid credentials for Bridge: {err}"
            ) from err
        except RequestException as err:
            webhook.async_unregister(menuai, entry.entry_id)
            raise NukiWebhookException(
                f"Error communicating with Bridge: {err}"
            ) from err


def _register_webhook(bridge: NukiBridge, entry_id: str, url: str) -> bool:
    # Register HA URL as webhook if not already
    callbacks = bridge.callback_list()
    for item in callbacks["callbacks"]:
        if entry_id in item["url"]:
            if item["url"] == url:
                return True
            bridge.callback_remove(item["id"])

    if bridge.callback_add(url)["success"]:
        return True

    return False


def _remove_webhook(bridge: NukiBridge, entry_id: str) -> None:
    # Remove webhook if set
    callbacks = bridge.callback_list()
    for item in callbacks["callbacks"]:
        if entry_id in item["url"]:
            bridge.callback_remove(item["id"])


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up the Nuki entry."""

    menuai.data.setdefault(DOMAIN, {})

    # Migration of entry unique_id
    if isinstance(entry.unique_id, int):
        new_id = parse_id(entry.unique_id)
        params = {"unique_id": new_id}
        if entry.title == entry.unique_id:
            params["title"] = new_id
        menuai.config_entries.async_update_entry(entry, **params)

    try:
        bridge = await menuai.async_add_executor_job(
            NukiBridge,
            entry.data[CONF_HOST],
            entry.data[CONF_TOKEN],
            entry.data[CONF_PORT],
            entry.data.get(CONF_ENCRYPT_TOKEN, True),
            DEFAULT_TIMEOUT,
        )

        locks, openers = await menuai.async_add_executor_job(_get_bridge_devices, bridge)
    except InvalidCredentialsException as err:
        raise exceptions.ConfigEntryAuthFailed from err
    except RequestException as err:
        raise exceptions.ConfigEntryNotReady from err

    # Device registration for the bridge
    info = bridge.info()
    bridge_id = parse_id(info["ids"]["hardwareId"])
    dev_reg = dr.async_get(menuai)
    dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, bridge_id)},
        manufacturer="Nuki Home Solutions GmbH",
        name=f"Nuki Bridge {bridge_id}",
        model="Hardware Bridge",
        sw_version=info["versions"]["firmwareVersion"],
        serial_number=parse_id(info["ids"]["hardwareId"]),
    )

    try:
        await _create_webhook(menuai, entry, bridge)
    except NukiWebhookException as err:
        _LOGGER.warning("Error registering menuai webhook: %s", err)

    async def _stop_nuki(_: Event):
        """Stop and remove the Nuki webhook."""
        webhook.async_unregister(menuai, entry.entry_id)
        try:
            async with asyncio.timeout(10):
                await menuai.async_add_executor_job(
                    _remove_webhook, bridge, entry.entry_id
                )
        except InvalidCredentialsException as err:
            _LOGGER.error(
                "Error unregistering webhook, invalid credentials for bridge: %s", err
            )
        except RequestException as err:
            _LOGGER.error("Error communicating with bridge: %s", err)

    entry.async_on_unload(
        menuai.bus.async_listen_once(EVENT_menuai_STOP, _stop_nuki)
    )

    coordinator = NukiCoordinator(menuai, entry, bridge, locks, openers)
    menuai.data[DOMAIN][entry.entry_id] = NukiEntryData(
        coordinator=coordinator,
        bridge=bridge,
        locks=locks,
        openers=openers,
    )

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_refresh()

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload the Nuki entry."""
    webhook.async_unregister(menuai, entry.entry_id)
    entry_data: NukiEntryData = menuai.data[DOMAIN][entry.entry_id]

    try:
        async with asyncio.timeout(10):
            await menuai.async_add_executor_job(
                _remove_webhook,
                entry_data.bridge,
                entry.entry_id,
            )
    except InvalidCredentialsException as err:
        raise UpdateFailed(
            f"Unable to remove callback. Invalid credentials for Bridge: {err}"
        ) from err
    except RequestException as err:
        raise UpdateFailed(
            f"Unable to remove callback. Error communicating with Bridge: {err}"
        ) from err

    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
