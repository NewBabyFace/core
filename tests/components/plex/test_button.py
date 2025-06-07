"""Tests for Plex buttons."""

from datetime import timedelta
from unittest.mock import patch

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.components.plex.const import DEBOUNCE_TIMEOUT
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai
from menuai.util import dt as dt_util

from tests.common import async_fire_time_changed


async def test_scan_clients_button_schedule(
    menuai: menuai, setup_plex_server
) -> None:
    """Test scan_clients button scheduled update."""
    with patch(
        "menuai.components.plex.server.PlexServer._async_update_platforms"
    ) as mock_scan_clients:
        await setup_plex_server()
        mock_scan_clients.reset_mock()

        async_fire_time_changed(
            menuai,
            dt_util.utcnow() + timedelta(seconds=DEBOUNCE_TIMEOUT),
        )

        await menuai.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {
                ATTR_ENTITY_ID: "button.plex_server_1_scan_clients",
            },
            True,
        )
        await menuai.async_block_till_done()

    assert mock_scan_clients.called
