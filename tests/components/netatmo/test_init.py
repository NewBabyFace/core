"""The tests for Netatmo component."""

from datetime import timedelta
from functools import partial
from time import time
from unittest.mock import AsyncMock, patch

import aiohttp
from pyatmo.const import ALL_SCOPES
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components import cloud
from menuai.components.netatmo import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_WEBHOOK_ID, Platform
from menuai.core import CoreState, menuai
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from .common import (
    FAKE_WEBHOOK_ACTIVATION,
    fake_post_request,
    selected_platforms,
    simulate_webhook,
)

from tests.common import MockConfigEntry, async_fire_time_changed
from tests.components.cloud import mock_cloud
from tests.typing import WebSocketGenerator

# Fake webhook thermostat mode change to "Max"
FAKE_WEBHOOK = {
    "room_id": "2746182631",
    "home": {
        "id": "91763b24c43d3e344f424e8b",
        "name": "MYHOME",
        "country": "DE",
        "rooms": [
            {
                "id": "2746182631",
                "name": "Livingroom",
                "type": "livingroom",
                "therm_setpoint_mode": "max",
                "therm_setpoint_end_time": 1612749189,
            }
        ],
        "modules": [
            {"id": "12:34:56:00:01:ae", "name": "Livingroom", "type": "NATherm1"}
        ],
    },
    "mode": "max",
    "event_type": "set_point",
    "push_type": "display_change",
}


async def test_setup_component(
    menuai: menuai, config_entry: MockConfigEntry
) -> None:
    """Test setup and teardown of the netatmo component."""
    with (
        patch(
            "menuai.components.netatmo.api.AsyncConfigEntryNetatmoAuth",
        ) as mock_auth,
        patch(
            "menuai.helpers.config_entry_oauth2_flow.async_get_config_entry_implementation",
        ) as mock_impl,
        patch("menuai.components.netatmo.webhook_generate_url") as mock_webhook,
    ):
        mock_auth.return_value.async_post_api_request.side_effect = partial(
            fake_post_request, menuai
        )
        mock_auth.return_value.async_addwebhook.side_effect = AsyncMock()
        mock_auth.return_value.async_dropwebhook.side_effect = AsyncMock()
        assert await async_setup_component(menuai, "netatmo", {})

    await menuai.async_block_till_done()

    mock_auth.assert_called_once()
    mock_impl.assert_called_once()
    mock_webhook.assert_called_once()

    assert config_entry.state is ConfigEntryState.LOADED
    assert menuai.config_entries.async_entries(DOMAIN)
    assert len(menuai.states.async_all()) > 0

    for entry in menuai.config_entries.async_entries("netatmo"):
        await menuai.config_entries.async_remove(entry.entry_id)

    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == 0
    assert not menuai.config_entries.async_entries(DOMAIN)


async def test_setup_component_with_config(
    menuai: menuai, config_entry: MockConfigEntry
) -> None:
    """Test setup of the netatmo component with dev account."""
    fake_post_hits = 0

    async def fake_post(*args, **kwargs):
        """Fake error during requesting backend data."""
        nonlocal fake_post_hits
        fake_post_hits += 1
        return await fake_post_request(menuai, *args, **kwargs)

    with (
        patch(
            "menuai.helpers.config_entry_oauth2_flow.async_get_config_entry_implementation",
        ) as mock_impl,
        patch("menuai.components.netatmo.webhook_generate_url") as mock_webhook,
        patch(
            "menuai.components.netatmo.api.AsyncConfigEntryNetatmoAuth",
        ) as mock_auth,
        patch("menuai.components.netatmo.data_handler.PLATFORMS", ["sensor"]),
    ):
        mock_auth.return_value.async_post_api_request.side_effect = fake_post
        mock_auth.return_value.async_addwebhook.side_effect = AsyncMock()
        mock_auth.return_value.async_dropwebhook.side_effect = AsyncMock()

        assert await async_setup_component(
            menuai, "netatmo", {"netatmo": {"client_id": "123", "client_secret": "abc"}}
        )

        await menuai.async_block_till_done()

        assert fake_post_hits >= 8
        mock_impl.assert_called_once()
        mock_webhook.assert_called_once()

    assert menuai.config_entries.async_entries(DOMAIN)
    assert len(menuai.states.async_all()) > 0


