"""Test the switchbot init."""

from collections.abc import Callable
from unittest.mock import AsyncMock, patch

import pytest

from menuai.core import menuai

from . import (
    HUBMINI_MATTER_SERVICE_INFO,
    LOCK_SERVICE_INFO,
    patch_async_ble_device_from_address,
)

from tests.common import MockConfigEntry
from tests.components.bluetooth import inject_bluetooth_service_info


@pytest.mark.parametrize(
    ("exception", "error_message"),
    [
        (
            ValueError("wrong model"),
            "Switchbot device initialization failed because of incorrect configuration parameters: wrong model",
        ),
    ],
)
async def test_exception_handling_for_device_initialization(
    menuai: menuai,
    mock_entry_encrypted_factory: Callable[[str], MockConfigEntry],
    exception: Exception,
    error_message: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test exception handling for lock initialization."""
    inject_bluetooth_service_info(menuai, LOCK_SERVICE_INFO)

    entry = mock_entry_encrypted_factory(sensor_type="lock")
    entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.switchbot.lock.switchbot.SwitchbotLock.__init__",
        side_effect=exception,
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()
    assert error_message in caplog.text


async def test_setup_entry_without_ble_device(
    menuai: menuai,
    mock_entry_factory: Callable[[str], MockConfigEntry],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test setup entry without ble device."""

    entry = mock_entry_factory("hygrometer_co2")
    entry.add_to_menuai(menuai)

    with patch_async_ble_device_from_address(None):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    assert (
        "Could not find Switchbot hygrometer_co2 with address aa:bb:cc:dd:ee:ff"
        in caplog.text
    )


async def test_coordinator_wait_ready_timeout(
    menuai: menuai,
    mock_entry_factory: Callable[[str], MockConfigEntry],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the coordinator async_wait_ready timeout by calling it directly."""

    inject_bluetooth_service_info(menuai, HUBMINI_MATTER_SERVICE_INFO)

    entry = mock_entry_factory("hubmini_matter")
    entry.add_to_menuai(menuai)

    timeout_mock = AsyncMock()
    timeout_mock.__aenter__.side_effect = TimeoutError
    timeout_mock.__aexit__.return_value = None

    with patch(
        "menuai.components.switchbot.coordinator.asyncio.timeout",
        return_value=timeout_mock,
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    assert "aa:bb:cc:dd:ee:ff is not advertising state" in caplog.text
