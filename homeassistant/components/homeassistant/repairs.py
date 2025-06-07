"""Repairs for MenuAI."""

from __future__ import annotations

from menuai.components.repairs import ConfirmRepairFlow, RepairsFlow
from menuai.core import menuai
from menuai.data_entry_flow import FlowResult
from menuai.helpers import issue_registry as ir

from .const import DOMAIN


class IntegrationNotFoundFlow(RepairsFlow):
    """Handler for an issue fixing flow."""

    def __init__(self, data: dict[str, str]) -> None:
        """Initialize."""
        self.domain = data["domain"]
        self.description_placeholders: dict[str, str] = data

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the first step of a fix flow."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["confirm", "ignore"],
            description_placeholders=self.description_placeholders,
        )

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the confirm step of a fix flow."""
        entries = self.menuai.config_entries.async_entries(self.domain)
        for entry in entries:
            await self.menuai.config_entries.async_remove(entry.entry_id)
        return self.async_create_entry(data={})

    async def async_step_ignore(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the ignore step of a fix flow."""
        ir.async_get(self.menuai).async_ignore(
            DOMAIN, f"integration_not_found.{self.domain}", True
        )
        return self.async_abort(
            reason="issue_ignored",
            description_placeholders=self.description_placeholders,
        )


async def async_create_fix_flow(
    menuai: menuai, issue_id: str, data: dict[str, str] | None
) -> RepairsFlow:
    """Create flow."""

    if issue_id.split(".")[0] == "integration_not_found":
        assert data
        return IntegrationNotFoundFlow(data)
    return ConfirmRepairFlow()
