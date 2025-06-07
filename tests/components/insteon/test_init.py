"""Test the init file for the Insteon component."""

from unittest.mock import patch

import pytest

from menuai.components import insteon
from menuai.components.insteon.const import CONF_DEV_PATH, DOMAIN
from menuai.const import EVENT_menuai_STOP
from menuai.core import menuai
from menuai.setup import async_setup_component

from .const import MOCK_USER_INPUT_PLM
from .mock_devices import MockDevices

from tests.common import MockConfigEntry


async def mock_successful_connection(*args, **kwargs):
    """Return a successful connection."""
    return True


async def mock_failed_connection(*args, **kwargs):
    """Return a failed connection."""
    raise ConnectionError("Connection failed")


async def test_setup_entry(menuai: menuai) -> None:
    """Test setting up the entry."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_INPUT_PLM)
    config_entry.add_to_menuai(menuai)

    with (
        patch.object(insteon, "async_connect", new=mock_successful_connection),
        patch.object(insteon, "async_close") as mock_close,
        patch.object(insteon, "devices", new=MockDevices()),
    ):
        assert await async_setup_component(
            menuai,
            insteon.DOMAIN,
            {},
        )
        await menuai.async_block_till_done()
        menuai.bus.async_fire(EVENT_menuai_STOP)
        await menuai.async_block_till_done()
        assert insteon.devices.async_save.call_count == 1
        assert mock_close.called


async def test_setup_entry_failed_connection(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test setting up the entry with a failed connection."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_INPUT_PLM)
    config_entry.add_to_menuai(menuai)

    with (
        patch.object(insteon, "async_connect", new=mock_failed_connection),
        patch.object(insteon, "devices", new=MockDevices(connected=False)),
    ):
        assert await async_setup_component(
            menuai,
            insteon.DOMAIN,
            {},
        )
        assert "Could not connect to Insteon modem" in caplog.text


async def test_import_frontend_dev_url(menuai: menuai) -> None:
    """Test importing a dev_url config entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_USER_INPUT_PLM, options={CONF_DEV_PATH: "/some/path"}
    )
    config_entry.add_to_menuai(menuai)

    with (
        patch.object(insteon, "async_connect", new=mock_successful_connection),
        patch.object(insteon, "async_close") as mock_close,
        patch.object(insteon, "devices", new=MockDevices()),
    ):
        assert await async_setup_component(
            menuai,
            insteon.DOMAIN,
            {},
        )
        await menuai.async_block_till_done()
        assert menuai.data[DOMAIN][CONF_DEV_PATH] == "/some/path"
        menuai.bus.async_fire(EVENT_menuai_STOP)
        await menuai.async_block_till_done()
        assert insteon.devices.async_save.call_count == 1
        assert mock_close.called
