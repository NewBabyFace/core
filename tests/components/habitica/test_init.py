"""Test the habitica module."""

import datetime
import logging
from unittest.mock import AsyncMock

from aiohttp import ClientError
from freezegun.api import FrozenDateTimeFactory
import pytest

from menuai.components.habitica.const import DOMAIN
from menuai.config_entries import SOURCE_REAUTH, ConfigEntryState
from menuai.core import menuai

from .conftest import (
    ERROR_BAD_REQUEST,
    ERROR_NOT_AUTHORIZED,
    ERROR_NOT_FOUND,
    ERROR_TOO_MANY_REQUESTS,
)

from tests.common import MockConfigEntry, async_fire_time_changed


@pytest.mark.usefixtures("habitica")
async def test_entry_setup_unload(
    menuai: menuai, config_entry: MockConfigEntry
) -> None:
    """Test integration setup and unload."""

    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(config_entry.entry_id)

    assert config_entry.state is ConfigEntryState.NOT_LOADED


@pytest.mark.parametrize(
    ("exception"),
    [ERROR_BAD_REQUEST, ERROR_TOO_MANY_REQUESTS, ClientError],
    ids=[
        "BadRequestError",
        "TooManyRequestsError",
        "ClientError",
    ],
)
async def test_config_entry_not_ready(
    menuai: menuai,
    config_entry: MockConfigEntry,
    habitica: AsyncMock,
    exception: Exception,
) -> None:
    """Test config entry not ready."""

    habitica.get_user.side_effect = exception
    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_config_entry_auth_failed(
    menuai: menuai, config_entry: MockConfigEntry, habitica: AsyncMock
) -> None:
    """Test config entry auth failed setup error."""

    habitica.get_user.side_effect = ERROR_NOT_AUTHORIZED
    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1

    flow = flows[0]
    assert flow.get("step_id") == "reauth_confirm"
    assert flow.get("handler") == DOMAIN

    assert "context" in flow
    assert flow["context"].get("source") == SOURCE_REAUTH
    assert flow["context"].get("entry_id") == config_entry.entry_id


@pytest.mark.parametrize("exception", [ERROR_NOT_FOUND, ClientError])
async def test_coordinator_update_failed(
    menuai: menuai,
    config_entry: MockConfigEntry,
    habitica: AsyncMock,
    exception: Exception,
) -> None:
    """Test coordinator update failed."""

    habitica.get_tasks.side_effect = exception
    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_coordinator_rate_limited(
    menuai: menuai,
    config_entry: MockConfigEntry,
    habitica: AsyncMock,
    caplog: pytest.LogCaptureFixture,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test coordinator when rate limited."""

    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    habitica.get_user.side_effect = ERROR_TOO_MANY_REQUESTS

    with caplog.at_level(logging.DEBUG):
        freezer.tick(datetime.timedelta(seconds=60))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()

        assert "Rate limit exceeded, will try again later" in caplog.text
