"""Provide add-on management."""

from __future__ import annotations

from menuai.components.menuaiio import AddonManager
from menuai.core import menuai, callback
from menuai.helpers.singleton import singleton

from .const import ADDON_SLUG, DOMAIN, LOGGER

DATA_ADDON_MANAGER = f"{DOMAIN}_addon_manager"


@singleton(DATA_ADDON_MANAGER)
@callback
def get_addon_manager(menuai: menuai) -> AddonManager:
    """Get the add-on manager."""
    return AddonManager(menuai, LOGGER, "Matter Server", ADDON_SLUG)
