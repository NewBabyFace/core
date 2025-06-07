"""Test the Coinbase diagnostics."""

from unittest.mock import patch

from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.core import menuai

from .common import (
    init_mock_coinbase,
    mock_get_current_user,
    mock_get_exchange_rates,
    mocked_get_accounts,
)

from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_entry_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test we handle a and redact a diagnostics request."""

    with (
        patch(
            "coinbase.wallet.client.Client.get_current_user",
            return_value=mock_get_current_user(),
        ),
        patch("coinbase.wallet.client.Client.get_accounts", new=mocked_get_accounts),
        patch(
            "coinbase.wallet.client.Client.get_exchange_rates",
            return_value=mock_get_exchange_rates(),
        ),
    ):
        config_entry = await init_mock_coinbase(menuai)
        await menuai.async_block_till_done()

        result = await get_diagnostics_for_config_entry(menuai, menuai_client, config_entry)

        assert result == snapshot(exclude=props("created_at", "modified_at"))
