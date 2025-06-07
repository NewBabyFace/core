"""Tests for the Withings component."""

from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, patch
from urllib.parse import urlparse

from aiohttp import ClientConnectionError
from aiohttp.hdrs import METH_HEAD
from aiowithings import (
    NotificationCategory,
    WithingsAuthenticationFailedError,
    WithingsConnectionError,
    WithingsUnauthorizedError,
)
from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai import config_entries
from menuai.components import cloud
from menuai.components.cloud import CloudNotAvailable
from menuai.components.webhook import async_generate_url
from menuai.components.withings.const import DOMAIN
from menuai.const import CONF_WEBHOOK_ID
from menuai.core import menuai
from menuai.helpers import device_registry as dr
from menuai.util import dt as dt_util

from . import call_webhook, prepare_webhook_setup, setup_integration
from .conftest import USER_ID, WEBHOOK_ID

from tests.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_cloud_connection_status,
)
from tests.components.cloud import mock_cloud
from tests.typing import ClientSessionGenerator


async def test_data_manager_webhook_subscription(
    menuai: menuai,
    withings: AsyncMock,
    webhook_config_entry: MockConfigEntry,
) -> None:
    """Test data manager webhook subscriptions."""
    await setup_integration(menuai, webhook_config_entry)
    await menuai.async_block_till_done()
    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=1))
    await menuai.async_block_till_done()

    assert withings.subscribe_notification.call_count == 6

    webhook_url = "https://example.com/api/webhook/55a7335ea8dee830eed4ef8f84cda8f6d80b83af0847dc74032e86120bffed5e"

    withings.subscribe_notification.assert_any_call(
        webhook_url, NotificationCategory.WEIGHT
    )
    withings.subscribe_notification.assert_any_call(
        webhook_url, NotificationCategory.PRESSURE
    )
    withings.subscribe_notification.assert_any_call(
        webhook_url, NotificationCategory.ACTIVITY
    )
    withings.subscribe_notification.assert_any_call(
        webhook_url, NotificationCategory.SLEEP
    )

    withings.revoke_notification_configurations.assert_any_call(
        webhook_url, NotificationCategory.IN_BED
    )
    withings.revoke_notification_configurations.assert_any_call(
        webhook_url, NotificationCategory.OUT_BED
    )


