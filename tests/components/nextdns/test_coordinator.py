"""Tests for NextDNS coordinator."""

from datetime import timedelta
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
from nextdns import InvalidApiKeyError

from menuai.components.nextdns.const import DOMAIN
from menuai.config_entries import SOURCE_REAUTH, ConfigEntryState
from menuai.core import menuai

from . import init_integration

from tests.common import async_fire_time_changed


async def test_auth_error(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test authentication error when polling data."""
    entry = await init_integration(menuai)

    assert entry.state is ConfigEntryState.LOADED

    freezer.tick(timedelta(minutes=10))
    with (
        patch(
            "menuai.components.nextdns.NextDns.get_profiles",
            side_effect=InvalidApiKeyError,
        ),
        patch(
            "menuai.components.nextdns.NextDns.get_analytics_status",
            side_effect=InvalidApiKeyError,
        ),
        patch(
            "menuai.components.nextdns.NextDns.get_analytics_encryption",
            side_effect=InvalidApiKeyError,
        ),
        patch(
            "menuai.components.nextdns.NextDns.get_analytics_dnssec",
            side_effect=InvalidApiKeyError,
        ),
        patch(
            "menuai.components.nextdns.NextDns.get_analytics_ip_versions",
            side_effect=InvalidApiKeyError,
        ),
        patch(
            "menuai.components.nextdns.NextDns.get_analytics_protocols",
            side_effect=InvalidApiKeyError,
        ),
        patch(
            "menuai.components.nextdns.NextDns.get_settings",
            side_effect=InvalidApiKeyError,
        ),
        patch(
            "menuai.components.nextdns.NextDns.connection_status",
            side_effect=InvalidApiKeyError,
        ),
    ):
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1

    flow = flows[0]
    assert flow.get("step_id") == "reauth_confirm"
    assert flow.get("handler") == DOMAIN

    assert "context" in flow
    assert flow["context"].get("source") == SOURCE_REAUTH
    assert flow["context"].get("entry_id") == entry.entry_id
