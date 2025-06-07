"""Config flow to configure the Open-Meteo integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from menuai.components.zone import DOMAIN as ZONE_DOMAIN
from menuai.config_entries import ConfigFlow, ConfigFlowResult
from menuai.const import CONF_ZONE
from menuai.helpers.selector import EntitySelector, EntitySelectorConfig

from .const import DOMAIN


class OpenMeteoFlowHandler(ConfigFlow, domain=DOMAIN):
    """Config flow for OpenMeteo."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_ZONE])
            self._abort_if_unique_id_configured()

            state = self.menuai.states.get(user_input[CONF_ZONE])
            return self.async_create_entry(
                title=state.name if state else "Open-Meteo",
                data={CONF_ZONE: user_input[CONF_ZONE]},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ZONE): EntitySelector(
                        EntitySelectorConfig(domain=ZONE_DOMAIN),
                    ),
                }
            ),
        )
