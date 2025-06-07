"""The sensor tests for the Ruckus platform."""

from datetime import timedelta
from unittest.mock import AsyncMock

from aioruckus.const import ERROR_CONNECT_EOF, ERROR_LOGIN_INCORRECT
from aioruckus.exceptions import AuthenticationError

from menuai.components.ruckus_unleashed import DOMAIN
from menuai.const import STATE_HOME, STATE_NOT_HOME, STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.helpers.entity_component import async_update_entity
from menuai.util import utcnow

from . import (
    DEFAULT_UNIQUEID,
    TEST_CLIENT_ENTITY_ID,
    RuckusAjaxApiPatchContext,
    init_integration,
    mock_config_entry,
)

from tests.common import async_fire_time_changed


async def test_client_connected(menuai: menuai) -> None:
    """Test client connected."""
    await init_integration(menuai)

    future = utcnow() + timedelta(minutes=60)
    with RuckusAjaxApiPatchContext():
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()
        await async_update_entity(menuai, TEST_CLIENT_ENTITY_ID)

    test_client = menuai.states.get(TEST_CLIENT_ENTITY_ID)
    assert test_client.state == STATE_HOME


async def test_client_disconnected(menuai: menuai) -> None:
    """Test client disconnected."""
    await init_integration(menuai)

    future = utcnow() + timedelta(minutes=60)
    with RuckusAjaxApiPatchContext(active_clients={}):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

        await async_update_entity(menuai, TEST_CLIENT_ENTITY_ID)
        test_client = menuai.states.get(TEST_CLIENT_ENTITY_ID)
        assert test_client.state == STATE_NOT_HOME


async def test_clients_update_failed(menuai: menuai) -> None:
    """Test failed update."""
    await init_integration(menuai)

    future = utcnow() + timedelta(minutes=60)
    with RuckusAjaxApiPatchContext(
        active_clients=AsyncMock(side_effect=ConnectionError(ERROR_CONNECT_EOF))
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

        await async_update_entity(menuai, TEST_CLIENT_ENTITY_ID)
        test_client = menuai.states.get(TEST_CLIENT_ENTITY_ID)
        assert test_client.state == STATE_UNAVAILABLE


async def test_clients_update_auth_failed(menuai: menuai) -> None:
    """Test failed update with bad auth."""
    await init_integration(menuai)

    future = utcnow() + timedelta(minutes=60)
    with RuckusAjaxApiPatchContext(
        active_clients=AsyncMock(side_effect=AuthenticationError(ERROR_LOGIN_INCORRECT))
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

        await async_update_entity(menuai, TEST_CLIENT_ENTITY_ID)
        test_client = menuai.states.get(TEST_CLIENT_ENTITY_ID)
        assert test_client.state == STATE_UNAVAILABLE


async def test_restoring_clients(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test restoring existing device_tracker entities if not detected on startup."""
    entry = mock_config_entry()
    entry.add_to_menuai(menuai)

    entity_registry.async_get_or_create(
        "device_tracker",
        DOMAIN,
        DEFAULT_UNIQUEID,
        suggested_object_id="ruckus_test_device",
        config_entry=entry,
    )

    with RuckusAjaxApiPatchContext(active_clients={}):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    device = menuai.states.get(TEST_CLIENT_ENTITY_ID)
    assert device is not None
    assert device.state == STATE_NOT_HOME
