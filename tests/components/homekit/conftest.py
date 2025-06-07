"""HomeKit session fixtures."""

import asyncio
from collections.abc import Generator
from contextlib import suppress
import os
from unittest.mock import MagicMock, patch

import pytest

from menuai.components.device_tracker.legacy import YAML_DEVICES
from menuai.components.homekit.accessories import HomeDriver
from menuai.components.homekit.const import BRIDGE_NAME, EVENT_HOMEKIT_CHANGED
from menuai.components.homekit.iidmanager import AccessoryIIDStorage
from menuai.core import Event, menuai

from tests.common import async_capture_events


@pytest.fixture
def iid_storage(menuai: menuai) -> Generator[AccessoryIIDStorage]:
    """Mock the iid storage."""
    with patch.object(AccessoryIIDStorage, "_async_schedule_save"):
        yield AccessoryIIDStorage(menuai, "")


@pytest.fixture
def run_driver(
    menuai: menuai, iid_storage: AccessoryIIDStorage
) -> Generator[HomeDriver]:
    """Return a custom AccessoryDriver instance for HomeKit accessory init.

    This mock does not mock async_stop, so the driver will not be stopped
    """
    event_loop = asyncio.get_event_loop()
    with (
        patch("pyhap.accessory_driver.AsyncZeroconf"),
        patch("pyhap.accessory_driver.AccessoryEncoder"),
        patch("pyhap.accessory_driver.HAPServer"),
        patch("pyhap.accessory_driver.AccessoryDriver.publish"),
        patch(
            "pyhap.accessory_driver.AccessoryDriver.persist",
        ),
    ):
        yield HomeDriver(
            menuai,
            pincode=b"123-45-678",
            entry_id="",
            entry_title="mock entry",
            bridge_name=BRIDGE_NAME,
            iid_storage=iid_storage,
            address="127.0.0.1",
            loop=event_loop,
        )


@pytest.fixture
def hk_driver(
    menuai: menuai, iid_storage: AccessoryIIDStorage
) -> Generator[HomeDriver]:
    """Return a custom AccessoryDriver instance for HomeKit accessory init."""
    event_loop = asyncio.get_event_loop()
    with (
        patch("pyhap.accessory_driver.AsyncZeroconf"),
        patch("pyhap.accessory_driver.AccessoryEncoder"),
        patch("pyhap.accessory_driver.HAPServer.async_stop"),
        patch("pyhap.accessory_driver.HAPServer.async_start"),
        patch(
            "pyhap.accessory_driver.AccessoryDriver.publish",
        ),
        patch(
            "pyhap.accessory_driver.AccessoryDriver.persist",
        ),
    ):
        yield HomeDriver(
            menuai,
            pincode=b"123-45-678",
            entry_id="",
            entry_title="mock entry",
            bridge_name=BRIDGE_NAME,
            iid_storage=iid_storage,
            address="127.0.0.1",
            loop=event_loop,
        )


@pytest.fixture
def mock_hap(
    menuai: menuai,
    iid_storage: AccessoryIIDStorage,
    mock_zeroconf: MagicMock,
) -> Generator[HomeDriver]:
    """Return a custom AccessoryDriver instance for HomeKit accessory init."""
    event_loop = asyncio.get_event_loop()
    with (
        patch("pyhap.accessory_driver.AsyncZeroconf"),
        patch("pyhap.accessory_driver.AccessoryEncoder"),
        patch("pyhap.accessory_driver.HAPServer.async_stop"),
        patch("pyhap.accessory_driver.HAPServer.async_start"),
        patch(
            "pyhap.accessory_driver.AccessoryDriver.publish",
        ),
        patch(
            "pyhap.accessory_driver.AccessoryDriver.async_start",
        ),
        patch(
            "pyhap.accessory_driver.AccessoryDriver.async_stop",
        ),
        patch(
            "pyhap.accessory_driver.AccessoryDriver.persist",
        ),
    ):
        yield HomeDriver(
            menuai,
            pincode=b"123-45-678",
            entry_id="",
            entry_title="mock entry",
            bridge_name=BRIDGE_NAME,
            iid_storage=iid_storage,
            address="127.0.0.1",
            loop=event_loop,
        )


@pytest.fixture
def events(menuai: menuai) -> list[Event]:
    """Yield caught homekit_changed events."""
    return async_capture_events(menuai, EVENT_HOMEKIT_CHANGED)


@pytest.fixture
def demo_cleanup(menuai: menuai) -> Generator[None]:
    """Clean up device tracker demo file."""
    yield
    with suppress(FileNotFoundError):
        os.remove(menuai.config.path(YAML_DEVICES))
