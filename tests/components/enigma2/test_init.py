"""Test the Enigma2 integration init."""

from unittest.mock import AsyncMock

import pytest

from menuai.components.enigma2.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from .conftest import TEST_REQUIRED

from tests.common import MockConfigEntry, async_load_json_object_fixture


async def test_device_without_mac_address(
    menuai: menuai,
    openwebif_device_mock: AsyncMock,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test that a device gets successfully registered when the device doesn't report a MAC address."""
    openwebif_device_mock.get_about.return_value = await async_load_json_object_fixture(
        menuai, "device_about_without_mac.json", DOMAIN
    )
    entry = MockConfigEntry(
        domain=DOMAIN, data=TEST_REQUIRED, title="name", unique_id="123456"
    )
    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.unique_id == "123456"
    assert device_registry.async_get_device({(DOMAIN, entry.unique_id)}) is not None


@pytest.mark.usefixtures("openwebif_device_mock")
async def test_unload_entry(menuai: menuai) -> None:
    """Test successful unload of entry."""
    entry = MockConfigEntry(domain=DOMAIN, data=TEST_REQUIRED, title="name")
    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert not menuai.data.get(DOMAIN)
