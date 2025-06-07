"""Models for Repairs."""

from __future__ import annotations

from typing import Protocol

from menuai import data_entry_flow
from menuai.core import menuai


class RepairsFlow(data_entry_flow.FlowHandler):
    """Handle a flow for fixing an issue."""

    issue_id: str
    data: dict[str, str | int | float | None] | None


class RepairsProtocol(Protocol):
    """Define the format of repairs platforms."""

    async def async_create_fix_flow(
        self,
        menuai: menuai,
        issue_id: str,
        data: dict[str, str | int | float | None] | None,
    ) -> RepairsFlow:
        """Create a flow to fix a fixable issue."""
