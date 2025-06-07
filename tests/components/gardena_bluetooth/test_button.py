"""Test Gardena Bluetooth sensor."""

from collections.abc import Awaitable, Callable
from unittest.mock import Mock, call

from gardena_bluetooth.const import Reset
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai

from . import setup_entry

from tests.common import MockConfigEntry


@pytest.fixture
def mock_switch_chars(mock_read_char_raw):
    """Mock data on device."""
    mock_read_char_raw[Reset.factory_reset.uuid] = b"\x00"
    return mock_read_char_raw


async def test_setup(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_entry: MockConfigEntry,
    mock_switch_chars: dict[str, bytes],
    scan_step: Callable[[], Awaitable[None]],
) -> None:
    """Test setup creates expected entities."""

    entity_id = "button.mock_title_factory_reset"
    await setup_entry(menuai, mock_entry, [Platform.BUTTON])
    assert menuai.states.get(entity_id) == snapshot

    mock_switch_chars[Reset.factory_reset.uuid] = b"\x01"
    await scan_step()
    assert menuai.states.get(entity_id) == snapshot


async def test_switching(
    menuai: menuai,
    mock_entry: MockConfigEntry,
    mock_client: Mock,
    mock_switch_chars: dict[str, bytes],
) -> None:
    """Test switching makes correct calls."""

    entity_id = "button.mock_title_factory_reset"
    await setup_entry(menuai, mock_entry, [Platform.BUTTON])
    assert menuai.states.get(entity_id)

    await menuai.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )

    assert mock_client.write_char.mock_calls == [
        call(Reset.factory_reset, True),
    ]
