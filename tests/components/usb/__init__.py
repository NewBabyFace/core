"""Tests for the USB Discovery integration."""

from unittest.mock import patch

from aiousbwatcher import InotifyNotAvailableError
import pytest

from menuai.components.usb import async_request_scan as usb_async_request_scan
from menuai.core import menuai


@pytest.fixture(name="force_usb_polling_watcher")
def force_usb_polling_watcher():
    """Patch the USB integration to not use inotify and fall back to polling."""
    with patch(
        "menuai.components.usb.AIOUSBWatcher.async_start",
        side_effect=InotifyNotAvailableError,
    ):
        yield


def patch_scanned_serial_ports(**kwargs) -> None:
    """Patch the USB integration's list of scanned serial ports."""
    return patch("menuai.components.usb.scan_serial_ports", **kwargs)


async def async_request_scan(menuai: menuai) -> None:
    """Request a USB scan."""
    return await usb_async_request_scan(menuai)
