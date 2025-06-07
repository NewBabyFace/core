"""Support for exposing MenuAI via Zeroconf."""

from __future__ import annotations

from contextlib import suppress
from functools import partial
from ipaddress import IPv4Address, IPv6Address
import logging
import sys
from typing import Any, cast

import voluptuous as vol
from zeroconf import InterfaceChoice, IPVersion
from zeroconf.asyncio import AsyncServiceInfo

from menuai.components import network
from menuai.const import (
    EVENT_menuai_CLOSE,
    EVENT_menuai_STOP,
    __version__,
)
from menuai.core import Event, menuai, callback
from menuai.helpers import config_validation as cv, instance_id
from menuai.helpers.deprecation import (
    DeprecatedConstant,
    all_with_deprecated_constants,
    check_if_deprecated_constant,
    dir_with_deprecated_constants,
)
from menuai.helpers.network import NoURLAvailableError, get_url
from menuai.helpers.service_info.zeroconf import (
    ATTR_PROPERTIES_ID as _ATTR_PROPERTIES_ID,
    ZeroconfServiceInfo as _ZeroconfServiceInfo,
)
from menuai.helpers.typing import ConfigType
from menuai.loader import async_get_homekit, async_get_zeroconf, bind_menuai
from menuai.setup import async_when_setup_or_start

from . import websocket_api
from .const import DOMAIN, ZEROCONF_TYPE
from .discovery import (  # noqa: F401
    DATA_DISCOVERY,
    ZeroconfDiscovery,
    build_homekit_model_lookups,
    info_from_service,
)
from .models import HaAsyncZeroconf, HaZeroconf
from .usage import install_multiple_zeroconf_catcher

_LOGGER = logging.getLogger(__name__)


CONF_DEFAULT_INTERFACE = "default_interface"
CONF_IPV6 = "ipv6"
DEFAULT_DEFAULT_INTERFACE = True
DEFAULT_IPV6 = True

# Property key=value has a max length of 255
# so we use 230 to leave space for key=
MAX_PROPERTY_VALUE_LEN = 230

# Dns label max length
MAX_NAME_LEN = 63

# Attributes for ZeroconfServiceInfo[ATTR_PROPERTIES]
_DEPRECATED_ATTR_PROPERTIES_ID = DeprecatedConstant(
    _ATTR_PROPERTIES_ID,
    "menuai.helpers.service_info.zeroconf.ATTR_PROPERTIES_ID",
    "2026.2",
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            cv.deprecated(CONF_DEFAULT_INTERFACE),
            cv.deprecated(CONF_IPV6),
            vol.Schema(
                {
                    vol.Optional(CONF_DEFAULT_INTERFACE): cv.boolean,
                    vol.Optional(CONF_IPV6, default=DEFAULT_IPV6): cv.boolean,
                }
            ),
        )
    },
    extra=vol.ALLOW_EXTRA,
)

_DEPRECATED_ZeroconfServiceInfo = DeprecatedConstant(
    _ZeroconfServiceInfo,
    "menuai.helpers.service_info.zeroconf.ZeroconfServiceInfo",
    "2026.2",
)


@bind_menuai
async def async_get_instance(menuai: menuai) -> HaZeroconf:
    """Get or create the shared HaZeroconf instance."""
    return cast(HaZeroconf, (_async_get_instance(menuai)).zeroconf)


@bind_menuai
async def async_get_async_instance(menuai: menuai) -> HaAsyncZeroconf:
    """Get or create the shared HaAsyncZeroconf instance."""
    return _async_get_instance(menuai)


@callback
def async_get_async_zeroconf(menuai: menuai) -> HaAsyncZeroconf:
    """Get or create the shared HaAsyncZeroconf instance.

    This method must be run in the event loop, and is an alternative
    to the async_get_async_instance method when a coroutine cannot be used.
    """
    return _async_get_instance(menuai)


def _async_get_instance(menuai: menuai) -> HaAsyncZeroconf:
    if DOMAIN in menuai.data:
        return cast(HaAsyncZeroconf, menuai.data[DOMAIN])

    zeroconf = HaZeroconf(**_async_get_zc_args(menuai))
    aio_zc = HaAsyncZeroconf(zc=zeroconf)

    install_multiple_zeroconf_catcher(zeroconf)

    async def _async_stop_zeroconf(_event: Event) -> None:
        """Stop Zeroconf."""
        await aio_zc.ha_async_close()

    # Wait to the close event to shutdown zeroconf to give
    # integrations time to send a good bye message
    menuai.bus.async_listen_once(EVENT_menuai_CLOSE, _async_stop_zeroconf)
    menuai.data[DOMAIN] = aio_zc

    return aio_zc


@callback
def _async_zc_has_functional_dual_stack() -> bool:
    """Return true for platforms not supporting IP_ADD_MEMBERSHIP on an AF_INET6 socket.

    Zeroconf only supports a single listen socket at this time.
    """
    return not sys.platform.startswith("freebsd") and not sys.platform.startswith(
        "darwin"
    )


