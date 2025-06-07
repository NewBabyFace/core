"""Tests for the Overseerr integration."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from python_overseerr import OverseerrAuthenticationError, OverseerrConnectionError
from python_overseerr.models import WebhookNotificationOptions
from syrupy.assertion import SnapshotAssertion

from menuai.components import cloud
from menuai.components.cloud import CloudNotAvailable
from menuai.components.overseerr import (
    CONF_CLOUDHOOK_URL,
    JSON_PAYLOAD,
    REGISTERED_NOTIFICATIONS,
)
from menuai.components.overseerr.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from . import setup_integration

from tests.common import MockConfigEntry
from tests.components.cloud import mock_cloud


@pytest.mark.parametrize(
    ("exception", "config_entry_state"),
    [
        (OverseerrAuthenticationError, ConfigEntryState.SETUP_ERROR),
        (OverseerrConnectionError, ConfigEntryState.SETUP_RETRY),
    ],
)
async def test_initialization_errors(
    menuai: menuai,
    mock_overseerr_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    exception: Exception,
    config_entry_state: ConfigEntryState,
) -> None:
    """Test the Overseerr integration initialization errors."""
    mock_overseerr_client.get_request_count.side_effect = exception

    await setup_integration(menuai, mock_config_entry)

    assert mock_config_entry.state == config_entry_state


async def test_device_info(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_overseerr_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test device registry integration."""
    await setup_integration(menuai, mock_config_entry)
    device_entry = device_registry.async_get_device(
        identifiers={(DOMAIN, mock_config_entry.entry_id)}
    )
    assert device_entry is not None
    assert device_entry == snapshot


async def test_proper_webhook_configuration(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_overseerr_client: AsyncMock,
) -> None:
    """Test the webhook configuration."""
    await setup_integration(menuai, mock_config_entry)

    assert REGISTERED_NOTIFICATIONS == 222

    mock_overseerr_client.test_webhook_notification_config.assert_not_called()
    mock_overseerr_client.set_webhook_notification_config.assert_not_called()


@pytest.mark.parametrize(
    "update_mock",
    [
        {"return_value.enabled": False},
        {"return_value.types": 4},
        {"return_value.types": 4062},
        {
            "return_value.options": WebhookNotificationOptions(
                webhook_url="http://example.com", json_payload=JSON_PAYLOAD
            )
        },
        {
            "return_value.options": WebhookNotificationOptions(
                webhook_url="http://10.10.10.10:8123/api/webhook/test-webhook-id",
                json_payload='"{\\"message\\": \\"{{title}}\\"}"',
            )
        },
    ],
    ids=[
        "Disabled",
        "Smaller scope",
        "Bigger scope",
        "Webhook URL",
        "JSON Payload",
    ],
)
async def test_webhook_configuration_need_update(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_overseerr_client: AsyncMock,
    update_mock: dict[str, Any],
) -> None:
    """Test the webhook configuration."""
    mock_overseerr_client.get_webhook_notification_config.configure_mock(**update_mock)

    await setup_integration(menuai, mock_config_entry)

    mock_overseerr_client.test_webhook_notification_config.assert_called_once()
    mock_overseerr_client.set_webhook_notification_config.assert_called_once()


@pytest.mark.parametrize(
    "update_mock",
    [
        {"return_value.enabled": False},
        {"return_value.types": 4},
        {"return_value.types": 4062},
        {
            "return_value.options": WebhookNotificationOptions(
                webhook_url="http://example.com", json_payload=JSON_PAYLOAD
            )
        },
        {
            "return_value.options": WebhookNotificationOptions(
                webhook_url="http://10.10.10.10:8123/api/webhook/test-webhook-id",
                json_payload='"{\\"message\\": \\"{{title}}\\"}"',
            )
        },
    ],
    ids=[
        "Disabled",
        "Smaller scope",
        "Bigger scope",
        "Webhook URL",
        "JSON Payload",
    ],
)
async def test_webhook_failing_test(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_overseerr_client: AsyncMock,
    update_mock: dict[str, Any],
) -> None:
    """Test the webhook configuration."""
    mock_overseerr_client.test_webhook_notification_config.return_value = False
    mock_overseerr_client.get_webhook_notification_config.configure_mock(**update_mock)

    await setup_integration(menuai, mock_config_entry)

    mock_overseerr_client.test_webhook_notification_config.assert_called_once()
    mock_overseerr_client.set_webhook_notification_config.assert_not_called()


