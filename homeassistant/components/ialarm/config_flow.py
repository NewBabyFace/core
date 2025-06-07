"""Config flow for Antifurto365 iAlarm integration."""

import logging
from typing import Any

from pyialarm import IAlarm
import voluptuous as vol

from menuai.config_entries import ConfigFlow, ConfigFlowResult
from menuai.const import CONF_HOST, CONF_PORT
from menuai.core import menuai

from .const import DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
    }
)


async def _get_device_mac(menuai: menuai, host, port):
    ialarm = IAlarm(host, port)
    return await menuai.async_add_executor_job(ialarm.get_mac)


class IAlarmConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Antifurto365 iAlarm."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}
        mac = None

        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)

        host = user_input[CONF_HOST]
        port = user_input[CONF_PORT]

        try:
            # If we are able to get the MAC address, we are able to establish
            # a connection to the device.
            mac = await _get_device_mac(self.menuai, host, port)
        except ConnectionError:
            errors["base"] = "cannot_connect"
        except Exception:
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"

        if errors:
            return self.async_show_form(
                step_id="user", data_schema=DATA_SCHEMA, errors=errors
            )

        await self.async_set_unique_id(mac)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(title=user_input[CONF_HOST], data=user_input)
