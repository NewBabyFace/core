"""Tests for the AVM Fritz!Box integration."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import Mock

from pyfritzhome import LoginError
from requests.exceptions import ConnectionError, HTTPError

from menuai.components.fritzbox.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_DEVICES
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.util.dt import utcnow

from . import FritzDeviceCoverMock, FritzDeviceSwitchMock, FritzEntityBaseMock
from .const import MOCK_CONFIG

from tests.common import MockConfigEntry, async_fire_time_changed


async def test_coordinator_update_after_reboot(
    menuai: menuai, fritz: Mock
) -> None:
    """Test coordinator after reboot."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG[DOMAIN][CONF_DEVICES][0],
        unique_id="any",
    )
    entry.add_to_menuai(menuai)
    fritz().update_devices.side_effect = [HTTPError(), ""]

    assert await menuai.config_entries.async_setup(entry.entry_id)
    assert fritz().update_devices.call_count == 2
    assert fritz().update_templates.call_count == 1
    assert fritz().get_devices.call_count == 1
    assert fritz().get_templates.call_count == 1
    assert fritz().login.call_count == 2


async def test_coordinator_update_after_password_change(
    menuai: menuai, fritz: Mock
) -> None:
    """Test coordinator after password change."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG[DOMAIN][CONF_DEVICES][0],
        unique_id="any",
    )
    entry.add_to_menuai(menuai)
    fritz().update_devices.side_effect = HTTPError()
    fritz().login.side_effect = ["", LoginError("some_user")]

    assert not await menuai.config_entries.async_setup(entry.entry_id)
    assert fritz().update_devices.call_count == 1
    assert fritz().get_devices.call_count == 0
    assert fritz().get_templates.call_count == 0
    assert fritz().login.call_count == 2


async def test_coordinator_update_when_unreachable(
    menuai: menuai, fritz: Mock
) -> None:
    """Test coordinator after reboot."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG[DOMAIN][CONF_DEVICES][0],
        unique_id="any",
    )
    entry.add_to_menuai(menuai)
    fritz().update_devices.side_effect = [ConnectionError(), ""]

    assert not await menuai.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_coordinator_automatic_registry_cleanup(
    menuai: menuai,
    fritz: Mock,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test automatic registry cleanup."""

    # init with 2 devices and 1 template
    fritz().get_devices.return_value = [
        FritzDeviceSwitchMock(
            ain="fake ain switch",
            device_and_unit_id=("fake ain switch", None),
            name="fake_switch",
        ),
        FritzDeviceCoverMock(
            ain="fake ain cover",
            device_and_unit_id=("fake ain cover", None),
            name="fake_cover",
        ),
    ]
    fritz().get_templates.return_value = [
        FritzEntityBaseMock(
            ain="fake ain template",
            device_and_unit_id=("fake ain template", None),
            name="fake_template",
        )
    ]
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG[DOMAIN][CONF_DEVICES][0],
        unique_id="any",
    )
    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert len(er.async_entries_for_config_entry(entity_registry, entry.entry_id)) == 20
    assert len(dr.async_entries_for_config_entry(device_registry, entry.entry_id)) == 3

    # remove one device, keep the template
    fritz().get_devices.return_value = [
        FritzDeviceSwitchMock(
            ain="fake ain switch",
            device_and_unit_id=("fake ain switch", None),
            name="fake_switch",
        )
    ]

    async_fire_time_changed(menuai, utcnow() + timedelta(seconds=35))
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert len(er.async_entries_for_config_entry(entity_registry, entry.entry_id)) == 13
    assert len(dr.async_entries_for_config_entry(device_registry, entry.entry_id)) == 2

    # remove the template, keep the device
    fritz().get_templates.return_value = []

    async_fire_time_changed(menuai, utcnow() + timedelta(seconds=35))
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert len(er.async_entries_for_config_entry(entity_registry, entry.entry_id)) == 12
    assert len(dr.async_entries_for_config_entry(device_registry, entry.entry_id)) == 1
