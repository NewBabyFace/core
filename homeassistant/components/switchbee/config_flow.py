"""Config flow for SwitchBee Smart Home integration."""

from __future__ import annotations

import logging
from typing import Any

from switchbee.api.central_unit import SwitchBeeError
from switchbee.api.polling import CentralUnitPolling
import voluptuous as vol

from menuai.config_entries import ConfigFlow, ConfigFlowResult
from menuai.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import config_validation as cv
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.device_registry import format_mac

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)


async def validate_input(menuai: menuai, data: dict[str, Any]) -> str:
    """Validate the user input allows us to connect."""

    websession = async_get_clientsession(menuai, verify_ssl=False)
    api = CentralUnitPolling(
        data[CONF_HOST], data[CONF_USERNAME], data[CONF_PASSWORD], websession
    )
    try:
        await api.connect()
    except SwitchBeeError as exp:
        _LOGGER.error(exp)
        if "LOGIN_FAILED" in str(exp):
            raise InvalidAuth from exp

        raise CannotConnect from exp

    if api.unique_id:
        return api.unique_id

    assert api.mac is not None
    return format_mac(api.mac)


class SwitchBeeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SwitchBee Smart Home."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the setup form to the user."""
        errors: dict[str, str] = {}

        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
            )

        try:
            unique_id = await validate_input(self.menuai, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"

        else:
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_HOST], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(menuaiError):
    """Error to indicate we cannot connect."""


class InvalidAuth(menuaiError):
    """Error to indicate there is invalid auth."""
