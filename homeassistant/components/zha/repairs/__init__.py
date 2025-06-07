"""ZHA repairs for common environmental and device problems."""

from __future__ import annotations

from typing import Any, cast

from menuai.components.repairs import ConfirmRepairFlow, RepairsFlow
from menuai.core import menuai
from menuai.helpers import issue_registry as ir

from ..const import DOMAIN
from .network_settings_inconsistent import (
    ISSUE_INCONSISTENT_NETWORK_SETTINGS,
    NetworkSettingsInconsistentFlow,
)
from .wrong_silabs_firmware import ISSUE_WRONG_SILABS_FIRMWARE_INSTALLED


def async_delete_blocking_issues(menuai: menuai) -> None:
    """Delete repair issues that should disappear on a successful startup."""
    ir.async_delete_issue(menuai, DOMAIN, ISSUE_WRONG_SILABS_FIRMWARE_INSTALLED)
    ir.async_delete_issue(menuai, DOMAIN, ISSUE_INCONSISTENT_NETWORK_SETTINGS)


async def async_create_fix_flow(
    menuai: menuai,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create flow."""
    if issue_id == ISSUE_INCONSISTENT_NETWORK_SETTINGS:
        return NetworkSettingsInconsistentFlow(menuai, cast(dict[str, Any], data))

    return ConfirmRepairFlow()
