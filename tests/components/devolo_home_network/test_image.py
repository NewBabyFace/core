"""Tests for the devolo Home Network images."""

from http import HTTPStatus
from unittest.mock import AsyncMock

from devolo_plc_api.exceptions.device import DeviceUnavailable
from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.devolo_home_network.const import SHORT_UPDATE_INTERVAL
from menuai.components.image import DOMAIN as PLATFORM
from menuai.config_entries import ConfigEntryState
from menuai.const import STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.util import dt as dt_util

from . import configure_integration
from .const import GUEST_WIFI_CHANGED
from .mock import MockDevice

from tests.common import async_fire_time_changed
from tests.typing import ClientSessionGenerator


@pytest.mark.usefixtures("mock_device")
async def test_image_setup(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test default setup of the image component."""
    entry = configure_integration(menuai)
    device_name = entry.title.replace(" ", "_").lower()
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    assert not entity_registry.async_get(
        f"{PLATFORM}.{device_name}_guest_wi_fi_credentials_as_qr_code"
    ).disabled


@pytest.mark.freeze_time("2023-01-13 12:00:00+00:00")
async def test_guest_wifi_qr(
    menuai: menuai,
    mock_device: MockDevice,
    entity_registry: er.EntityRegistry,
    menuai_client: ClientSessionGenerator,
    freezer: FrozenDateTimeFactory,
    snapshot: SnapshotAssertion,
) -> None:
    """Test showing a QR code of the guest wifi credentials."""
    entry = configure_integration(menuai)
    device_name = entry.title.replace(" ", "_").lower()
    state_key = f"{PLATFORM}.{device_name}_guest_wi_fi_credentials_as_qr_code"

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    state = menuai.states.get(state_key)
    assert state.name == "Mock Title Guest Wi-Fi credentials as QR code"
    assert state.state == dt_util.utcnow().isoformat()
    assert entity_registry.async_get(state_key) == snapshot

    client = await menuai_client()
    resp = await client.get(f"/api/image_proxy/{state_key}")
    assert resp.status == HTTPStatus.OK
    body = await resp.read()
    assert body == snapshot

    # Emulate device failure
    mock_device.device.async_get_wifi_guest_access.side_effect = DeviceUnavailable()
    freezer.tick(SHORT_UPDATE_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    state = menuai.states.get(state_key)
    assert state is not None
    assert state.state == STATE_UNAVAILABLE

    # Emulate state change
    mock_device.device.async_get_wifi_guest_access = AsyncMock(
        return_value=GUEST_WIFI_CHANGED
    )
    freezer.tick(SHORT_UPDATE_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    state = menuai.states.get(state_key)
    assert state is not None
    assert state.state == dt_util.utcnow().isoformat()

    client = await menuai_client()
    resp = await client.get(f"/api/image_proxy/{state_key}")
    assert resp.status == HTTPStatus.OK
    assert await resp.read() != body