async def test_setup_component_with_webhook(
    menuai: menuai, config_entry, netatmo_auth
) -> None:
    """Test setup and teardown of the netatmo component with webhook registration."""
    with selected_platforms(
        [Platform.CAMERA, Platform.CLIMATE, Platform.LIGHT, Platform.SENSOR]
    ):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)

        await menuai.async_block_till_done()

    webhook_id = config_entry.data[CONF_WEBHOOK_ID]
    await simulate_webhook(menuai, webhook_id, FAKE_WEBHOOK_ACTIVATION)

    assert len(menuai.states.async_all()) > 0

    webhook_id = config_entry.data[CONF_WEBHOOK_ID]
    await simulate_webhook(menuai, webhook_id, FAKE_WEBHOOK_ACTIVATION)

    # Assert webhook is established successfully
    climate_entity_livingroom = "climate.livingroom"
    assert menuai.states.get(climate_entity_livingroom).state == "auto"
    await simulate_webhook(menuai, webhook_id, FAKE_WEBHOOK)
    assert menuai.states.get(climate_entity_livingroom).state == "heat"

    for entry in menuai.config_entries.async_entries("netatmo"):
        await menuai.config_entries.async_remove(entry.entry_id)

    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == 0
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 0


async def test_setup_without_https(
    menuai: menuai, config_entry: MockConfigEntry, caplog: pytest.LogCaptureFixture
) -> None:
    """Test if set up with cloud link and without https."""
    menuai.config.components.add("cloud")
    with (
        patch(
            "menuai.helpers.network.get_url",
            return_value="http://example.nabu.casa",
        ),
        patch(
            "menuai.components.netatmo.api.AsyncConfigEntryNetatmoAuth"
        ) as mock_auth,
        patch(
            "menuai.helpers.config_entry_oauth2_flow.async_get_config_entry_implementation",
        ),
        patch(
            "menuai.components.netatmo.webhook_generate_url"
        ) as mock_async_generate_url,
    ):
        mock_auth.return_value.async_post_api_request.side_effect = partial(
            fake_post_request, menuai
        )
        mock_async_generate_url.return_value = "http://example.com"
        assert await async_setup_component(
            menuai, "netatmo", {"netatmo": {"client_id": "123", "client_secret": "abc"}}
        )

        await menuai.async_block_till_done()
        mock_auth.assert_called_once()
        mock_async_generate_url.assert_called_once()

    assert "https and port 443 is required to register the webhook" in caplog.text


