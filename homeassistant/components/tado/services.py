"""Services for the Tado integration."""

import logging

import voluptuous as vol

from menuai.core import menuai, ServiceCall, callback
from menuai.exceptions import menuaiError, ServiceValidationError
from menuai.helpers import selector

from .const import (
    ATTR_MESSAGE,
    CONF_CONFIG_ENTRY,
    CONF_READING,
    DOMAIN,
    SERVICE_ADD_METER_READING,
)

_LOGGER = logging.getLogger(__name__)
SCHEMA_ADD_METER_READING = vol.Schema(
    {
        vol.Required(CONF_CONFIG_ENTRY): selector.ConfigEntrySelector(
            {
                "integration": DOMAIN,
            }
        ),
        vol.Required(CONF_READING): vol.Coerce(int),
    }
)


@callback
def setup_services(menuai: menuai) -> None:
    """Set up the services for the Tado integration."""

    async def add_meter_reading(call: ServiceCall) -> None:
        """Send meter reading to Tado."""
        entry_id: str = call.data[CONF_CONFIG_ENTRY]
        reading: int = call.data[CONF_READING]
        _LOGGER.debug("Add meter reading %s", reading)

        entry = menuai.config_entries.async_get_entry(entry_id)
        if entry is None:
            raise ServiceValidationError("Config entry not found")

        coordinator = entry.runtime_data.coordinator
        response: dict = await coordinator.set_meter_reading(call.data[CONF_READING])

        if ATTR_MESSAGE in response:
            raise menuaiError(response[ATTR_MESSAGE])

    menuai.services.async_register(
        DOMAIN, SERVICE_ADD_METER_READING, add_meter_reading, SCHEMA_ADD_METER_READING
    )
