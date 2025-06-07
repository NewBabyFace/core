"""Tests for the Habitica switch platform."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

from aiohttp import ClientError
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from menuai.config_entries import ConfigEntryState
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from .conftest import ERROR_BAD_REQUEST, ERROR_TOO_MANY_REQUESTS

from tests.common import MockConfigEntry, snapshot_platform


@pytest.fixture(autouse=True)
def switch_only() -> Generator[None]:
    """Enable only the switch platform."""
    with patch(
        "menuai.components.habitica.PLATFORMS",
        [Platform.SWITCH],
    ):
        yield


@pytest.mark.usefixtures("habitica")
async def test_switch(
    menuai: menuai,
    config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test switch entities."""

    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    await snapshot_platform(menuai, entity_registry, snapshot, config_entry.entry_id)


@pytest.mark.parametrize(
    ("service_call"),
    [
        SERVICE_TURN_ON,
        SERVICE_TURN_OFF,
        SERVICE_TOGGLE,
    ],
)
async def test_turn_on_off_toggle(
    menuai: menuai,
    config_entry: MockConfigEntry,
    service_call: str,
    habitica: AsyncMock,
) -> None:
    """Test switch turn on/off, toggle method."""

    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        service_call,
        {ATTR_ENTITY_ID: "switch.test_user_rest_in_the_inn"},
        blocking=True,
    )

    habitica.toggle_sleep.assert_awaited_once()


@pytest.mark.parametrize(
    ("service_call"),
    [
        SERVICE_TURN_ON,
        SERVICE_TURN_OFF,
        SERVICE_TOGGLE,
    ],
)
@pytest.mark.parametrize(
    ("raise_exception", "expected_exception"),
    [
        (ERROR_TOO_MANY_REQUESTS, menuaiError),
        (ERROR_BAD_REQUEST, menuaiError),
        (ClientError, menuaiError),
    ],
)
async def test_turn_on_off_toggle_exceptions(
    menuai: menuai,
    config_entry: MockConfigEntry,
    service_call: str,
    habitica: AsyncMock,
    raise_exception: Exception,
    expected_exception: Exception,
) -> None:
    """Test switch turn on/off, toggle method."""

    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    habitica.toggle_sleep.side_effect = raise_exception

    with pytest.raises(expected_exception=expected_exception):
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            service_call,
            {ATTR_ENTITY_ID: "switch.test_user_rest_in_the_inn"},
            blocking=True,
        )
