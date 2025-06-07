"""Config flow for Gree."""

from greeclimate.discovery import Discovery

from menuai.components.network import async_get_ipv4_broadcast_addresses
from menuai.core import menuai
from menuai.helpers import config_entry_flow

from .const import DISCOVERY_TIMEOUT, DOMAIN


async def _async_has_devices(menuai: menuai) -> bool:
    """Return if there are devices that can be discovered."""
    gree_discovery = Discovery(DISCOVERY_TIMEOUT)
    bcast_addr = list(await async_get_ipv4_broadcast_addresses(menuai))
    devices = await gree_discovery.scan(
        wait_for=DISCOVERY_TIMEOUT, bcast_ifaces=bcast_addr
    )
    return len(devices) > 0


config_entry_flow.register_discovery_flow(DOMAIN, "Gree Climate", _async_has_devices)
