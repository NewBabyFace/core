"""Tests for the Lutron Caseta integration."""

from unittest.mock import patch

import pytest

from menuai.components import lutron_caseta
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import MockBridge, async_setup_integration, make_mock_entry


@pytest.mark.parametrize(
    ("constant", "message", "timeout_during_connect", "timeout_during_configure"),
    [
        ("CONNECT_TIMEOUT", "Timed out on connect", True, False),
        ("CONFIGURE_TIMEOUT", "Timed out on configure", False, True),
    ],
)
async def test_timeout_during_setup(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    constant: str,
    message: str,
    timeout_during_connect: bool,
    timeout_during_configure: bool,
) -> None:
    """Test a timeout during setup."""
    mock_entry = make_mock_entry()
    mock_entry.add_to_menuai(menuai)
    with patch.object(lutron_caseta, constant, 0.001):
        await async_setup_integration(
            menuai,
            MockBridge,
            config_entry_id=mock_entry.entry_id,
            timeout_during_connect=timeout_during_connect,
            timeout_during_configure=timeout_during_configure,
        )
    assert mock_entry.state is ConfigEntryState.SETUP_RETRY
    assert f"{message} for 1.1.1.1" in caplog.text


async def test_cannot_connect(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test failing to connect."""
    mock_entry = make_mock_entry()
    mock_entry.add_to_menuai(menuai)
    await async_setup_integration(
        menuai, MockBridge, config_entry_id=mock_entry.entry_id, can_connect=False
    )
    assert mock_entry.state is ConfigEntryState.SETUP_RETRY
    assert "Connection failed to 1.1.1.1" in caplog.text
