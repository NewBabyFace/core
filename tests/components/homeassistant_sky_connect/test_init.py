"""Test the MenuAI SkyConnect integration."""

from datetime import timedelta
from unittest.mock import patch

import pytest

from menuai.components.menuai_hardware.util import (
    ApplicationType,
    FirmwareInfo,
)
from menuai.components.menuai_sky_connect.const import (
    DESCRIPTION,
    DOMAIN,
    MANUFACTURER,
    PID,
    PRODUCT,
    SERIAL_NUMBER,
    VID,
)
from menuai.components.usb import USBDevice
from menuai.config_entries import ConfigEntryState
from menuai.const import EVENT_menuai_STARTED
from menuai.core import menuai
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import MockConfigEntry, async_fire_time_changed
from tests.components.usb import (
    async_request_scan,
    force_usb_polling_watcher,  # noqa: F401
    patch_scanned_serial_ports,
)


async def test_config_entry_migration_v2(menuai: menuai) -> None:
    """Test migrating config entries from v1 to v2 format."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="some_unique_id",
        data={
            "device": "/dev/serial/by-id/usb-Nabu_Casa_SkyConnect_v1.0_9e2adbd75b8beb119fe564a0f320645d-if00-port0",
            "vid": "10C4",
            "pid": "EA60",
            "serial_number": "3c0ed67c628beb11b1cd64a0f320645d",
            "manufacturer": "Nabu Casa",
            "description": "SkyConnect v1.0",
        },
        version=1,
    )

    config_entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.menuai_sky_connect.guess_firmware_info",
        return_value=FirmwareInfo(
            device="/dev/serial/by-id/usb-Nabu_Casa_SkyConnect_v1.0_9e2adbd75b8beb119fe564a0f320645d-if00-port0",
            firmware_version=None,
            firmware_type=ApplicationType.SPINEL,
            source="otbr",
            owners=[],
        ),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)

    assert config_entry.version == 1
    assert config_entry.minor_version == 4
    assert config_entry.data == {
        "description": "SkyConnect v1.0",
        "device": "/dev/serial/by-id/usb-Nabu_Casa_SkyConnect_v1.0_9e2adbd75b8beb119fe564a0f320645d-if00-port0",
        "vid": "10C4",
        "pid": "EA60",
        "serial_number": "3c0ed67c628beb11b1cd64a0f320645d",
        "manufacturer": "Nabu Casa",
        "product": "SkyConnect v1.0",  # `description` has been copied to `product`
        "firmware": "spinel",  # new key
        "firmware_version": None,  # new key
    }

    await menuai.config_entries.async_unload(config_entry.entry_id)


async def test_setup_fails_on_missing_usb_port(menuai: menuai) -> None:
    """Test setup failing when the USB port is missing."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="some_unique_id",
        data={
            "description": "SkyConnect v1.0",
            "device": "/dev/serial/by-id/usb-Nabu_Casa_SkyConnect_v1.0_9e2adbd75b8beb119fe564a0f320645d-if00-port0",
            "vid": "10C4",
            "pid": "EA60",
            "serial_number": "3c0ed67c628beb11b1cd64a0f320645d",
            "manufacturer": "Nabu Casa",
            "product": "SkyConnect v1.0",
            "firmware": "ezsp",
            "firmware_version": "7.4.4.0",
        },
        version=1,
        minor_version=3,
    )

    config_entry.add_to_menuai(menuai)

    # Set up the config entry
    with patch(
        "menuai.components.menuai_sky_connect.os.path.exists"
    ) as mock_exists:
        mock_exists.return_value = False
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

        # Failed to set up, the device is missing
        assert config_entry.state is ConfigEntryState.SETUP_RETRY

        mock_exists.return_value = True
        async_fire_time_changed(menuai, dt_util.now() + timedelta(seconds=30))
        await menuai.async_block_till_done(wait_background_tasks=True)

        # Now it's ready
        assert config_entry.state is ConfigEntryState.LOADED


