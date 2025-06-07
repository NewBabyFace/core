"""Test init of NextDNS integration."""

from unittest.mock import patch

from nextdns import ApiError, InvalidApiKeyError
import pytest
from tenacity import RetryError

from menuai.components.nextdns.const import CONF_PROFILE_ID, DOMAIN
from menuai.config_entries import SOURCE_REAUTH, ConfigEntryState
from menuai.const import CONF_API_KEY, STATE_UNAVAILABLE
from menuai.core import menuai

from . import init_integration

from tests.common import MockConfigEntry


async def test_async_setup_entry(menuai: menuai) -> None:
    """Test a successful setup entry."""
    await init_integration(menuai)

    state = menuai.states.get("sensor.fake_profile_dns_queries_blocked_ratio")
    assert state is not None
    assert state.state != STATE_UNAVAILABLE
    assert state.state == "20.0"


@pytest.mark.parametrize(
    "exc", [ApiError("API Error"), RetryError("Retry Error"), TimeoutError]
)
async def test_config_not_ready(menuai: menuai, exc: Exception) -> None:
    """Test for setup failure if the connection to the service fails."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Fake Profile",
        unique_id="xyz12",
        data={CONF_API_KEY: "fake_api_key", CONF_PROFILE_ID: "xyz12"},
    )

    with patch(
        "menuai.components.nextdns.NextDns.get_profiles",
        side_effect=exc,
    ):
        entry.add_to_menuai(menuai)
        await menuai.config_entries.async_setup(entry.entry_id)
        assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload_entry(menuai: menuai) -> None:
    """Test successful unload of entry."""
    entry = await init_integration(menuai)

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert not menuai.data.get(DOMAIN)


async def test_config_auth_failed(menuai: menuai) -> None:
    """Test for setup failure if the auth fails."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Fake Profile",
        unique_id="xyz12",
        data={CONF_API_KEY: "fake_api_key", CONF_PROFILE_ID: "xyz12"},
    )
    entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.nextdns.NextDns.get_profiles",
        side_effect=InvalidApiKeyError,
    ):
        await menuai.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.SETUP_ERROR

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1

    flow = flows[0]
    assert flow.get("step_id") == "reauth_confirm"
    assert flow.get("handler") == DOMAIN

    assert "context" in flow
    assert flow["context"].get("source") == SOURCE_REAUTH
    assert flow["context"].get("entry_id") == entry.entry_id