async def test_prefer_internal_ip(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_overseerr_client: AsyncMock,
) -> None:
    """Test the integration prefers internal IP."""
    mock_overseerr_client.test_webhook_notification_config.return_value = False
    menuai.config.internal_url = "http://192.168.0.123:8123"
    menuai.config.external_url = "https://www.example.com"
    await menuai.async_block_till_done(wait_background_tasks=True)
    await setup_integration(menuai, mock_config_entry)

    assert (
        mock_overseerr_client.test_webhook_notification_config.call_args_list[0][0][0]
        == "http://192.168.0.123:8123/api/webhook/test-webhook-id"
    )
    assert (
        mock_overseerr_client.test_webhook_notification_config.call_args_list[1][0][0]
        == "https://www.example.com/api/webhook/test-webhook-id"
    )


async def test_cloudhook_setup(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_overseerr_client_needs_change: AsyncMock,
) -> None:
    """Test if set up with active cloud subscription and cloud hook."""

    await mock_cloud(menuai)
    await menuai.async_block_till_done()

    mock_overseerr_client_needs_change.test_webhook_notification_config.side_effect = [
        False,
        True,
    ]

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
    ):
        await setup_integration(menuai, mock_config_entry)

        assert cloud.async_active_subscription(menuai) is True

        assert (
            mock_config_entry.data[CONF_CLOUDHOOK_URL] == "https://hooks.nabu.casa/ABCD"
        )

        assert (
            len(
                mock_overseerr_client_needs_change.test_webhook_notification_config.mock_calls
            )
            == 2
        )

        assert menuai.config_entries.async_entries(DOMAIN)
        fake_create_cloudhook.assert_called()

        for config_entry in menuai.config_entries.async_entries(DOMAIN):
            await menuai.config_entries.async_remove(config_entry.entry_id)
            fake_delete_cloudhook.assert_called_once()

        await menuai.async_block_till_done()
        assert not menuai.config_entries.async_entries(DOMAIN)


async def test_cloudhook_consistent(
    menuai: menuai,
    mock_cloudhook_config_entry: MockConfigEntry,
    mock_overseerr_client_needs_change: AsyncMock,
) -> None:
    """Test if we keep the cloudhook if it is already set up."""

    await mock_cloud(menuai)
    await menuai.async_block_till_done()

    mock_overseerr_client_needs_change.test_webhook_notification_config.side_effect = [
        False,
        True,
    ]

    with (
        patch("menuai.components.cloud.async_is_logged_in", return_value=True),
        patch("menuai.components.cloud.async_is_connected", return_value=True),
        patch.object(cloud, "async_active_subscription", return_value=True),
        patch(
            "menuai.components.cloud.async_create_cloudhook",
            return_value="https://hooks.nabu.casa/ABCD",
        ) as fake_create_cloudhook,
    ):
        await setup_integration(menuai, mock_cloudhook_config_entry)

        assert cloud.async_active_subscription(menuai) is True

        assert (
            mock_cloudhook_config_entry.data[CONF_CLOUDHOOK_URL]
            == "https://hooks.nabu.casa/ABCD"
        )

        assert (
            len(
                mock_overseerr_client_needs_change.test_webhook_notification_config.mock_calls
            )
            == 2
        )

        assert menuai.config_entries.async_entries(DOMAIN)
        fake_create_cloudhook.assert_not_called()