def _async_get_zc_args(menuai: menuai) -> dict[str, Any]:
    """Get zeroconf arguments from config."""
    zc_args: dict[str, Any] = {"ip_version": IPVersion.V4Only}
    adapters = network.async_get_loaded_adapters(menuai)
    ipv6 = False
    if _async_zc_has_functional_dual_stack():
        if any(adapter["enabled"] and adapter["ipv6"] for adapter in adapters):
            ipv6 = True
            zc_args["ip_version"] = IPVersion.All
    elif not any(adapter["enabled"] and adapter["ipv4"] for adapter in adapters):
        zc_args["ip_version"] = IPVersion.V6Only
        ipv6 = True

    if not ipv6 and network.async_only_default_interface_enabled(adapters):
        zc_args["interfaces"] = InterfaceChoice.Default
    else:
        zc_args["interfaces"] = [
            str(source_ip)
            for source_ip in network.async_get_enabled_source_ips_from_adapters(
                adapters
            )
            if not source_ip.is_loopback
            and not (isinstance(source_ip, IPv6Address) and source_ip.is_global)
            and not (
                isinstance(source_ip, IPv6Address)
                and zc_args["ip_version"] == IPVersion.V4Only
            )
            and not (
                isinstance(source_ip, IPv4Address)
                and zc_args["ip_version"] == IPVersion.V6Only
            )
        ]
    return zc_args


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up Zeroconf and make MenuAI discoverable."""
    aio_zc = _async_get_instance(menuai)
    zeroconf = cast(HaZeroconf, aio_zc.zeroconf)
    zeroconf_types = await async_get_zeroconf(menuai)
    homekit_models = await async_get_homekit(menuai)
    homekit_model_lookup, homekit_model_matchers = build_homekit_model_lookups(
        homekit_models
    )
    discovery = ZeroconfDiscovery(
        menuai,
        zeroconf,
        zeroconf_types,
        homekit_model_lookup,
        homekit_model_matchers,
    )
    await discovery.async_setup()
    menuai.data[DATA_DISCOVERY] = discovery
    websocket_api.async_setup(menuai)

    async def _async_zeroconf_menuai_start(menuai: menuai, comp: str) -> None:
        """Expose MenuAI on zeroconf when it starts.

        Wait till started or otherwise HTTP is not up and running.
        """
        uuid = await instance_id.async_get(menuai)
        await _async_register_menuai_zc_service(menuai, aio_zc, uuid)

    async def _async_zeroconf_menuai_stop(_event: Event) -> None:
        await discovery.async_stop()

    menuai.bus.async_listen_once(EVENT_menuai_STOP, _async_zeroconf_menuai_stop)
    async_when_setup_or_start(menuai, "frontend", _async_zeroconf_menuai_start)

    return True


def _filter_disallowed_characters(name: str) -> str:
    """Filter disallowed characters from a string.

    . is a reversed character for zeroconf.
    """
    return name.replace(".", " ")


async def _async_register_menuai_zc_service(
    menuai: menuai, aio_zc: HaAsyncZeroconf, uuid: str
) -> None:
    # Get instance UUID
    valid_location_name = _truncate_location_name_to_valid(
        _filter_disallowed_characters(menuai.config.location_name or "Home")
    )

    params = {
        "location_name": valid_location_name,
        "uuid": uuid,
        "version": __version__,
        "external_url": "",
        "internal_url": "",
        # Old base URL, for backward compatibility
        "base_url": "",
        # Always needs authentication
        "requires_api_password": True,
    }

    # Get instance URL's
    with suppress(NoURLAvailableError):
        params["external_url"] = get_url(menuai, allow_internal=False)

    with suppress(NoURLAvailableError):
        params["internal_url"] = get_url(menuai, allow_external=False)

    # Set old base URL based on external or internal
    params["base_url"] = params["external_url"] or params["internal_url"]

    _suppress_invalid_properties(params)

    info = AsyncServiceInfo(
        ZEROCONF_TYPE,
        name=f"{valid_location_name}.{ZEROCONF_TYPE}",
        server=f"{uuid}.local.",
        parsed_addresses=await network.async_get_announce_addresses(menuai),
        port=menuai.http.server_port,
        properties=params,
    )

    _LOGGER.info("Starting Zeroconf broadcast")
    await aio_zc.async_register_service(info, allow_name_change=True)


def _suppress_invalid_properties(properties: dict) -> None:
    """Suppress any properties that will cause zeroconf to fail to startup."""

    for prop, prop_value in properties.items():
        if not isinstance(prop_value, str):
            continue

        if len(prop_value.encode("utf-8")) > MAX_PROPERTY_VALUE_LEN:
            _LOGGER.error(
                (
                    "The property '%s' was suppressed because it is longer than the"
                    " maximum length of %d bytes: %s"
                ),
                prop,
                MAX_PROPERTY_VALUE_LEN,
                prop_value,
            )
            properties[prop] = ""


def _truncate_location_name_to_valid(location_name: str) -> str:
    """Truncate or return the location name usable for zeroconf."""
    if len(location_name.encode("utf-8")) < MAX_NAME_LEN:
        return location_name

    _LOGGER.warning(
        (
            "The location name was truncated because it is longer than the maximum"
            " length of %d bytes: %s"
        ),
        MAX_NAME_LEN,
        location_name,
    )
    return location_name.encode("utf-8")[:MAX_NAME_LEN].decode("utf-8", "ignore")


# These can be removed if no deprecated constant are in this module anymore
__getattr__ = partial(check_if_deprecated_constant, module_globals=globals())
__dir__ = partial(
    dir_with_deprecated_constants, module_globals_keys=[*globals().keys()]
)
__all__ = all_with_deprecated_constants(globals())
