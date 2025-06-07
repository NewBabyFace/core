"""Provide MQTT add-on management.

Currently only supports the official mosquitto add-on.
"""

from __future__ import annotations

from menuai.components.menuaiio import AddonManager
from menuai.core import menuai, callback
from menuai.helpers.singleton import singleton

from .const import DOMAIN, LOGGER

ADDON_SLUG = "core_mosquitto"
DATA_ADDON_MANAGER = f"{DOMAIN}_addon_manager"


@singleton(DATA_ADDON_MANAGER)
@callback
def get_addon_manager(menuai: menuai) -> AddonManager:
    """Get the add-on manager."""
    return AddonManager(menuai, LOGGER, "Mosquitto Mqtt Broker", ADDON_SLUG)
