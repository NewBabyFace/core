"""Component for wiffi support."""

from datetime import timedelta
import errno
import logging

from wiffi import WiffiTcpServer

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_PORT, Platform
from menuai.core import menuai, callback
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers.dispatcher import async_dispatcher_send
from menuai.helpers.event import async_track_time_interval

from .const import (
    CHECK_ENTITIES_SIGNAL,
    CREATE_ENTITY_SIGNAL,
    DOMAIN,
    UPDATE_ENTITY_SIGNAL,
)
from .entity import generate_unique_id

_LOGGER = logging.getLogger(__name__)


PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up wiffi from a config entry, config_entry contains data from config entry database."""
    if not entry.update_listeners:
        entry.add_update_listener(async_update_options)

    # create api object
    api = WiffiIntegrationApi(menuai)
    api.async_setup(entry)

    # store api object
    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = api

    try:
        await api.server.start_server()
    except OSError as exc:
        if exc.errno != errno.EADDRINUSE:
            _LOGGER.error("Start_server failed, errno: %d", exc.errno)
            return False
        _LOGGER.error("Port %s already in use", entry.data[CONF_PORT])
        raise ConfigEntryNotReady from exc

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_update_options(menuai: menuai, entry: ConfigEntry) -> None:
    """Update options."""
    await menuai.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    api: WiffiIntegrationApi = menuai.data[DOMAIN][entry.entry_id]
    await api.server.close_server()

    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        api = menuai.data[DOMAIN].pop(entry.entry_id)
        api.shutdown()

    return unload_ok


class WiffiIntegrationApi:
    """API object for wiffi handling. Stored in menuai.data."""

    def __init__(self, menuai):
        """Initialize the instance."""
        self._menuai = menuai
        self._server = None
        self._known_devices = {}
        self._periodic_callback = None

    def async_setup(self, config_entry):
        """Set up api instance."""
        self._server = WiffiTcpServer(config_entry.data[CONF_PORT], self)
        self._periodic_callback = async_track_time_interval(
            self._menuai, self._periodic_tick, timedelta(seconds=10)
        )

    def shutdown(self):
        """Shutdown wiffi api.

        Remove listener for periodic callbacks.
        """
        if (remove_listener := self._periodic_callback) is not None:
            remove_listener()

    async def __call__(self, device, metrics):
        """Process callback from TCP server if new data arrives from a device."""
        if device.mac_address not in self._known_devices:
            # add empty set for new device
            self._known_devices[device.mac_address] = set()

        for metric in metrics:
            if metric.id not in self._known_devices[device.mac_address]:
                self._known_devices[device.mac_address].add(metric.id)
                async_dispatcher_send(self._menuai, CREATE_ENTITY_SIGNAL, device, metric)
            else:
                async_dispatcher_send(
                    self._menuai,
                    f"{UPDATE_ENTITY_SIGNAL}-{generate_unique_id(device, metric)}",
                    device,
                    metric,
                )

    @property
    def server(self):
        """Return TCP server instance for start + close."""
        return self._server

    @callback
    def _periodic_tick(self, now=None):
        """Check if any entity has timed out because it has not been updated."""
        async_dispatcher_send(self._menuai, CHECK_ENTITIES_SIGNAL)
