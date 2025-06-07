"""Config flow for flo integration."""

from typing import Any

from aioflo import async_get_api
from aioflo.errors import RequestError
import voluptuous as vol

from menuai.config_entries import ConfigFlow, ConfigFlowResult
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, LOGGER

DATA_SCHEMA = vol.Schema(
    {vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str}
)


async def validate_input(menuai: menuai, data):
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """

    session = async_get_clientsession(menuai)
    try:
        await async_get_api(data[CONF_USERNAME], data[CONF_PASSWORD], session=session)
    except RequestError as request_error:
        LOGGER.error("Error connecting to the Flo API: %s", request_error)
        raise CannotConnect from request_error


class FloConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for flo."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_USERNAME])
            self._abort_if_unique_id_configured()
            try:
                await validate_input(self.menuai, user_input)
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME], data=user_input
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class CannotConnect(menuaiError):
    """Error to indicate we cannot connect."""