async def test_cloudhook_needs_no_change(
    menuai: menuai,
    mock_cloudhook_config_entry: MockConfigEntry,
    mock_overseerr_client_cloudhook: AsyncMock,
) -> None:
    """Test if we keep the cloudhook if it is already set up."""

    await setup_integration(menuai, mock_cloudhook_config_entry)

    assert (
        len(mock_overseerr_client_cloudhook.test_webhook_notification_config.mock_calls)
        == 0
    )


async def test_cloudhook_not_needed(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_overseerr_client_needs_change: AsyncMock,
) -> None:
    """Test if we prefer local webhook over cloudhook."""

    await menuai.async_block_till_done()

    with (
        patch.object(cloud, "async_active_subscription", return_value=True),
    ):
        await setup_integration(menuai, mock_config_entry)

        assert cloud.async_active_subscription(menuai) is True

        assert CONF_CLOUDHOOK_URL not in mock_config_entry.data

        assert (
            len(
                mock_overseerr_client_needs_change.test_webhook_notification_config.mock_calls
            )
            == 1
        )
        assert (
            mock_overseerr_client_needs_change.test_webhook_notification_config.call_args_list[
                0
            ][0][0]
            == "http://10.10.10.10:8123/api/webhook/test-webhook-id"
        )


async def test_cloudhook_not_connecting(
    menuai: menuai,
    mock_cloudhook_config_entry: MockConfigEntry,
    mock_overseerr_client_needs_change: AsyncMock,
) -> None:
    """Test the cloudhook is not registered if Overseerr cannot connect to it."""

    await mock_cloud(menuai)
    await menuai.async_block_till_done()

    mock_overseerr_client_needs_change.test_webhook_notification_config.return_value = (
        False
    )

    with (
        patch("menuai.components.cloud.async_is_logged_in", return_value=True),
        patch("menuai.components.cloud.async_is_connected", return_value=True),
        patch.object(cloud, "async_active_subscription", return_value=True),
        patch(
            "menuai.components.cloud.async_create_cloudhook",
            return_value="https://hooks.nabu.casa/ABCD",
        ) as fake_create_cloudhook,
    ):
        await setup_integration(menuai, mock_cloudhook_config_entry)

        assert cloud.async_active_subscription(menuai) is True

        assert (
            mock_cloudhook_config_entry.data[CONF_CLOUDHOOK_URL]
            == "https://hooks.nabu.casa/ABCD"
        )

        assert (
            len(
                mock_overseerr_client_needs_change.test_webhook_notification_config.mock_calls
            )
            == 3
        )

        mock_overseerr_client_needs_change.set_webhook_notification_config.assert_not_called()

        assert menuai.config_entries.async_entries(DOMAIN)
        fake_create_cloudhook.assert_not_called()


async def test_removing_entry_with_cloud_unavailable(
    menuai: menuai,
    mock_cloudhook_config_entry: MockConfigEntry,
    mock_overseerr_client: AsyncMock,
) -> None:
    """Test handling cloud unavailable when deleting entry."""

    await mock_cloud(menuai)
    await menuai.async_block_till_done()

    with (
        patch("menuai.components.cloud.async_is_logged_in", return_value=True),
        patch("menuai.components.cloud.async_is_connected", return_value=True),
        patch.object(cloud, "async_active_subscription", return_value=True),
        patch(
            "menuai.components.cloud.async_create_cloudhook",
            return_value="https://hooks.nabu.casa/ABCD",
        ),
        patch(
            "menuai.helpers.config_entry_oauth2_flow.async_get_config_entry_implementation",
        ),
        patch(
            "menuai.components.cloud.async_delete_cloudhook",
            side_effect=CloudNotAvailable(),
        ),
    ):
        await setup_integration(menuai, mock_cloudhook_config_entry)

        assert cloud.async_active_subscription(menuai) is True

        await menuai.async_block_till_done()
        assert menuai.config_entries.async_entries(DOMAIN)

        for config_entry in menuai.config_entries.async_entries(DOMAIN):
            await menuai.config_entries.async_remove(config_entry.entry_id)

        await menuai.async_block_till_done()
        assert not menuai.config_entries.async_entries(DOMAIN)
