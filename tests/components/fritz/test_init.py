"""Tests for Fritz!Tools."""

from unittest.mock import patch

import pytest

from menuai.components.device_tracker import (
    CONF_CONSIDER_HOME,
    DEFAULT_CONSIDER_HOME,
)
from menuai.components.fritz.const import (
    DOMAIN,
    FRITZ_AUTH_EXCEPTIONS,
    FRITZ_EXCEPTIONS,
)
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from .const import MOCK_USER_DATA

from tests.common import MockConfigEntry


async def test_setup(menuai: menuai, fc_class_mock, fh_class_mock) -> None:
    """Test setup and unload of Fritz!Tools."""

    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_DATA)
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_options_reload(
    menuai: menuai, fc_class_mock, fh_class_mock
) -> None:
    """Test reload of Fritz!Tools, when options changed."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_USER_DATA,
        options={CONF_CONSIDER_HOME: DEFAULT_CONSIDER_HOME.total_seconds()},
    )
    entry.add_to_menuai(menuai)

    with patch(
        "menuai.config_entries.ConfigEntries.async_reload",
        return_value=None,
    ) as mock_reload:
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED

        result = await menuai.config_entries.options.async_init(entry.entry_id)
        await menuai.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONF_CONSIDER_HOME: 60},
        )
        await menuai.async_block_till_done()
        mock_reload.assert_called_once()


@pytest.mark.parametrize(
    "error",
    FRITZ_AUTH_EXCEPTIONS,
)
async def test_setup_auth_fail(menuai: menuai, error) -> None:
    """Test starting a flow by user with an already configured device."""

    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_DATA)
    entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.fritz.coordinator.FritzConnection",
        side_effect=error,
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR


@pytest.mark.parametrize(
    "error",
    FRITZ_EXCEPTIONS,
)
async def test_setup_fail(menuai: menuai, error) -> None:
    """Test starting a flow by user with an already configured device."""

    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_DATA)
    entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.fritz.coordinator.FritzConnection",
        side_effect=error,
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY
