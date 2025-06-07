"""Common test tools."""

from __future__ import annotations

from collections.abc import Callable, Coroutine, Generator
from typing import Any
from unittest.mock import MagicMock, Mock, patch

from freezegun import freeze_time
import pytest
from RFXtrx import Connect, RFXtrxTransport

from menuai.components import rfxtrx
from menuai.components.rfxtrx import DOMAIN
from menuai.core import menuai
from menuai.util.dt import utcnow

from tests.common import MockConfigEntry, async_fire_time_changed
from tests.components.light.conftest import mock_light_profiles  # noqa: F401


def create_rfx_test_cfg(
    device="abcd",
    automatic_add=False,
    protocols=None,
    devices=None,
    host=None,
    port=None,
):
    """Create rfxtrx config entry data."""
    return {
        "device": device,
        "host": host,
        "port": port,
        "automatic_add": automatic_add,
        "protocols": protocols,
        "debug": False,
        "devices": devices or {},
    }


async def setup_rfx_test_cfg(
    menuai: menuai,
    device="abcd",
    automatic_add=False,
    devices: dict[str, dict] | None = None,
    protocols=None,
    host=None,
    port=None,
):
    """Construct a rfxtrx config entry."""
    entry_data = create_rfx_test_cfg(
        device=device,
        automatic_add=automatic_add,
        devices=devices,
        protocols=protocols,
        host=host,
        port=port,
    )
    mock_entry = MockConfigEntry(domain="rfxtrx", unique_id=DOMAIN, data=entry_data)
    mock_entry.supports_remove_device = True
    mock_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(mock_entry.entry_id)
    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()
    return mock_entry


@pytest.fixture(autouse=True)
def transport_mock() -> Generator[Mock]:
    """Fixture that make sure all transports are fake."""
    transport = Mock(spec=RFXtrxTransport)
    with (
        patch("RFXtrx.PySerialTransport", new=transport),
        patch("RFXtrx.PyNetworkTransport", transport),
    ):
        yield transport


@pytest.fixture(autouse=True)
def connect_mock() -> Generator[MagicMock]:
    """Fixture that make sure connect class is mocked."""
    with patch("RFXtrx.Connect") as connect:
        yield connect


@pytest.fixture(autouse=True, name="rfxtrx")
def rfxtrx_fixture(menuai: menuai, connect_mock: MagicMock) -> Mock:
    """Fixture that cleans up threads from integration."""

    rfx = Mock(spec=Connect)

    def _init(transport, event_callback=None, modes=None):
        rfx.event_callback = event_callback
        rfx.transport = transport
        return rfx

    connect_mock.side_effect = _init

    async def _signal_event(packet_id):
        event = rfxtrx.get_rfx_object(packet_id)
        await menuai.async_add_executor_job(
            rfx.event_callback,
            event,
        )

        await menuai.async_block_till_done()
        await menuai.async_block_till_done()
        return event

    rfx.signal = _signal_event

    return rfx


@pytest.fixture(name="rfxtrx_automatic")
async def rfxtrx_automatic_fixture(menuai: menuai, rfxtrx: Mock) -> Mock:
    """Fixture that starts up with automatic additions."""
    await setup_rfx_test_cfg(menuai, automatic_add=True, devices={})
    return rfxtrx


@pytest.fixture
def timestep(
    menuai: menuai,
) -> Generator[Callable[[int], Coroutine[Any, Any, None]]]:
    """Step system time forward."""

    with freeze_time(utcnow()) as frozen_time:

        async def delay(seconds: int) -> None:
            """Trigger delay in system."""
            frozen_time.tick(delta=seconds)
            async_fire_time_changed(menuai)
            await menuai.async_block_till_done()

        yield delay
