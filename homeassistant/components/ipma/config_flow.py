"""Config flow to configure IPMA component."""

import logging
from typing import Any

from pyipma import IPMAException
from pyipma.api import IPMA_API
from pyipma.location import Location
import voluptuous as vol

from menuai.config_entries import ConfigFlow, ConfigFlowResult
from menuai.const import CONF_LATITUDE, CONF_LONGITUDE
from menuai.helpers import config_validation as cv
from menuai.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class IpmaFlowHandler(ConfigFlow, domain=DOMAIN):
    """Config flow for IPMA component."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors = {}

        if user_input is not None:
            self._async_abort_entries_match(user_input)

            api = IPMA_API(async_get_clientsession(self.menuai))

            try:
                location = await Location.get(
                    api,
                    user_input[CONF_LATITUDE],
                    user_input[CONF_LONGITUDE],
                )
            except IPMAException:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=location.name, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_LATITUDE): cv.latitude,
                        vol.Required(CONF_LONGITUDE): cv.longitude,
                    }
                ),
                {
                    CONF_LATITUDE: self.menuai.config.latitude,
                    CONF_LONGITUDE: self.menuai.config.longitude,
                },
            ),
            errors=errors,
        )