@pytest.mark.usefixtures("force_usb_polling_watcher")
async def test_usb_device_reactivity(menuai: menuai) -> None:
    """Test setting up USB monitoring."""
    assert await async_setup_component(menuai, "usb", {"usb": {}})

    await menuai.async_block_till_done()
    menuai.bus.async_fire(EVENT_menuai_STARTED)
    await menuai.async_block_till_done()

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="some_unique_id",
        data={
            "description": "SkyConnect v1.0",
            "device": "/dev/serial/by-id/usb-Nabu_Casa_SkyConnect_v1.0_9e2adbd75b8beb119fe564a0f320645d-if00-port0",
            "vid": "10C4",
            "pid": "EA60",
            "serial_number": "3c0ed67c628beb11b1cd64a0f320645d",
            "manufacturer": "Nabu Casa",
            "product": "SkyConnect v1.0",
            "firmware": "ezsp",
            "firmware_version": "7.4.4.0",
        },
        version=1,
        minor_version=3,
    )

    config_entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.menuai_sky_connect.os.path.exists"
    ) as mock_exists:
        mock_exists.return_value = False
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

        # Failed to set up, the device is missing
        assert config_entry.state is ConfigEntryState.SETUP_RETRY

        # Now we make it available but do not wait
        mock_exists.return_value = True

        with patch_scanned_serial_ports(
            return_value=[
                USBDevice(
                    device="/dev/serial/by-id/usb-Nabu_Casa_SkyConnect_v1.0_9e2adbd75b8beb119fe564a0f320645d-if00-port0",
                    vid="10C4",
                    pid="EA60",
                    serial_number="3c0ed67c628beb11b1cd64a0f320645d",
                    manufacturer="Nabu Casa",
                    description="SkyConnect v1.0",
                )
            ],
        ):
            await async_request_scan(menuai)

        # It loads immediately
        await menuai.async_block_till_done(wait_background_tasks=True)
        assert config_entry.state is ConfigEntryState.LOADED

        # Wait for a bit for the USB scan debouncer to cool off
        async_fire_time_changed(menuai, dt_util.now() + timedelta(minutes=5))

        # Unplug the stick
        mock_exists.return_value = False

        with patch_scanned_serial_ports(return_value=[]):
            await async_request_scan(menuai)

        # The integration has reloaded and is now in a failed state
        await menuai.async_block_till_done(wait_background_tasks=True)
        assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_bad_config_entry_fixing(menuai: menuai) -> None:
    """Test fixing/deleting config entries with bad data."""

    # Newly-added ZBT-1
    new_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="some_unique_id-9e2adbd75b8beb119fe564a0f320645d",
        data={
            "device": "/dev/serial/by-id/usb-Nabu_Casa_SkyConnect_v1.0_9e2adbd75b8beb119fe564a0f320645d-if00-port0",
            "vid": "10C4",
            "pid": "EA60",
            "serial_number": "9e2adbd75b8beb119fe564a0f320645d",
            "manufacturer": "Nabu Casa",
            "product": "SkyConnect v1.0",
            "firmware": "ezsp",
            "firmware_version": "7.4.4.0 (build 123)",
        },
        version=1,
        minor_version=3,
    )

    new_entry.add_to_menuai(menuai)

    # Old config entry, without firmware info
    old_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="some_unique_id-3c0ed67c628beb11b1cd64a0f320645d",
        data={
            "device": "/dev/serial/by-id/usb-Nabu_Casa_SkyConnect_v1.0_3c0ed67c628beb11b1cd64a0f320645d-if00-port0",
            "vid": "10C4",
            "pid": "EA60",
            "serial_number": "3c0ed67c628beb11b1cd64a0f320645d",
            "manufacturer": "Nabu Casa",
            "description": "SkyConnect v1.0",
        },
        version=1,
        minor_version=1,
    )

    old_entry.add_to_menuai(menuai)

    # Bad config entry, missing most keys
    bad_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="some_unique_id-9f6c4bba657cc9a4f0cea48bc5948562",
        data={
            "device": "/dev/serial/by-id/usb-Nabu_Casa_SkyConnect_v1.0_9f6c4bba657cc9a4f0cea48bc5948562-if00-port0",
        },
        version=1,
        minor_version=2,
    )

    bad_entry.add_to_menuai(menuai)

    # Bad config entry, missing most keys, but fixable since the device is present
    fixable_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="some_unique_id-4f5f3b26d59f8714a78b599690741999",
        data={
            "device": "/dev/serial/by-id/usb-Nabu_Casa_SkyConnect_v1.0_4f5f3b26d59f8714a78b599690741999-if00-port0",
        },
        version=1,
        minor_version=2,
    )

    fixable_entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.menuai_sky_connect.scan_serial_ports",
        return_value=[
            USBDevice(
                device="/dev/serial/by-id/usb-Nabu_Casa_SkyConnect_v1.0_4f5f3b26d59f8714a78b599690741999-if00-port0",
                vid="10C4",
                pid="EA60",
                serial_number="4f5f3b26d59f8714a78b599690741999",
                manufacturer="Nabu Casa",
                description="SkyConnect v1.0",
            )
        ],
    ):
        await async_setup_component(menuai, "menuai_sky_connect", {})

    assert menuai.config_entries.async_get_entry(new_entry.entry_id) is not None
    assert menuai.config_entries.async_get_entry(old_entry.entry_id) is not None
    assert menuai.config_entries.async_get_entry(fixable_entry.entry_id) is not None

    updated_entry = menuai.config_entries.async_get_entry(fixable_entry.entry_id)
    assert updated_entry is not None
    assert updated_entry.data[VID] == "10C4"
    assert updated_entry.data[PID] == "EA60"
    assert updated_entry.data[SERIAL_NUMBER] == "4f5f3b26d59f8714a78b599690741999"
    assert updated_entry.data[MANUFACTURER] == "Nabu Casa"
    assert updated_entry.data[PRODUCT] == "SkyConnect v1.0"
    assert updated_entry.data[DESCRIPTION] == "SkyConnect v1.0"

    untouched_bad_entry = menuai.config_entries.async_get_entry(bad_entry.entry_id)
    assert untouched_bad_entry.minor_version == 3
