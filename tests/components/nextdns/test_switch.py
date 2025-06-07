"""Test switch of NextDNS integration."""

from datetime import timedelta
from unittest.mock import Mock, patch

from aiohttp import ClientError
from aiohttp.client_exceptions import ClientConnectorError
from nextdns import ApiError, InvalidApiKeyError
import pytest
from syrupy.assertion import SnapshotAssertion
from tenacity import RetryError

from menuai.components.nextdns.const import DOMAIN
from menuai.components.switch import DOMAIN as SWITCH_DOMAIN
from menuai.config_entries import SOURCE_REAUTH, ConfigEntryState
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    Platform,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er
from menuai.util.dt import utcnow

from . import init_integration, mock_nextdns

from tests.common import async_fire_time_changed, snapshot_platform


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_switch(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test states of the switches."""
    with patch("menuai.components.nextdns.PLATFORMS", [Platform.SWITCH]):
        entry = await init_integration(menuai)

    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)


async def test_switch_on(menuai: menuai) -> None:
    """Test the switch can be turned on."""
    await init_integration(menuai)

    state = menuai.states.get("switch.fake_profile_block_page")
    assert state
    assert state.state == STATE_OFF

    with patch(
        "menuai.components.nextdns.NextDns.set_setting", return_value=True
    ) as mock_switch_on:
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: "switch.fake_profile_block_page"},
            blocking=True,
        )
        await menuai.async_block_till_done()

        state = menuai.states.get("switch.fake_profile_block_page")
        assert state
        assert state.state == STATE_ON

        mock_switch_on.assert_called_once()


async def test_switch_off(menuai: menuai) -> None:
    """Test the switch can be turned on."""
    await init_integration(menuai)

    state = menuai.states.get("switch.fake_profile_web3")
    assert state
    assert state.state == STATE_ON

    with patch(
        "menuai.components.nextdns.NextDns.set_setting", return_value=True
    ) as mock_switch_on:
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: "switch.fake_profile_web3"},
            blocking=True,
        )
        await menuai.async_block_till_done()

        state = menuai.states.get("switch.fake_profile_web3")
        assert state
        assert state.state == STATE_OFF

        mock_switch_on.assert_called_once()


@pytest.mark.parametrize(
    "exc",
    [
        ApiError("API Error"),
        RetryError("Retry Error"),
        TimeoutError,
    ],
)
async def test_availability(menuai: menuai, exc: Exception) -> None:
    """Ensure that we mark the entities unavailable correctly when service causes an error."""
    await init_integration(menuai)

    state = menuai.states.get("switch.fake_profile_web3")
    assert state
    assert state.state != STATE_UNAVAILABLE
    assert state.state == STATE_ON

    future = utcnow() + timedelta(minutes=10)
    with patch(
        "menuai.components.nextdns.NextDns.get_settings",
        side_effect=exc,
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get("switch.fake_profile_web3")
    assert state
    assert state.state == STATE_UNAVAILABLE

    future = utcnow() + timedelta(minutes=20)
    with mock_nextdns():
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get("switch.fake_profile_web3")
    assert state
    assert state.state != STATE_UNAVAILABLE
    assert state.state == STATE_ON


@pytest.mark.parametrize(
    "exc",
    [
        ApiError(Mock()),
        TimeoutError,
        ClientConnectorError(Mock(), Mock()),
        ClientError,
    ],
)
async def test_switch_failure(menuai: menuai, exc: Exception) -> None:
    """Tests that the turn on/off service throws menuaiError."""
    await init_integration(menuai)

    with (
        patch("menuai.components.nextdns.NextDns.set_setting", side_effect=exc),
        pytest.raises(menuaiError),
    ):
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: "switch.fake_profile_block_page"},
            blocking=True,
        )


async def test_switch_auth_error(menuai: menuai) -> None:
    """Tests that the turn on/off action starts re-auth flow."""
    entry = await init_integration(menuai)

    with patch(
        "menuai.components.nextdns.NextDns.set_setting",
        side_effect=InvalidApiKeyError,
    ):
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: "switch.fake_profile_block_page"},
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
