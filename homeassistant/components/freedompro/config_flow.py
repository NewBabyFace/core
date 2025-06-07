"""Config flow to configure Freedompro."""

from typing import Any

from pyfreedompro import get_list
import voluptuous as vol

from menuai.config_entries import ConfigFlow, ConfigFlowResult
from menuai.const import CONF_API_KEY
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import aiohttp_client

from .const import DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema({vol.Required(CONF_API_KEY): str})


class Hub:
    """Freedompro Hub class."""

    def __init__(self, menuai: menuai, api_key: str) -> None:
        """Freedompro Hub class init."""
        self._menuai = menuai
        self._api_key = api_key

    async def authenticate(self) -> dict[str, Any]:
        """Freedompro Hub class authenticate."""
        return await get_list(
            aiohttp_client.async_get_clientsession(self._menuai), self._api_key
        )


async def validate_input(menuai: menuai, api_key: str) -> None:
    """Validate api key."""
    hub = Hub(menuai, api_key)
    result = await hub.authenticate()
    if result["state"] is False:
        if result["code"] == -201:
            raise InvalidAuth
        if result["code"] == -200:
            raise CannotConnect


class FreedomProConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the setup form to the user."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            await validate_input(self.menuai, user_input[CONF_API_KEY])
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        else:
            return self.async_create_entry(title="Freedompro", data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(menuaiError):
    """Error to indicate we cannot connect."""


class InvalidAuth(menuaiError):
    """Error to indicate there is invalid auth."""
