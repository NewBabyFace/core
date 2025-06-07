"""Diagnostics support for Tailscale."""

from __future__ import annotations

import json
from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_API_KEY
from menuai.core import menuai

from .const import CONF_TAILNET, DOMAIN
from .coordinator import TailscaleDataUpdateCoordinator

TO_REDACT = {
    CONF_API_KEY,
    CONF_TAILNET,
    "addresses",
    "device_id",
    "endpoints",
    "hostname",
    "machine_key",
    "name",
    "node_key",
    "user",
}


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: TailscaleDataUpdateCoordinator = menuai.data[DOMAIN][entry.entry_id]
    # Round-trip via JSON to trigger serialization
    devices = [json.loads(device.to_json()) for device in coordinator.data.values()]
    return async_redact_data({"devices": devices}, TO_REDACT)