async def test_setup_with_cloud(
    menuai: menuai, config_entry: MockConfigEntry
) -> None:
    """Test if set up with active cloud subscription."""
    await mock_cloud(menuai)
    await menuai.async_block_till_done()

    with (
        patch("menuai.components.cloud.async_is_logged_in", return_value=True),
        patch.object(cloud, "async_is_connected", return_value=True),
        patch.object(cloud, "async_active_subscription", return_value=True),
        patch(
            "menuai.components.cloud.async_create_cloudhook",
            return_value="https://hooks.nabu.casa/ABCD",
        ) as fake_create_cloudhook,
        patch(
            "menuai.components.cloud.async_delete_cloudhook"
        ) as fake_delete_cloudhook,
        patch(
            "menuai.components.netatmo.api.AsyncConfigEntryNetatmoAuth"
        ) as mock_auth,
        patch("menuai.components.netatmo.data_handler.PLATFORMS", []),
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
        assert await async_setup_component(
            menuai, "netatmo", {"netatmo": {"client_id": "123", "client_secret": "abc"}}
        )
        assert cloud.async_active_subscription(menuai) is True
        assert cloud.async_is_connected(menuai) is True
        fake_create_cloudhook.assert_called_once()

        assert (
            menuai.config_entries.async_entries("netatmo")[0].data["cloudhook_url"]
            == "https://hooks.nabu.casa/ABCD"
        )

        await menuai.async_block_till_done()
        assert menuai.config_entries.async_entries(DOMAIN)

        for entry in menuai.config_entries.async_entries("netatmo"):
            await menuai.config_entries.async_remove(entry.entry_id)
            fake_delete_cloudhook.assert_called_once()

        await menuai.async_block_till_done()
        assert not menuai.config_entries.async_entries(DOMAIN)


async def test_setup_with_cloudhook(menuai: menuai) -> None:
    """Test if set up with active cloud subscription and cloud hook."""
    config_entry = MockConfigEntry(
        domain="netatmo",
        data={
            "auth_implementation": "cloud",
            "cloudhook_url": "https://hooks.nabu.casa/ABCD",
            "token": {
                "refresh_token": "mock-refresh-token",
                "access_token": "mock-access-token",
                "type": "Bearer",
                "expires_in": 60,
                "expires_at": time() + 1000,
                "scope": ALL_SCOPES,
            },
        },
    )
    config_entry.add_to_menuai(menuai)

    await mock_cloud(menuai)
    await menuai.async_block_till_done()

    with (
        patch("menuai.components.cloud.async_is_logged_in", return_value=True),
        patch("menuai.components.cloud.async_is_connected", return_value=True),
        patch.object(cloud, "async_active_subscription", return_value=True),
        patch(
            "menuai.components.cloud.async_create_cloudhook",
            return_value="https://hooks.nabu.casa/ABCD",
        ) as fake_create_cloudhook,
        patch(
            "menuai.components.cloud.async_delete_cloudhook"
        ) as fake_delete_cloudhook,
        patch(
            "menuai.components.netatmo.api.AsyncConfigEntryNetatmoAuth"
        ) as mock_auth,
        patch("menuai.components.netatmo.data_handler.PLATFORMS", []),
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
        assert cloud.async_active_subscription(menuai) is True

        assert (
            menuai.config_entries.async_entries("netatmo")[0].data["cloudhook_url"]
            == "https://hooks.nabu.casa/ABCD"
        )

        await menuai.async_block_till_done()
        assert menuai.config_entries.async_entries(DOMAIN)
        fake_create_cloudhook.assert_not_called()

        for config_entry in menuai.config_entries.async_entries("netatmo"):
            await menuai.config_entries.async_remove(config_entry.entry_id)
            fake_delete_cloudhook.assert_called_once()

        await menuai.async_block_till_done()
        assert not menuai.config_entries.async_entries(DOMAIN)


async def test_setup_component_with_delay(
    menuai: menuai, config_entry: MockConfigEntry
) -> None:
    """Test setup of the netatmo component with delayed startup."""
    menuai.set_state(CoreState.not_running)

    with (
        patch(
            "pyatmo.AbstractAsyncAuth.async_addwebhook", side_effect=AsyncMock()
        ) as mock_addwebhook,
        patch(
            "pyatmo.AbstractAsyncAuth.async_dropwebhook", side_effect=AsyncMock()
        ) as mock_dropwebhook,
        patch(
            "menuai.helpers.config_entry_oauth2_flow.async_get_config_entry_implementation",
        ) as mock_impl,
        patch("menuai.components.netatmo.webhook_generate_url") as mock_webhook,
        patch(
            "pyatmo.AbstractAsyncAuth.async_post_api_request",
            side_effect=partial(fake_post_request, menuai),
        ) as mock_post_api_request,
        patch("menuai.components.netatmo.data_handler.PLATFORMS", ["light"]),
    ):
        assert await async_setup_component(
            menuai, "netatmo", {"netatmo": {"client_id": "123", "client_secret": "abc"}}
        )

        await menuai.async_block_till_done()

        assert mock_post_api_request.call_count == 7

        mock_impl.assert_called_once()
        mock_webhook.assert_not_called()

        await menuai.async_start()
        await menuai.async_block_till_done()
        mock_webhook.assert_called_once()

        # Fake webhook activation
        await simulate_webhook(
            menuai, config_entry.data[CONF_WEBHOOK_ID], FAKE_WEBHOOK_ACTIVATION
        )
        await menuai.async_block_till_done()

        mock_addwebhook.assert_called_once()
        mock_dropwebhook.assert_not_awaited()

        async_fire_time_changed(
            menuai,
            dt_util.utcnow() + timedelta(seconds=60),
        )
        await menuai.async_block_till_done()

        assert menuai.config_entries.async_entries(DOMAIN)
        assert len(menuai.states.async_all()) > 0

        await menuai.async_stop()
        mock_dropwebhook.assert_called_once()


async def test_setup_component_invalid_token_scope(menuai: menuai) -> None:
    """Test handling of invalid token scope."""
    config_entry = MockConfigEntry(
        domain="netatmo",
        data={
            "auth_implementation": "cloud",
            "token": {
                "refresh_token": "mock-refresh-token",
                "access_token": "mock-access-token",
                "type": "Bearer",
                "expires_in": 60,
                "expires_at": time() + 1000,
                "scope": "read_smokedetector read_thermostat write_thermostat",
            },
        },
        options={},
    )
    config_entry.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.netatmo.api.AsyncConfigEntryNetatmoAuth",
        ) as mock_auth,
        patch(
            "menuai.helpers.config_entry_oauth2_flow.async_get_config_entry_implementation",
        ) as mock_impl,
        patch("menuai.components.netatmo.webhook_generate_url") as mock_webhook,
    ):
        mock_auth.return_value.async_post_api_request.side_effect = partial(
            fake_post_request, menuai
        )
        mock_auth.return_value.async_addwebhook.side_effect = AsyncMock()
        mock_auth.return_value.async_dropwebhook.side_effect = AsyncMock()
        assert await async_setup_component(menuai, "netatmo", {})

    await menuai.async_block_till_done()

    mock_auth.assert_not_called()
    mock_impl.assert_called_once()
    mock_webhook.assert_not_called()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    assert menuai.config_entries.async_entries(DOMAIN)

    # Test a reauth flow is initiated
    assert len(list(config_entry.async_get_active_flows(menuai, {"reauth"}))) == 1

    for config_entry in menuai.config_entries.async_entries("netatmo"):
        await menuai.config_entries.async_remove(config_entry.entry_id)


