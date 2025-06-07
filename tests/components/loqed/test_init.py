"""Tests the init part of the Loqed integration."""

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import aiohttp
from loqedAPI import loqed

from menuai.components.loqed.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_WEBHOOK_ID
from menuai.core import menuai
from menuai.helpers.network import get_url
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry, async_load_fixture
from tests.typing import ClientSessionGenerator


async def test_webhook_accepts_valid_message(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    integration: MockConfigEntry,
    lock: loqed.Lock,
) -> None:
    """Test webhook called with valid message."""
    await async_setup_component(menuai, "http", {"http": {}})
    client = await menuai_client_no_auth()
    processed_message = json.loads(
        await async_load_fixture(menuai, "lock_going_to_nightlock.json", DOMAIN)
    )
    lock.receiveWebhook = AsyncMock(return_value=processed_message)

    message = await async_load_fixture(menuai, "battery_update.json", DOMAIN)
    timestamp = 1653304609
    await client.post(
        f"/api/webhook/{integration.data[CONF_WEBHOOK_ID]}",
        data=message,
        headers={"timestamp": str(timestamp), "hash": "incorrect hash"},
    )
    lock.receiveWebhook.assert_called()


async def test_setup_webhook_in_bridge(
    menuai: menuai, config_entry: MockConfigEntry, lock: loqed.Lock
) -> None:
    """Test webhook setup in loqed bridge."""
    config: dict[str, Any] = {DOMAIN: {}}
    config_entry.add_to_menuai(menuai)

    lock_status = json.loads(await async_load_fixture(menuai, "status_ok.json", DOMAIN))
    webhooks_fixture = json.loads(
        await async_load_fixture(menuai, "get_all_webhooks.json", DOMAIN)
    )
    lock.getWebhooks = AsyncMock(side_effect=[[], webhooks_fixture])

    with (
        patch("loqedAPI.loqed.LoqedAPI.async_get_lock", return_value=lock),
        patch(
            "loqedAPI.loqed.LoqedAPI.async_get_lock_details", return_value=lock_status
        ),
    ):
        await async_setup_component(menuai, DOMAIN, config)
        await menuai.async_block_till_done()

    lock.registerWebhook.assert_called_with(f"{get_url(menuai)}/api/webhook/Webhook_id")


async def test_cannot_connect_to_bridge_will_retry(
    menuai: menuai, config_entry: MockConfigEntry, lock: loqed.Lock
) -> None:
    """Test webhook setup in loqed bridge."""
    config: dict[str, Any] = {DOMAIN: {}}
    config_entry.add_to_menuai(menuai)

    with patch(
        "loqedAPI.loqed.LoqedAPI.async_get_lock", side_effect=aiohttp.ClientError
    ):
        await async_setup_component(menuai, DOMAIN, config)
        await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_cloudhook_in_bridge(
    menuai: menuai, config_entry: MockConfigEntry, lock: loqed.Lock
) -> None:
    """Test webhook setup in loqed bridge."""
    config: dict[str, Any] = {DOMAIN: {}}
    config_entry.add_to_menuai(menuai)

    lock_status = json.loads(await async_load_fixture(menuai, "status_ok.json", DOMAIN))
    webhooks_fixture = json.loads(
        await async_load_fixture(menuai, "get_all_webhooks.json", DOMAIN)
    )
    lock.getWebhooks = AsyncMock(side_effect=[[], webhooks_fixture])

    with (
        patch("loqedAPI.loqed.LoqedAPI.async_get_lock", return_value=lock),
        patch(
            "loqedAPI.loqed.LoqedAPI.async_get_lock_details", return_value=lock_status
        ),
        patch(
            "menuai.components.cloud.async_active_subscription",
            return_value=True,
        ),
        patch(
            "menuai.components.cloud.async_create_cloudhook",
            return_value=webhooks_fixture[0]["url"],
        ),
    ):
        await async_setup_component(menuai, DOMAIN, config)
        await menuai.async_block_till_done()

    lock.registerWebhook.assert_called_with(f"{get_url(menuai)}/api/webhook/Webhook_id")


async def test_setup_cloudhook_from_entry_in_bridge(
    menuai: menuai, cloud_config_entry: MockConfigEntry, lock: loqed.Lock
) -> None:
    """Test webhook setup in loqed bridge."""
    webhooks_fixture = json.loads(
        await async_load_fixture(menuai, "get_all_webhooks.json", DOMAIN)
    )

    config: dict[str, Any] = {DOMAIN: {}}
    cloud_config_entry.add_to_menuai(menuai)

    lock_status = json.loads(await async_load_fixture(menuai, "status_ok.json", DOMAIN))

    lock.getWebhooks = AsyncMock(side_effect=[[], webhooks_fixture])

    with (
        patch("loqedAPI.loqed.LoqedAPI.async_get_lock", return_value=lock),
        patch(
            "loqedAPI.loqed.LoqedAPI.async_get_lock_details", return_value=lock_status
        ),
        patch(
            "menuai.components.cloud.async_active_subscription",
            return_value=True,
        ),
        patch(
            "menuai.components.cloud.async_create_cloudhook",
            return_value=webhooks_fixture[0]["url"],
        ),
    ):
        await async_setup_component(menuai, DOMAIN, config)
        await menuai.async_block_till_done()

    lock.registerWebhook.assert_called_with(f"{get_url(menuai)}/api/webhook/Webhook_id")


async def test_unload_entry(
    menuai: menuai, integration: MockConfigEntry, lock: loqed.Lock
) -> None:
    """Test successful unload of entry."""

    assert await menuai.config_entries.async_unload(integration.entry_id)
    await menuai.async_block_till_done()

    lock.deleteWebhook.assert_called_with(1)
    assert integration.state is ConfigEntryState.NOT_LOADED
    assert not menuai.data.get(DOMAIN)


async def test_unload_entry_fails(
    menuai: menuai, integration: MockConfigEntry, lock: loqed.Lock
) -> None:
    """Test unsuccessful unload of entry."""
    lock.deleteWebhook = AsyncMock(side_effect=Exception)

    assert not await menuai.config_entries.async_unload(integration.entry_id)
