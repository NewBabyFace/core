"""Tests of the initialization of the venstar integration."""

from unittest.mock import patch

from menuai.components.venstar.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_HOST, CONF_SSL
from menuai.core import menuai

from . import VenstarColorTouchMock

from tests.common import MockConfigEntry

TEST_HOST = "venstartest.localdomain"


async def test_setup_entry(menuai: menuai) -> None:
    """Validate that setup entry also configure the client."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: TEST_HOST,
            CONF_SSL: False,
        },
    )
    config_entry.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.venstar.VenstarColorTouch._request",
            new=VenstarColorTouchMock._request,
        ),
        patch(
            "menuai.components.venstar.VenstarColorTouch.update_sensors",
            new=VenstarColorTouchMock.update_sensors,
        ),
        patch(
            "menuai.components.venstar.VenstarColorTouch.update_info",
            new=VenstarColorTouchMock.update_info,
        ),
        patch(
            "menuai.components.venstar.VenstarColorTouch.update_alerts",
            new=VenstarColorTouchMock.update_alerts,
        ),
        patch(
            "menuai.components.venstar.VenstarColorTouch.get_runtimes",
            new=VenstarColorTouchMock.get_runtimes,
        ),
        patch(
            "menuai.components.venstar.coordinator.VENSTAR_SLEEP",
            new=0,
        ),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(config_entry.entry_id)

    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_entry_exception(menuai: menuai) -> None:
    """Validate that setup entry also configure the client."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: TEST_HOST,
            CONF_SSL: False,
        },
    )
    config_entry.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.venstar.VenstarColorTouch._request",
            new=VenstarColorTouchMock._request,
        ),
        patch(
            "menuai.components.venstar.VenstarColorTouch.update_sensors",
            new=VenstarColorTouchMock.update_sensors,
        ),
        patch(
            "menuai.components.venstar.VenstarColorTouch.update_info",
            new=VenstarColorTouchMock.broken_update_info,
        ),
        patch(
            "menuai.components.venstar.VenstarColorTouch.update_alerts",
            new=VenstarColorTouchMock.update_alerts,
        ),
        patch(
            "menuai.components.venstar.VenstarColorTouch.get_runtimes",
            new=VenstarColorTouchMock.get_runtimes,
        ),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY
