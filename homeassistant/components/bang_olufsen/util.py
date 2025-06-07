"""Various utilities for the Bang & Olufsen integration."""

from __future__ import annotations

from menuai.core import menuai
from menuai.helpers import device_registry as dr
from menuai.helpers.device_registry import DeviceEntry

from .const import DOMAIN


def get_device(menuai: menuai, unique_id: str) -> DeviceEntry:
    """Get the device."""
    device_registry = dr.async_get(menuai)
    device = device_registry.async_get_device({(DOMAIN, unique_id)})
    assert device

    return device


def get_serial_number_from_jid(jid: str) -> str:
    """Get serial number from Beolink JID."""
    return jid.split(".")[2].split("@")[0]
