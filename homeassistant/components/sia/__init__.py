"""The sia integration."""

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_PORT
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady

from .const import DOMAIN, PLATFORMS
from .hub import SIAHub


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up sia from a config entry."""
    hub: SIAHub = SIAHub(menuai, entry)
    hub.async_setup_hub()

    menuai.data.setdefault(DOMAIN, {})
    menuai.data[DOMAIN][entry.entry_id] = hub
    try:
        if hub.sia_client:
            await hub.sia_client.async_start(reuse_port=True)
    except OSError as exc:
        raise ConfigEntryNotReady(
            f"SIA Server at port {entry.data[CONF_PORT]} could not start."
        ) from exc
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hub: SIAHub = menuai.data[DOMAIN].pop(entry.entry_id)
        await hub.async_shutdown()
    return unload_ok
