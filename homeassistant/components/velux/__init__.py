"""Support for VELUX KLF 200 devices."""

from pyvlx import PyVLX, PyVLXException

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, CONF_PASSWORD, EVENT_menuai_STOP
from menuai.core import menuai, ServiceCall

from .const import DOMAIN, LOGGER, PLATFORMS


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up the velux component."""
    module = VeluxModule(menuai, entry.data)
    try:
        module.setup()
        await module.async_start()

    except PyVLXException as ex:
        LOGGER.exception("Can't connect to velux interface: %s", ex)
        return False

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = module

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


class VeluxModule:
    """Abstraction for velux component."""

    def __init__(self, menuai, domain_config):
        """Initialize for velux component."""
        self.pyvlx = None
        self._menuai = menuai
        self._domain_config = domain_config

    def setup(self):
        """Velux component setup."""

        async def on_menuai_stop(event):
            """Close connection when menuai stops."""
            LOGGER.debug("Velux interface terminated")
            await self.pyvlx.disconnect()

        async def async_reboot_gateway(service_call: ServiceCall) -> None:
            await self.pyvlx.reboot_gateway()

        self._menuai.bus.async_listen_once(EVENT_menuai_STOP, on_menuai_stop)
        host = self._domain_config.get(CONF_HOST)
        password = self._domain_config.get(CONF_PASSWORD)
        self.pyvlx = PyVLX(host=host, password=password)

        self._menuai.services.async_register(
            DOMAIN, "reboot_gateway", async_reboot_gateway
        )

    async def async_start(self):
        """Start velux component."""
        LOGGER.debug("Velux interface started")
        await self.pyvlx.load_scenes()
        await self.pyvlx.load_nodes()
