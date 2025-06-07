"""Test HomematicIP Cloud accesspoint."""

from unittest.mock import Mock, patch

from homematicip.auth import Auth
from homematicip.connection.connection_context import ConnectionContext
from homematicip.exceptions.connection_exceptions import HmipConnectionError
import pytest

from menuai.components.homematicip_cloud import DOMAIN
from menuai.components.homematicip_cloud.const import (
    HMIPC_AUTHTOKEN,
    HMIPC_HAPID,
    HMIPC_NAME,
    HMIPC_PIN,
)
from menuai.components.homematicip_cloud.errors import HmipcConnectionError
from menuai.components.homematicip_cloud.hap import (
    HomematicipAuth,
    HomematicipHAP,
)
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady

from .helper import HAPID, HAPPIN, HomeFactory

from tests.common import MockConfigEntry


async def test_auth_setup(menuai: menuai) -> None:
    """Test auth setup for client registration."""
    config = {HMIPC_HAPID: "ABC123", HMIPC_PIN: "123", HMIPC_NAME: "hmip"}
    hmip_auth = HomematicipAuth(menuai, config)
    with patch.object(hmip_auth, "get_auth"):
        assert await hmip_auth.async_setup()


async def test_auth_setup_connection_error(menuai: menuai) -> None:
    """Test auth setup connection error behaviour."""
    config = {HMIPC_HAPID: "ABC123", HMIPC_PIN: "123", HMIPC_NAME: "hmip"}
    hmip_auth = HomematicipAuth(menuai, config)
    with patch.object(hmip_auth, "get_auth", side_effect=HmipcConnectionError):
        assert not await hmip_auth.async_setup()


async def test_auth_auth_check_and_register(menuai: menuai) -> None:
    """Test auth client registration."""
    config = {HMIPC_HAPID: "ABC123", HMIPC_PIN: "123", HMIPC_NAME: "hmip"}

    hmip_auth = HomematicipAuth(menuai, config)
    hmip_auth.auth = Mock(spec=Auth)
    with (
        patch.object(hmip_auth.auth, "is_request_acknowledged", return_value=True),
        patch.object(hmip_auth.auth, "request_auth_token", return_value="ABC"),
        patch.object(
            hmip_auth.auth,
            "confirm_auth_token",
        ),
    ):
        assert await hmip_auth.async_checkbutton()
        assert await hmip_auth.async_register() == "ABC"


async def test_auth_auth_check_and_register_with_exception(menuai: menuai) -> None:
    """Test auth client registration."""
    config = {HMIPC_HAPID: "ABC123", HMIPC_PIN: "123", HMIPC_NAME: "hmip"}
    hmip_auth = HomematicipAuth(menuai, config)
    hmip_auth.auth = Mock(spec=Auth)
    with (
        patch.object(
            hmip_auth.auth, "is_request_acknowledged", side_effect=HmipConnectionError
        ),
        patch.object(
            hmip_auth.auth, "request_auth_token", side_effect=HmipConnectionError
        ),
    ):
        assert not await hmip_auth.async_checkbutton()
        assert await hmip_auth.async_register() is False


async def test_hap_setup_works(menuai: menuai) -> None:
    """Test a successful setup of a accesspoint."""
    # This test should not be accessing the integration internals
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={HMIPC_HAPID: "ABC123", HMIPC_AUTHTOKEN: "123", HMIPC_NAME: "hmip"},
    )
    home = Mock()
    hap = HomematicipHAP(menuai, entry)
    with patch.object(hap, "get_hap", return_value=home):
        async with entry.setup_lock:
            assert await hap.async_setup()

    assert hap.home is home


async def test_hap_setup_connection_error() -> None:
    """Test a failed accesspoint setup."""
    menuai = Mock()
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={HMIPC_HAPID: "ABC123", HMIPC_AUTHTOKEN: "123", HMIPC_NAME: "hmip"},
    )
    hap = HomematicipHAP(menuai, entry)
    with (
        patch.object(hap, "get_hap", side_effect=HmipcConnectionError),
        pytest.raises(ConfigEntryNotReady),
    ):
        async with entry.setup_lock:
            assert not await hap.async_setup()

    assert not menuai.async_run_menuai_job.mock_calls
    assert not menuai.config_entries.flow.async_init.mock_calls


