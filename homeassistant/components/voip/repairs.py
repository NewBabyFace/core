"""Repairs implementation for the VoIP integration."""

from __future__ import annotations

from menuai.components.assist_pipeline.repair_flows import (
    AssistInProgressDeprecatedRepairFlow,
)
from menuai.components.repairs import RepairsFlow
from menuai.core import menuai


async def async_create_fix_flow(
    menuai: menuai,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create flow."""
    if issue_id.startswith("assist_in_progress_deprecated"):
        return AssistInProgressDeprecatedRepairFlow(data)
    # If VoIP adds confirm-only repairs in the future, this should be changed
    # to return a ConfirmRepairFlow instead of raising a ValueError
    raise ValueError(f"unknown repair {issue_id}")
