"""Test button of NextDNS integration."""

from unittest.mock import Mock, patch

from aiohttp import ClientError
from aiohttp.client_exceptions import ClientConnectorError
from nextdns import ApiError, InvalidApiKeyError
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.components.nextdns.const import DOMAIN
from menuai.config_entries import SOURCE_REAUTH, ConfigEntryState
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er
from menuai.util import dt as dt_util

from . import init_integration

from tests.common import snapshot_platform


async def test_button(
    menuai: menuai, entity_registry: er.EntityRegistry, snapshot: SnapshotAssertion
) -> None:
    """Test states of the button."""
    with patch("menuai.components.nextdns.PLATFORMS", [Platform.BUTTON]):
        entry = await init_integration(menuai)

    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)


async def test_button_press(menuai: menuai) -> None:
    """Test button press."""
    await init_integration(menuai)

    now = dt_util.utcnow()
    with (
        patch("menuai.components.nextdns.NextDns.clear_logs") as mock_clear_logs,
        patch("menuai.core.dt_util.utcnow", return_value=now),
    ):
        await menuai.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: "button.fake_profile_clear_logs"},
            blocking=True,
        )
        await menuai.async_block_till_done()

    mock_clear_logs.assert_called_once()

    state = menuai.states.get("button.fake_profile_clear_logs")
    assert state
    assert state.state == now.isoformat()


@pytest.mark.parametrize(
    "exc",
    [
        ApiError(Mock()),
        TimeoutError,
        ClientConnectorError(Mock(), Mock()),
        ClientError,
    ],
)
async def test_button_failure(menuai: menuai, exc: Exception) -> None:
    """Tests that the press action throws menuaiError."""
    await init_integration(menuai)

    with (
        patch("menuai.components.nextdns.NextDns.clear_logs", side_effect=exc),
        pytest.raises(
            menuaiError,
            match="An error occurred while calling the NextDNS API method for button.fake_profile_clear_logs",
        ),
    ):
        await menuai.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: "button.fake_profile_clear_logs"},
            blocking=True,
        )


async def test_button_auth_error(menuai: menuai) -> None:
    """Tests that the press action starts re-auth flow."""
    entry = await init_integration(menuai)

    with patch(
        "menuai.components.nextdns.NextDns.clear_logs",
        side_effect=InvalidApiKeyError,
    ):
        await menuai.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: "button.fake_profile_clear_logs"},
            blocking=True,
        )

    assert entry.state is ConfigEntryState.LOADED

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1

    flow = flows[0]
    assert flow.get("step_id") == "reauth_confirm"
    assert flow.get("handler") == DOMAIN

    assert "context" in flow
    assert flow["context"].get("source") == SOURCE_REAUTH
    assert flow["context"].get("entry_id") == entry.entry_id