async def test_hap_reset_unloads_entry_if_setup(
    menuai: menuai, default_mock_hap_factory: HomeFactory
) -> None:
    """Test calling reset while the entry has been setup."""
    mock_hap = await default_mock_hap_factory.async_get_mock_hap()
    config_entries = menuai.config_entries.async_entries(DOMAIN)
    assert len(config_entries) == 1
    assert config_entries[0].runtime_data == mock_hap
    # hap_reset is called during unload
    await menuai.config_entries.async_unload(config_entries[0].entry_id)
    # entry is unloaded
    assert config_entries[0].state is ConfigEntryState.NOT_LOADED


async def test_hap_create(
    menuai: menuai, hmip_config_entry: MockConfigEntry, simple_mock_home
) -> None:
    """Mock AsyncHome to execute get_hap."""
    menuai.config.components.add(DOMAIN)
    hap = HomematicipHAP(menuai, hmip_config_entry)
    assert hap
    with (
        patch(
            "menuai.components.homematicip_cloud.hap.ConnectionContextBuilder.build_context_async",
            return_value=ConnectionContext(),
        ),
        patch.object(hap, "async_connect"),
    ):
        async with hmip_config_entry.setup_lock:
            assert await hap.async_setup()


async def test_hap_create_exception(
    menuai: menuai, hmip_config_entry: MockConfigEntry, mock_connection_init
) -> None:
    """Mock AsyncHome to execute get_hap."""
    menuai.config.components.add(DOMAIN)

    hap = HomematicipHAP(menuai, hmip_config_entry)
    assert hap

    with (
        patch(
            "menuai.components.homematicip_cloud.hap.ConnectionContextBuilder.build_context_async",
            return_value=ConnectionContext(),
        ),
        patch(
            "menuai.components.homematicip_cloud.hap.AsyncHome.get_current_state_async",
            side_effect=Exception,
        ),
    ):
        assert not await hap.async_setup()

    with (
        patch(
            "menuai.components.homematicip_cloud.hap.ConnectionContextBuilder.build_context_async",
            return_value=ConnectionContext(),
        ),
        patch(
            "menuai.components.homematicip_cloud.hap.AsyncHome.get_current_state_async",
            side_effect=HmipConnectionError,
        ),
        pytest.raises(ConfigEntryNotReady),
    ):
        await hap.async_setup()


async def test_auth_create(menuai: menuai, simple_mock_auth) -> None:
    """Mock AsyncAuth to execute get_auth."""
    config = {HMIPC_HAPID: HAPID, HMIPC_PIN: HAPPIN, HMIPC_NAME: "hmip"}
    hmip_auth = HomematicipAuth(menuai, config)
    assert hmip_auth

    with (
        patch(
            "menuai.components.homematicip_cloud.hap.Auth",
            return_value=simple_mock_auth,
        ),
        patch(
            "menuai.components.homematicip_cloud.hap.ConnectionContextBuilder.build_context_async",
            return_value=ConnectionContext(),
        ),
    ):
        assert await hmip_auth.async_setup()
        await menuai.async_block_till_done()
        assert hmip_auth.auth.pin == HAPPIN


async def test_auth_create_exception(menuai: menuai, simple_mock_auth) -> None:
    """Mock AsyncAuth to execute get_auth."""
    config = {HMIPC_HAPID: HAPID, HMIPC_PIN: HAPPIN, HMIPC_NAME: "hmip"}
    hmip_auth = HomematicipAuth(menuai, config)
    simple_mock_auth.connection_request.side_effect = HmipConnectionError
    assert hmip_auth
    with (
        patch(
            "menuai.components.homematicip_cloud.hap.Auth",
            return_value=simple_mock_auth,
        ),
        patch(
            "menuai.components.homematicip_cloud.hap.ConnectionContextBuilder.build_context_async",
            return_value=ConnectionContext(),
        ),
    ):
        assert not await hmip_auth.async_setup()

    with (
        patch(
            "menuai.components.homematicip_cloud.hap.Auth",
            return_value=simple_mock_auth,
        ),
        patch(
            "menuai.components.homematicip_cloud.hap.ConnectionContextBuilder.build_context_async",
            return_value=ConnectionContext(),
        ),
    ):
        assert not await hmip_auth.get_auth(menuai, HAPID, HAPPIN)