async def test_setup_component_invalid_token(
    menuai: menuai, config_entry: MockConfigEntry
) -> None:
    """Test handling of invalid token."""

    async def fake_ensure_valid_token(*args, **kwargs):
        raise aiohttp.ClientResponseError(
            request_info=aiohttp.client.RequestInfo(
                url="http://example.com",
                method="GET",
                headers={},
                real_url="http://example.com",
            ),
            status=400,
            history=(),
        )

    with (
        patch(
            "menuai.components.netatmo.api.AsyncConfigEntryNetatmoAuth",
        ) as mock_auth,
        patch(
            "menuai.helpers.config_entry_oauth2_flow.async_get_config_entry_implementation",
        ) as mock_impl,
        patch("menuai.components.netatmo.webhook_generate_url") as mock_webhook,
        patch(
            "menuai.helpers.config_entry_oauth2_flow.OAuth2Session"
        ) as mock_session,
    ):
        mock_auth.return_value.async_post_api_request.side_effect = partial(
            fake_post_request, menuai
        )
        mock_auth.return_value.async_addwebhook.side_effect = AsyncMock()
        mock_auth.return_value.async_dropwebhook.side_effect = AsyncMock()
        mock_session.return_value.async_ensure_token_valid.side_effect = (
            fake_ensure_valid_token
        )
        assert await async_setup_component(menuai, "netatmo", {})

    await menuai.async_block_till_done()

    mock_auth.assert_not_called()
    mock_impl.assert_called_once()
    mock_webhook.assert_not_called()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    assert menuai.config_entries.async_entries(DOMAIN)

    # Test a reauth flow is initiated
    assert len(list(config_entry.async_get_active_flows(menuai, {"reauth"}))) == 1

    for entry in menuai.config_entries.async_entries("netatmo"):
        await menuai.config_entries.async_remove(entry.entry_id)


async def test_devices(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    netatmo_auth: AsyncMock,
) -> None:
    """Test devices are registered."""
    with selected_platforms(
        [
            Platform.CAMERA,
            Platform.CLIMATE,
            Platform.COVER,
            Platform.LIGHT,
            Platform.SELECT,
            Platform.SENSOR,
            Platform.SWITCH,
        ]
    ):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)

        await menuai.async_block_till_done()

    device_entries = dr.async_entries_for_config_entry(
        device_registry, config_entry.entry_id
    )

    assert device_entries

    for device_entry in device_entries:
        identifier = list(device_entry.identifiers)[0]
        assert device_entry == snapshot(name=f"{identifier[0]}-{identifier[1]}")


async def test_device_remove_devices(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    config_entry: MockConfigEntry,
    netatmo_auth: AsyncMock,
) -> None:
    """Test we can only remove a device that no longer exists."""

    assert await async_setup_component(menuai, "config", {})

    with selected_platforms([Platform.CLIMATE]):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)

        await menuai.async_block_till_done()

    climate_entity_livingroom = "climate.livingroom"
    entity = entity_registry.async_get(climate_entity_livingroom)

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
