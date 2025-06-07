"""Tests for the WiLight integration."""

from unittest.mock import patch

import pytest
import pywilight
from pywilight.const import DOMAIN
import requests

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import (
    HOST,
    UPNP_MAC_ADDRESS,
    UPNP_MODEL_NAME_P_B,
    UPNP_MODEL_NUMBER,
    UPNP_SERIAL,
    setup_integration,
)


@pytest.fixture(name="dummy_device_from_host")
def mock_dummy_device_from_host():
    """Mock a valid api_devce."""

    device = pywilight.wilight_from_discovery(
        f"http://{HOST}:45995/wilight.xml",
        UPNP_MAC_ADDRESS,
        UPNP_MODEL_NAME_P_B,
        UPNP_SERIAL,
        UPNP_MODEL_NUMBER,
    )

    device.set_dummy(True)

    with patch(
        "pywilight.device_from_host",
        return_value=device,
    ):
        yield device


async def test_config_entry_not_ready(menuai: menuai) -> None:
    """Test the WiLight configuration entry not ready."""
    with patch(
        "pywilight.device_from_host",
        side_effect=requests.exceptions.Timeout,
    ):
        entry = await setup_integration(menuai)

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload_config_entry(menuai: menuai, dummy_device_from_host) -> None:
    """Test the WiLight configuration entry unloading."""
    entry = await setup_integration(menuai)

    assert entry.entry_id in menuai.data[DOMAIN]
    assert entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    if DOMAIN in menuai.data:
        assert entry.entry_id not in menuai.data[DOMAIN]
        assert entry.state is ConfigEntryState.NOT_LOADED
