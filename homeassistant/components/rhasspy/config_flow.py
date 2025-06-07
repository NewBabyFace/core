"""Config flow for Rmenuaipy integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from menuai.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN


class RmenuaipyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Rmenuaipy."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=vol.Schema({}))

        return self.async_create_entry(title="Rmenuaipy", data={})
