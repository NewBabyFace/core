"""Test the Netatmo diagnostics."""

from functools import partial
from unittest.mock import AsyncMock, patch

from syrupy.assertion import SnapshotAssertion
from syrupy.filters import paths

from menuai.core import menuai
from menuai.setup import async_setup_component

from .common import fake_post_request

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_entry_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
    config_entry: MockConfigEntry,
) -> None:
    """Test config entry diagnostics."""
    with (
        patch(
            "menuai.components.netatmo.api.AsyncConfigEntryNetatmoAuth",
        ) as mock_auth,
        patch(
            "menuai.helpers.config_entry_oauth2_flow.async_get_config_entry_implementation",
        ),
        patch(
            "menuai.components.netatmo.webhook_generate_url",
        ),
    ):
        mock_auth.return_value.async_post_api_request.side_effect = partial(
            fake_post_request, menuai
        )
        mock_auth.return_value.async_addwebhook.side_effect = AsyncMock()
        mock_auth.return_value.async_dropwebhook.side_effect = AsyncMock()
        assert await async_setup_component(menuai, "netatmo", {})

    await menuai.async_block_till_done()

    assert await get_diagnostics_for_config_entry(
        menuai, menuai_client, config_entry
    ) == snapshot(
        exclude=paths(
            "info.data.token.expires_at",
            "info.entry_id",
            "info.created_at",
            "info.modified_at",
        )
    )
