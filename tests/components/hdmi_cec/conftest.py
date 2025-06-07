"""Tests for the HDMI-CEC component."""

from collections.abc import Callable, Coroutine, Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from menuai.components.hdmi_cec import DOMAIN
from menuai.const import EVENT_menuai_START
from menuai.core import menuai
from menuai.setup import async_setup_component

type CecEntityCreator = Callable[..., Coroutine[Any, Any, None]]
type HDMINetworkCreator = Callable[..., Coroutine[Any, Any, MagicMock]]


@pytest.fixture(name="mock_cec_adapter", autouse=True)
def mock_cec_adapter_fixture() -> Generator[MagicMock]:
    """Mock CecAdapter.

    Always mocked as it imports the `cec` library which is part of `libcec`.
    """
    with patch(
        "menuai.components.hdmi_cec.CecAdapter", autospec=True
    ) as mock_cec_adapter:
        yield mock_cec_adapter


@pytest.fixture(name="mock_hdmi_network")
def mock_hdmi_network_fixture() -> Generator[MagicMock]:
    """Mock HDMINetwork."""
    with patch(
        "menuai.components.hdmi_cec.HDMINetwork", autospec=True
    ) as mock_hdmi_network:
        yield mock_hdmi_network


@pytest.fixture
def create_hdmi_network(
    menuai: menuai, mock_hdmi_network: MagicMock
) -> HDMINetworkCreator:
    """Create an initialized mock hdmi_network."""

    async def hdmi_network(config=None):
        if not config:
            config = {}
        await async_setup_component(menuai, DOMAIN, {DOMAIN: config})

        mock_hdmi_network_instance = mock_hdmi_network.return_value

        menuai.bus.async_fire(EVENT_menuai_START)
        await menuai.async_block_till_done()
        return mock_hdmi_network_instance

    return hdmi_network


@pytest.fixture
def create_cec_entity(menuai: menuai) -> CecEntityCreator:
    """Create a CecEntity."""

    async def cec_entity(hdmi_network, device):
        new_device_callback = hdmi_network.set_new_device_callback.call_args.args[0]
        new_device_callback(device)
        await menuai.async_block_till_done()

    return cec_entity
