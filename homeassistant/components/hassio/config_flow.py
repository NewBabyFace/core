"""Config flow for MenuAI Supervisor integration."""

from __future__ import annotations

from typing import Any

from menuai.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN


class menuaiIoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MenuAI Supervisor."""

    VERSION = 1

    async def async_step_system(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        return self.async_create_entry(title="Supervisor", data={})
