"""Test the Raspberry Pi integration."""

from unittest.mock import patch

import pytest

from menuai.components.menuaiio import DOMAIN as menuaiIO_DOMAIN
from menuai.components.raspberry_pi.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry, MockModule, mock_integration


@pytest.fixture(autouse=True)
def mock_rpi_power():
    """Mock the rpi_power integration."""
    with patch(
        "menuai.components.rpi_power.async_setup_entry",
        return_value=True,
    ):
        yield


async def test_setup_entry(menuai: menuai) -> None:
    """Test setup of a config entry."""
    mock_integration(menuai, MockModule("menuaiio"))
    await async_setup_component(menuai, menuaiIO_DOMAIN, {})

    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={},
        title="Raspberry Pi",
    )
    config_entry.add_to_menuai(menuai)
    assert not menuai.config_entries.async_entries("rpi_power")
    with (
        patch(
            "menuai.components.raspberry_pi.get_os_info",
            return_value={"board": "rpi"},
        ) as mock_get_os_info,
        patch("menuai.components.rpi_power.config_flow.new_under_voltage"),
    ):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
        assert len(mock_get_os_info.mock_calls) == 1

    assert len(menuai.config_entries.async_entries("rpi_power")) == 1


async def test_setup_entry_no_menuaiio(menuai: menuai) -> None:
    """Test setup of a config entry without menuaiio."""
    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={},
        title="Raspberry Pi",
    )
    config_entry.add_to_menuai(menuai)
    assert len(menuai.config_entries.async_entries()) == 1

    with patch("menuai.components.raspberry_pi.get_os_info") as mock_get_os_info:
        assert not await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert len(mock_get_os_info.mock_calls) == 0
    assert len(menuai.config_entries.async_entries()) == 0


async def test_setup_entry_wrong_board(menuai: menuai) -> None:
    """Test setup of a config entry with wrong board type."""
    mock_integration(menuai, MockModule("menuaiio"))
    await async_setup_component(menuai, menuaiIO_DOMAIN, {})

    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={},
        title="Raspberry Pi",
    )
    config_entry.add_to_menuai(menuai)
    assert len(menuai.config_entries.async_entries()) == 1

    with patch(
        "menuai.components.raspberry_pi.get_os_info",
        return_value={"board": "generic-x86-64"},
    ) as mock_get_os_info:
        assert not await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert len(mock_get_os_info.mock_calls) == 1
    assert len(menuai.config_entries.async_entries()) == 0


async def test_setup_entry_wait_menuaiio(menuai: menuai) -> None:
    """Test setup of a config entry when menuaiio has not fetched os_info."""
    mock_integration(menuai, MockModule("menuaiio"))
    await async_setup_component(menuai, menuaiIO_DOMAIN, {})

    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={},
        title="Raspberry Pi",
    )
    config_entry.add_to_menuai(menuai)
    with patch(
        "menuai.components.raspberry_pi.get_os_info",
        return_value=None,
    ) as mock_get_os_info:
        assert not await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert len(mock_get_os_info.mock_calls) == 1
    assert config_entry.state is ConfigEntryState.SETUP_RETRY
