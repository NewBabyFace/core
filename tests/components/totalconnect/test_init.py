"""Tests for the TotalConnect init process."""

from unittest.mock import patch

from total_connect_client.exceptions import AuthenticationError

from menuai.components.totalconnect.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.setup import async_setup_component

from .common import CONFIG_DATA

from tests.common import MockConfigEntry


async def test_reauth_started(menuai: menuai) -> None:
    """Test that reauth is started when we have login errors."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        data=CONFIG_DATA,
    )
    mock_entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.totalconnect.TotalConnectClient",
    ) as mock_client:
        mock_client.side_effect = AuthenticationError()
        assert await async_setup_component(menuai, DOMAIN, {})
        await menuai.async_block_till_done()

    assert mock_entry.state is ConfigEntryState.SETUP_ERROR