async def test_webhook_subscription_polling_config(
    menuai: menuai,
    withings: AsyncMock,
    polling_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test webhook subscriptions not run when polling."""
    await setup_integration(menuai, polling_config_entry, False)
    await menuai.async_block_till_done()
    freezer.tick(timedelta(seconds=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert withings.revoke_notification_configurations.call_count == 0
    assert withings.subscribe_notification.call_count == 0
    assert withings.list_notification_configurations.call_count == 0


async def test_head_request(
    menuai: menuai,
    withings: AsyncMock,
    webhook_config_entry: MockConfigEntry,
    menuai_client_no_auth: ClientSessionGenerator,
) -> None:
    """Test we handle head requests Withings sends."""
    await setup_integration(menuai, webhook_config_entry)
    client = await menuai_client_no_auth()
    webhook_url = async_generate_url(menuai, WEBHOOK_ID)

    response = await client.request(
        method=METH_HEAD,
        path=urlparse(webhook_url).path,
    )
    assert response.status == 200


async def test_webhooks_request_data(
    menuai: menuai,
    withings: AsyncMock,
    webhook_config_entry: MockConfigEntry,
    menuai_client_no_auth: ClientSessionGenerator,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test calling a webhook requests data."""
    await setup_integration(menuai, webhook_config_entry)
    await prepare_webhook_setup(menuai, freezer)

    client = await menuai_client_no_auth()

    assert withings.get_measurement_since.call_count == 0
    assert withings.get_measurement_in_period.call_count == 1

    await call_webhook(
        menuai,
        WEBHOOK_ID,
        {"userid": USER_ID, "appli": NotificationCategory.WEIGHT},
        client,
    )
    assert withings.get_measurement_since.call_count == 1
    assert withings.get_measurement_in_period.call_count == 1


@pytest.mark.parametrize(
    "error",
    [
        WithingsUnauthorizedError(401),
        WithingsAuthenticationFailedError(500),
    ],
)
async def test_triggering_reauth(
    menuai: menuai,
    withings: AsyncMock,
    polling_config_entry: MockConfigEntry,
    error: Exception,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test triggering reauth."""
    await setup_integration(menuai, polling_config_entry, False)

    withings.get_measurement_since.side_effect = error
    freezer.tick(timedelta(minutes=10))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    flows = menuai.config_entries.flow.async_progress()

    assert len(flows) == 1
    flow = flows[0]
    assert flow["step_id"] == "reauth_confirm"
    assert flow["handler"] == DOMAIN
    assert flow["context"]["source"] == config_entries.SOURCE_REAUTH


@pytest.mark.parametrize(
    ("config_entry"),
    [
        MockConfigEntry(
            domain=DOMAIN,
            unique_id="123",
            data={
                "token": {"userid": 123},
                "profile": "henk",
                "use_webhook": False,
                "webhook_id": "3290798afaebd28519c4883d3d411c7197572e0cc9b8d507471f59a700a61a55",
            },
        ),
        MockConfigEntry(
            domain=DOMAIN,
            unique_id="123",
            data={
                "token": {"userid": 123},
                "profile": "henk",
                "use_webhook": False,
            },
        ),
    ],
)
async def test_config_flow_upgrade(
    menuai: menuai, config_entry: MockConfigEntry
) -> None:
    """Test config flow upgrade."""
    config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    entry = menuai.config_entries.async_get_entry(config_entry.entry_id)

    assert entry.unique_id == "123"
    assert entry.data["token"]["userid"] == 123
    assert CONF_WEBHOOK_ID in entry.data


async def test_setup_with_cloudhook(
    menuai: menuai, cloudhook_config_entry: MockConfigEntry, withings: AsyncMock
) -> None:
    """Test if set up with active cloud subscription and cloud hook."""

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
            "menuai.helpers.config_entry_oauth2_flow.async_get_config_entry_implementation",
        ),
        patch(
            "menuai.components.cloud.async_delete_cloudhook"
        ) as fake_delete_cloudhook,
        patch("menuai.components.withings.webhook_generate_url"),
    ):
        await setup_integration(menuai, cloudhook_config_entry)

        assert cloud.async_active_subscription(menuai) is True

        assert (
            menuai.config_entries.async_entries(DOMAIN)[0].data["cloudhook_url"]
            == "https://hooks.nabu.casa/ABCD"
        )

        await menuai.async_block_till_done()
        assert menuai.config_entries.async_entries(DOMAIN)
        fake_create_cloudhook.assert_not_called()

        for config_entry in menuai.config_entries.async_entries(DOMAIN):
            await menuai.config_entries.async_remove(config_entry.entry_id)
            fake_delete_cloudhook.assert_called_once()

        await menuai.async_block_till_done()
        assert not menuai.config_entries.async_entries(DOMAIN)


async def test_removing_entry_with_cloud_unavailable(
    menuai: menuai, cloudhook_config_entry: MockConfigEntry, withings: AsyncMock
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
        patch(
            "menuai.components.withings.webhook_generate_url",
        ),
    ):
        await setup_integration(menuai, cloudhook_config_entry)

        assert cloud.async_active_subscription(menuai) is True

        await menuai.async_block_till_done()
        assert menuai.config_entries.async_entries(DOMAIN)

        for config_entry in menuai.config_entries.async_entries(DOMAIN):
            await menuai.config_entries.async_remove(config_entry.entry_id)

        await menuai.async_block_till_done()
        assert not menuai.config_entries.async_entries(DOMAIN)


async def test_setup_with_cloud(
    menuai: menuai,
    webhook_config_entry: MockConfigEntry,
    withings: AsyncMock,
    freezer: FrozenDateTimeFactory,
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
            "menuai.components.withings.async_get_config_entry_implementation",
        ),
        patch(
            "menuai.components.cloud.async_delete_cloudhook"
        ) as fake_delete_cloudhook,
        patch("menuai.components.withings.webhook_generate_url"),
    ):
        await setup_integration(menuai, webhook_config_entry)
        await prepare_webhook_setup(menuai, freezer)

        assert cloud.async_active_subscription(menuai) is True
        assert cloud.async_is_connected(menuai) is True
        fake_create_cloudhook.assert_called_once()
        fake_delete_cloudhook.assert_called_once()

        assert (
            menuai.config_entries.async_entries("withings")[0].data["cloudhook_url"]
            == "https://hooks.nabu.casa/ABCD"
        )

        await menuai.async_block_till_done()
        assert menuai.config_entries.async_entries(DOMAIN)

        for config_entry in menuai.config_entries.async_entries("withings"):
            await menuai.config_entries.async_remove(config_entry.entry_id)
            assert fake_delete_cloudhook.call_count == 2

        await menuai.async_block_till_done()
        assert not menuai.config_entries.async_entries(DOMAIN)


@pytest.mark.parametrize("url", ["http://example.com", "https://example.com:444"])
async def test_setup_no_webhook(
    menuai: menuai,
    webhook_config_entry: MockConfigEntry,
    withings: AsyncMock,
    caplog: pytest.LogCaptureFixture,
    freezer: FrozenDateTimeFactory,
    url: str,
) -> None:
    """Test if set up with cloud link and without https."""
    menuai.config.components.add("cloud")
    with (
        patch(
            "menuai.helpers.network.get_url",
            return_value="http://example.nabu.casa",
        ),
        patch(
            "menuai.helpers.config_entry_oauth2_flow.async_get_config_entry_implementation",
        ),
        patch(
            "menuai.components.withings.webhook_generate_url"
        ) as mock_async_generate_url,
    ):
        mock_async_generate_url.return_value = url
        await setup_integration(menuai, webhook_config_entry)
        await prepare_webhook_setup(menuai, freezer)

        await menuai.async_block_till_done()
        mock_async_generate_url.assert_called_once()

    assert "https and port 443 is required to register the webhook" in caplog.text


async def test_cloud_disconnect(
    menuai: menuai,
    withings: AsyncMock,
    webhook_config_entry: MockConfigEntry,
    menuai_client_no_auth: ClientSessionGenerator,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test disconnecting from the cloud."""
    await mock_cloud(menuai)
    await menuai.async_block_till_done()

    with (
        patch("menuai.components.cloud.async_is_logged_in", return_value=True),
        patch.object(cloud, "async_is_connected", return_value=True),
        patch.object(cloud, "async_active_subscription", return_value=True),
        patch(
            "menuai.components.cloud.async_create_cloudhook",
            return_value="https://hooks.nabu.casa/ABCD",
        ),
        patch(
            "menuai.components.withings.async_get_config_entry_implementation",
        ),
        patch(
            "menuai.components.cloud.async_delete_cloudhook",
        ),
        patch(
            "menuai.components.withings.webhook_generate_url",
        ),
    ):
        await setup_integration(menuai, webhook_config_entry)
        await prepare_webhook_setup(menuai, freezer)

        assert cloud.async_active_subscription(menuai) is True
        assert cloud.async_is_connected(menuai) is True

        await menuai.async_block_till_done()

        withings.list_notification_configurations.return_value = []

        assert withings.subscribe_notification.call_count == 6

        async_mock_cloud_connection_status(menuai, False)
        await menuai.async_block_till_done()

        assert withings.revoke_notification_configurations.call_count == 3

        async_mock_cloud_connection_status(menuai, True)
        await menuai.async_block_till_done()

        assert withings.subscribe_notification.call_count == 12


async def test_internet_disconnect(
    menuai: menuai,
    withings: AsyncMock,
    webhook_config_entry: MockConfigEntry,
    menuai_client_no_auth: ClientSessionGenerator,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test we can recover from internet disconnects."""
    await mock_cloud(menuai)
    await menuai.async_block_till_done()

    with (
        patch("menuai.components.cloud.async_is_logged_in", return_value=True),
        patch.object(cloud, "async_is_connected", return_value=True),
        patch.object(cloud, "async_active_subscription", return_value=True),
        patch(
            "menuai.components.cloud.async_create_cloudhook",
            return_value="https://hooks.nabu.casa/ABCD",
        ),
        patch(
            "menuai.components.withings.async_get_config_entry_implementation",
        ),
        patch(
            "menuai.components.cloud.async_delete_cloudhook",
        ),
        patch(
            "menuai.components.withings.webhook_generate_url",
        ),
    ):
        await setup_integration(menuai, webhook_config_entry)
        await prepare_webhook_setup(menuai, freezer)

        assert cloud.async_active_subscription(menuai) is True
        assert cloud.async_is_connected(menuai) is True
        assert withings.revoke_notification_configurations.call_count == 3
        assert withings.subscribe_notification.call_count == 6

        await menuai.async_block_till_done()

        withings.list_notification_configurations.side_effect = ClientConnectionError

        async_mock_cloud_connection_status(menuai, False)
        await menuai.async_block_till_done()

        assert withings.revoke_notification_configurations.call_count == 3

        async_mock_cloud_connection_status(menuai, True)
        await menuai.async_block_till_done()

        assert withings.subscribe_notification.call_count == 12


async def test_cloud_disconnect_retry(
    menuai: menuai,
    withings: AsyncMock,
    webhook_config_entry: MockConfigEntry,
    menuai_client_no_auth: ClientSessionGenerator,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test we retry to create webhook connection again after cloud disconnects."""
    await mock_cloud(menuai)
    await menuai.async_block_till_done()

    with (
        patch("menuai.components.cloud.async_is_logged_in", return_value=True),
        patch.object(cloud, "async_is_connected", return_value=True),
        patch.object(
            cloud, "async_active_subscription", return_value=True
        ) as mock_async_active_subscription,
        patch(
            "menuai.components.cloud.async_create_cloudhook",
            return_value="https://hooks.nabu.casa/ABCD",
        ),
        patch(
            "menuai.components.withings.async_get_config_entry_implementation",
        ),
        patch(
            "menuai.components.cloud.async_delete_cloudhook",
        ),
        patch(
            "menuai.components.withings.webhook_generate_url",
        ),
    ):
        await setup_integration(menuai, webhook_config_entry)
        await prepare_webhook_setup(menuai, freezer)

        assert cloud.async_active_subscription(menuai) is True
        assert cloud.async_is_connected(menuai) is True
        assert mock_async_active_subscription.call_count == 3

        await menuai.async_block_till_done()

        async_mock_cloud_connection_status(menuai, False)
        await menuai.async_block_till_done()

        assert mock_async_active_subscription.call_count == 3

        freezer.tick(timedelta(seconds=30))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()

        assert mock_async_active_subscription.call_count == 4


async def test_internet_timeout_then_restore(
    menuai: menuai,
    withings: AsyncMock,
    webhook_config_entry: MockConfigEntry,
    menuai_client_no_auth: ClientSessionGenerator,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test we can recover from internet disconnects."""
    await mock_cloud(menuai)
    await menuai.async_block_till_done()

    with (
        patch("menuai.components.cloud.async_is_logged_in", return_value=True),
        patch.object(cloud, "async_is_connected", return_value=True),
        patch.object(cloud, "async_active_subscription", return_value=True),
        patch(
            "menuai.components.cloud.async_create_cloudhook",
            return_value="https://hooks.nabu.casa/ABCD",
        ),
        patch(
            "menuai.components.withings.async_get_config_entry_implementation",
        ),
        patch(
            "menuai.components.cloud.async_delete_cloudhook",
        ),
        patch(
            "menuai.components.withings.webhook_generate_url",
        ),
    ):
        await setup_integration(menuai, webhook_config_entry)
        await prepare_webhook_setup(menuai, freezer)

        assert cloud.async_active_subscription(menuai) is True
        assert cloud.async_is_connected(menuai) is True
        assert withings.revoke_notification_configurations.call_count == 3
        assert withings.subscribe_notification.call_count == 6

        await menuai.async_block_till_done()

        withings.list_notification_configurations.side_effect = WithingsConnectionError

        async_mock_cloud_connection_status(menuai, False)
        await menuai.async_block_till_done()

        assert withings.revoke_notification_configurations.call_count == 3
        withings.list_notification_configurations.side_effect = None

        async_mock_cloud_connection_status(menuai, True)
        await menuai.async_block_till_done()

        assert withings.subscribe_notification.call_count == 12


@pytest.mark.parametrize(
    ("body", "expected_code"),
    [
        ({"userid": 0, "appli": NotificationCategory.WEIGHT.value}, 0),  # Success
        ({"userid": None, "appli": 1}, 0),  # Success, we ignore the user_id.
        ({}, 12),  # No request body.
        ({"userid": "GG"}, 20),  # appli not provided.
        ({"userid": 0}, 20),  # appli not provided.
        (
            {"userid": 11, "appli": NotificationCategory.WEIGHT.value},
            0,
        ),  # Success, we ignore the user_id
    ],
)
@pytest.mark.usefixtures("current_request_with_host")
async def test_webhook_post(
    menuai: menuai,
    withings: AsyncMock,
    webhook_config_entry: MockConfigEntry,
    menuai_client_no_auth: ClientSessionGenerator,
    body: dict[str, Any],
    expected_code: int,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test webhook callback."""
    await setup_integration(menuai, webhook_config_entry)
    await prepare_webhook_setup(menuai, freezer)
    client = await menuai_client_no_auth()
    webhook_url = async_generate_url(menuai, WEBHOOK_ID)

    resp = await client.post(urlparse(webhook_url).path, data=body)

    # Wait for remaining tasks to complete.
    await menuai.async_block_till_done()

    data = await resp.json()
    resp.close()

    assert data["code"] == expected_code


async def test_devices(
    menuai: menuai,
    withings: AsyncMock,
    webhook_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test devices."""
    await setup_integration(menuai, webhook_config_entry)

    await menuai.async_block_till_done()

    for device_id in ("12345", "f998be4b9ccc9e136fd8cd8e8e344c31ec3b271d"):
        device = device_registry.async_get_device({(DOMAIN, device_id)})
        assert device is not None
        assert device == snapshot(name=device_id)
