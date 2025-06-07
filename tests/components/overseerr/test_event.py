"""Tests for the Overseerr event platform."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
from future.backports.datetime import timedelta
import pytest
from python_overseerr import OverseerrConnectionError
from syrupy.assertion import SnapshotAssertion

from menuai.components.overseerr import DOMAIN
from menuai.const import STATE_UNAVAILABLE, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import call_webhook, setup_integration

from tests.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_load_json_object_fixture,
    snapshot_platform,
)
from tests.typing import ClientSessionGenerator


@pytest.mark.freeze_time("2023-10-21")
async def test_entities(
    menuai: menuai,
    mock_overseerr_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    menuai_client_no_auth: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    with patch("menuai.components.overseerr.PLATFORMS", [Platform.EVENT]):
        await setup_integration(menuai, mock_config_entry)

    client = await menuai_client_no_auth()

    await call_webhook(
        menuai,
        await async_load_json_object_fixture(
            menuai, "webhook_request_automatically_approved.json", DOMAIN
        ),
        client,
    )
    await menuai.async_block_till_done()

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.freeze_time("2023-10-21")
async def test_event_does_not_write_state(
    menuai: menuai,
    mock_overseerr_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    menuai_client_no_auth: ClientSessionGenerator,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test event entities don't write state on coordinator update."""
    await setup_integration(menuai, mock_config_entry)

    client = await menuai_client_no_auth()

    await call_webhook(
        menuai,
        await async_load_json_object_fixture(
            menuai, "webhook_request_automatically_approved.json", DOMAIN
        ),
        client,
    )
    await menuai.async_block_till_done()

    assert menuai.states.get(
        "event.overseerr_last_media_event"
    ).last_reported == datetime(2023, 10, 21, 0, 0, 0, tzinfo=UTC)

    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert menuai.states.get(
        "event.overseerr_last_media_event"
    ).last_reported == datetime(2023, 10, 21, 0, 0, 0, tzinfo=UTC)


async def test_event_goes_unavailable(
    menuai: menuai,
    mock_overseerr_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test event entities go unavailable when we can't fetch data."""
    await setup_integration(menuai, mock_config_entry)

    assert (
        menuai.states.get("event.overseerr_last_media_event").state != STATE_UNAVAILABLE
    )

    mock_overseerr_client.get_request_count.side_effect = OverseerrConnectionError(
        "Boom"
    )

    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert (
        menuai.states.get("event.overseerr_last_media_event").state == STATE_UNAVAILABLE
    )


async def test_not_push_based(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_overseerr_client_needs_change: AsyncMock,
) -> None:
    """Test event entities aren't created if not push based."""

    mock_overseerr_client_needs_change.test_webhook_notification_config.return_value = (
        False
    )

    await setup_integration(menuai, mock_config_entry)

    assert menuai.states.get("event.overseerr_last_media_event") is None


async def test_cant_fetch_webhook_config(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_overseerr_client: AsyncMock,
) -> None:
    """Test event entities aren't created if not push based."""

    mock_overseerr_client.get_webhook_notification_config.side_effect = (
        OverseerrConnectionError("Boom")
    )

    await setup_integration(menuai, mock_config_entry)

    assert menuai.states.get("event.overseerr_last_media_event") is None


async def test_not_push_based_but_was_before(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_overseerr_client_needs_change: AsyncMock,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test event entities are created if push based in the past."""

    entity_registry.async_get_or_create(
        Platform.EVENT,
        DOMAIN,
        f"{mock_config_entry.entry_id}-media",
        suggested_object_id="overseerr_last_media_event",
        disabled_by=None,
    )

    mock_overseerr_client_needs_change.test_webhook_notification_config.return_value = (
        False
    )

    await setup_integration(menuai, mock_config_entry)

    assert menuai.states.get("event.overseerr_last_media_event") is not None

    assert (
        menuai.states.get("event.overseerr_last_media_event").state == STATE_UNAVAILABLE
    )
