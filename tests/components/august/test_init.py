"""The tests for the august platform."""

from unittest.mock import Mock, patch

from aiohttp import ClientResponseError
import pytest
from yalexs.authenticator_common import AuthenticationState
from yalexs.const import Brand
from yalexs.exceptions import AugustApiAIOHTTPError

from menuai.components.august.const import DOMAIN
from menuai.components.lock import DOMAIN as LOCK_DOMAIN, LockState
from menuai.config_entries import ConfigEntryState
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_LOCK,
    SERVICE_OPEN,
    SERVICE_UNLOCK,
    STATE_ON,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import (
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)
from menuai.setup import async_setup_component

from .mocks import (
    _create_august_with_devices,
    _mock_august_authentication,
    _mock_doorsense_enabled_august_lock_detail,
    _mock_doorsense_missing_august_lock_detail,
    _mock_get_config,
    _mock_inoperative_august_lock_detail,
    _mock_lock_with_offline_key,
    _mock_operative_august_lock_detail,
)

from tests.common import MockConfigEntry
from tests.typing import WebSocketGenerator


async def test_august_api_is_failing(menuai: menuai) -> None:
    """Config entry state is SETUP_RETRY when august api is failing."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=_mock_get_config()[DOMAIN],
        title="August august",
    )
    config_entry.add_to_menuai(menuai)

    with patch(
        "yalexs.authenticator_async.AuthenticatorAsync.async_authenticate",
        side_effect=ClientResponseError(None, None, status=500),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_august_is_offline(menuai: menuai) -> None:
    """Config entry state is SETUP_RETRY when august is offline."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=_mock_get_config()[DOMAIN],
        title="August august",
    )
    config_entry.add_to_menuai(menuai)

    with patch(
        "yalexs.authenticator_async.AuthenticatorAsync.async_authenticate",
        side_effect=TimeoutError,
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_august_late_auth_failure(menuai: menuai) -> None:
    """Test we can detect a late auth failure."""
    aiohttp_client_response_exception = ClientResponseError(None, None, status=401)
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=_mock_get_config()[DOMAIN],
        title="August august",
    )
    config_entry.add_to_menuai(menuai)

    with patch(
        "yalexs.authenticator_async.AuthenticatorAsync.async_authenticate",
        side_effect=AugustApiAIOHTTPError(
            "This should bubble up as its user consumable",
            aiohttp_client_response_exception,
        ),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = menuai.config_entries.flow.async_progress()

    assert flows[0]["step_id"] == "reauth_validate"


async def test_unlock_throws_august_api_http_error(menuai: menuai) -> None:
    """Test unlock throws correct error on http error."""
    mocked_lock_detail = await _mock_operative_august_lock_detail(menuai)
    aiohttp_client_response_exception = ClientResponseError(None, None, status=400)

    def _unlock_return_activities_side_effect(access_token, device_id):
        raise AugustApiAIOHTTPError(
            "This should bubble up as its user consumable",
            aiohttp_client_response_exception,
        )

    await _create_august_with_devices(
        menuai,
        [mocked_lock_detail],
        api_call_side_effects={
            "unlock_return_activities": _unlock_return_activities_side_effect
        },
    )
    data = {ATTR_ENTITY_ID: "lock.a6697750d607098bae8d6baa11ef8063_name"}

    with pytest.raises(
        menuaiError,
        match=(
            "A6697750D607098BAE8D6BAA11EF8063 Name: This should bubble up as its user"
            " consumable"
        ),
    ):
        await menuai.services.async_call(LOCK_DOMAIN, SERVICE_UNLOCK, data, blocking=True)


async def test_lock_throws_august_api_http_error(menuai: menuai) -> None:
    """Test lock throws correct error on http error."""
    mocked_lock_detail = await _mock_operative_august_lock_detail(menuai)
    aiohttp_client_response_exception = ClientResponseError(None, None, status=400)

    def _lock_return_activities_side_effect(access_token, device_id):
        raise AugustApiAIOHTTPError(
            "This should bubble up as its user consumable",
            aiohttp_client_response_exception,
        )

    await _create_august_with_devices(
        menuai,
        [mocked_lock_detail],
        api_call_side_effects={
            "lock_return_activities": _lock_return_activities_side_effect
        },
    )
    data = {ATTR_ENTITY_ID: "lock.a6697750d607098bae8d6baa11ef8063_name"}
    with pytest.raises(
        menuaiError,
        match=(
            "A6697750D607098BAE8D6BAA11EF8063 Name: This should bubble up as its user"
            " consumable"
        ),
    ):
        await menuai.services.async_call(LOCK_DOMAIN, SERVICE_LOCK, data, blocking=True)


async def test_open_throws_menuai_service_not_supported_error(
    menuai: menuai,
) -> None:
    """Test open throws correct error on entity does not support this service error."""
    mocked_lock_detail = await _mock_operative_august_lock_detail(menuai)
    await _create_august_with_devices(menuai, [mocked_lock_detail])
    data = {ATTR_ENTITY_ID: "lock.a6697750d607098bae8d6baa11ef8063_name"}
    with pytest.raises(menuaiError):
        await menuai.services.async_call(LOCK_DOMAIN, SERVICE_OPEN, data, blocking=True)


async def test_inoperative_locks_are_filtered_out(menuai: menuai) -> None:
    """Ensure inoperative locks do not get setup."""
    august_operative_lock = await _mock_operative_august_lock_detail(menuai)
    august_inoperative_lock = await _mock_inoperative_august_lock_detail(menuai)
    await _create_august_with_devices(
        menuai, [august_operative_lock, august_inoperative_lock]
    )

    lock_abc_name = menuai.states.get("lock.abc_name")
    assert lock_abc_name is None
    lock_a6697750d607098bae8d6baa11ef8063_name = menuai.states.get(
        "lock.a6697750d607098bae8d6baa11ef8063_name"
    )
    assert lock_a6697750d607098bae8d6baa11ef8063_name.state == LockState.LOCKED


async def test_lock_has_doorsense(menuai: menuai) -> None:
    """Check to see if a lock has doorsense."""
    doorsenselock = await _mock_doorsense_enabled_august_lock_detail(menuai)
    nodoorsenselock = await _mock_doorsense_missing_august_lock_detail(menuai)
    await _create_august_with_devices(menuai, [doorsenselock, nodoorsenselock])

    binary_sensor_online_with_doorsense_name_open = menuai.states.get(
        "binary_sensor.online_with_doorsense_name_door"
    )
    assert binary_sensor_online_with_doorsense_name_open.state == STATE_ON
    binary_sensor_missing_doorsense_id_name_open = menuai.states.get(
        "binary_sensor.missing_with_doorsense_name_door"
    )
    assert binary_sensor_missing_doorsense_id_name_open is None


async def test_auth_fails(menuai: menuai) -> None:
    """Config entry state is SETUP_ERROR when auth fails."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=_mock_get_config()[DOMAIN],
        title="August august",
    )
    config_entry.add_to_menuai(menuai)
    assert menuai.config_entries.flow.async_progress() == []

    with patch(
        "yalexs.authenticator_async.AuthenticatorAsync.async_authenticate",
        side_effect=ClientResponseError(None, None, status=401),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR

    flows = menuai.config_entries.flow.async_progress()

    assert flows[0]["step_id"] == "reauth_validate"


async def test_bad_password(menuai: menuai) -> None:
    """Config entry state is SETUP_ERROR when the password has been changed."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=_mock_get_config()[DOMAIN],
        title="August august",
    )
    config_entry.add_to_menuai(menuai)
    assert menuai.config_entries.flow.async_progress() == []

    with patch(
        "yalexs.authenticator_async.AuthenticatorAsync.async_authenticate",
        return_value=_mock_august_authentication(
            "original_token", 1234, AuthenticationState.BAD_PASSWORD
        ),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR

    flows = menuai.config_entries.flow.async_progress()

    assert flows[0]["step_id"] == "reauth_validate"


async def test_http_failure(menuai: menuai) -> None:
    """Config entry state is SETUP_RETRY when august is offline."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=_mock_get_config()[DOMAIN],
        title="August august",
    )
    config_entry.add_to_menuai(menuai)
    assert menuai.config_entries.flow.async_progress() == []

    with patch(
        "yalexs.authenticator_async.AuthenticatorAsync.async_authenticate",
        side_effect=ClientResponseError(None, None, status=500),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY

    assert menuai.config_entries.flow.async_progress() == []


async def test_unknown_auth_state(menuai: menuai) -> None:
    """Config entry state is SETUP_ERROR when august is in an unknown auth state."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=_mock_get_config()[DOMAIN],
        title="August august",
    )
    config_entry.add_to_menuai(menuai)
    assert menuai.config_entries.flow.async_progress() == []

    with patch(
        "yalexs.authenticator_async.AuthenticatorAsync.async_authenticate",
        return_value=_mock_august_authentication("original_token", 1234, None),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR

    flows = menuai.config_entries.flow.async_progress()

    assert flows[0]["step_id"] == "reauth_validate"


async def test_requires_validation_state(menuai: menuai) -> None:
    """Config entry state is SETUP_ERROR when august requires validation."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=_mock_get_config()[DOMAIN],
        title="August august",
    )
    config_entry.add_to_menuai(menuai)
    assert menuai.config_entries.flow.async_progress() == []

    with patch(
        "yalexs.authenticator_async.AuthenticatorAsync.async_authenticate",
        return_value=_mock_august_authentication(
            "original_token", 1234, AuthenticationState.REQUIRES_VALIDATION
        ),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR

    assert len(menuai.config_entries.flow.async_progress()) == 1
    assert menuai.config_entries.flow.async_progress()[0]["context"]["source"] == "reauth"


async def test_unknown_auth_http_401(menuai: menuai) -> None:
    """Config entry state is SETUP_ERROR when august gets an http."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=_mock_get_config()[DOMAIN],
        title="August august",
    )
    config_entry.add_to_menuai(menuai)
    assert menuai.config_entries.flow.async_progress() == []

    with patch(
        "yalexs.authenticator_async.AuthenticatorAsync.async_authenticate",
        return_value=_mock_august_authentication("original_token", 1234, None),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR

    flows = menuai.config_entries.flow.async_progress()

    assert flows[0]["step_id"] == "reauth_validate"


async def test_load_unload(menuai: menuai) -> None:
    """Config entry can be unloaded."""

    august_operative_lock = await _mock_operative_august_lock_detail(menuai)
    august_inoperative_lock = await _mock_inoperative_august_lock_detail(menuai)
    config_entry = await _create_august_with_devices(
        menuai, [august_operative_lock, august_inoperative_lock]
    )

    assert config_entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_load_triggers_ble_discovery(
    menuai: menuai, mock_discovery: Mock
) -> None:
    """Test that loading a lock that supports offline ble operation passes the keys to yalexe_ble."""

    august_lock_with_key = await _mock_lock_with_offline_key(menuai)
    august_lock_without_key = await _mock_operative_august_lock_detail(menuai)

    config_entry = await _create_august_with_devices(
        menuai, [august_lock_with_key, august_lock_without_key]
    )
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    assert len(mock_discovery.mock_calls) == 1
    assert mock_discovery.mock_calls[0].kwargs["data"] == {
        "name": "Front Door Lock",
        "address": None,
        "serial": "X2FSW05DGA",
        "key": "kkk01d4300c1dcxxx1c330f794941111",
        "slot": 1,
    }


async def test_device_remove_devices(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test we can only remove a device that no longer exists."""
    assert await async_setup_component(menuai, "config", {})
    august_operative_lock = await _mock_operative_august_lock_detail(menuai)
    config_entry = await _create_august_with_devices(menuai, [august_operative_lock])
    entity = entity_registry.entities["lock.a6697750d607098bae8d6baa11ef8063_name"]

    device_entry = device_registry.async_get(entity.device_id)
    client = await menuai_ws_client(menuai)
    response = await client.remove_device(device_entry.id, config_entry.entry_id)
    assert not response["success"]

    dead_device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, "remove-device-id")},
    )
    response = await client.remove_device(dead_device_entry.id, config_entry.entry_id)
    assert response["success"]


async def test_brand_migration_issue(menuai: menuai) -> None:
    """Test creating and removing the brand migration issue."""
    august_operative_lock = await _mock_operative_august_lock_detail(menuai)
    config_entry = await _create_august_with_devices(
        menuai, [august_operative_lock], brand=Brand.YALE_HOME
    )

    assert config_entry.state is ConfigEntryState.LOADED

    issue_reg = ir.async_get(menuai)
    issue_entry = issue_reg.async_get_issue(DOMAIN, "yale_brand_migration")
    assert issue_entry
    assert issue_entry.severity == ir.IssueSeverity.CRITICAL
    assert issue_entry.translation_placeholders == {
        "migrate_url": "https://my.home-assistant.io/redirect/config_flow_start?domain=yale"
    }

    await menuai.config_entries.async_remove(config_entry.entry_id)
    assert not issue_reg.async_get_issue(DOMAIN, "yale_brand_migration")
