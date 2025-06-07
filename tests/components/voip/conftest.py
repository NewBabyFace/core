"""Test helpers for VoIP integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest
from voip_utils import CallInfo
from voip_utils.sip import get_sip_endpoint

from menuai.components.voip import DOMAIN
from menuai.components.voip.devices import VoIPDevice, VoIPDevices
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry
from tests.components.tts.conftest import (
    mock_tts_cache_dir_fixture_autouse,  # noqa: F401
)


@pytest.fixture(autouse=True)
async def load_menuai(menuai: menuai) -> None:
    """Load the menuai integration."""
    assert await async_setup_component(menuai, "menuai", {})


@pytest.fixture
def config_entry(menuai: menuai) -> MockConfigEntry:
    """Create a config entry."""
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_menuai(menuai)
    return entry


@pytest.fixture
async def setup_voip(menuai: menuai, config_entry: MockConfigEntry) -> None:
    """Set up VoIP integration."""
    with patch(
        "menuai.components.voip._create_sip_server",
        return_value=(Mock(), AsyncMock()),
    ):
        assert await async_setup_component(menuai, DOMAIN, {})
        assert config_entry.state is ConfigEntryState.LOADED
        yield


@pytest.fixture
async def voip_devices(menuai: menuai, setup_voip: None) -> VoIPDevices:
    """Get VoIP devices object from a configured instance."""
    return menuai.data[DOMAIN].devices


@pytest.fixture
def call_info() -> CallInfo:
    """Fake call info."""
    return CallInfo(
        caller_endpoint=get_sip_endpoint("192.168.1.210", 5060),
        local_endpoint=get_sip_endpoint("192.168.1.10", 5060),
        caller_rtp_port=5004,
        server_ip="192.168.1.10",
        headers={
            "via": "SIP/2.0/UDP 192.168.1.210:5060;branch=z9hG4bK912387041;rport",
            "from": "<sip:IPCall@192.168.1.210:5060>;tag=1836983217",
            "to": "<sip:192.168.1.10:5060>",
            "call-id": "860888843-5060-9@BJC.BGI.B.CBA",
            "cseq": "80 INVITE",
            "contact": "<sip:IPCall@192.168.1.210:5060>",
            "max-forwards": "70",
            "user-agent": "Grandstream HT801 1.0.17.5",
            "supported": "replaces, path, timer, eventlist",
            "allow": "INVITE, ACK, OPTIONS, CANCEL, BYE, SUBSCRIBE, NOTIFY, INFO, REFER, UPDATE",
            "content-type": "application/sdp",
            "accept": "application/sdp, application/dtmf-relay",
            "content-length": "480",
        },
    )


@pytest.fixture
async def voip_device(
    menuai: menuai, voip_devices: VoIPDevices, call_info: CallInfo
) -> VoIPDevice:
    """Get a VoIP device fixture."""
    device = voip_devices.async_get_or_create(call_info)
    # to make sure all platforms are set up
    await menuai.async_block_till_done()
    return device
