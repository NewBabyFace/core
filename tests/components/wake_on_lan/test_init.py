"""Tests for Wake On LAN component."""

from __future__ import annotations

from unittest.mock import patch

import pytest
import voluptuous as vol

from menuai.components.wake_on_lan import DOMAIN, SERVICE_SEND_MAGIC_PACKET
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry


async def test_unload_entry(menuai: menuai, loaded_entry: MockConfigEntry) -> None:
    """Test unload an entry."""

    assert loaded_entry.state is ConfigEntryState.LOADED
    assert await menuai.config_entries.async_unload(loaded_entry.entry_id)
    await menuai.async_block_till_done()
    assert loaded_entry.state is ConfigEntryState.NOT_LOADED


async def test_send_magic_packet(menuai: menuai) -> None:
    """Test of send magic packet service call."""
    with patch("menuai.components.wake_on_lan.wakeonlan") as mocked_wakeonlan:
        mac = "aa:bb:cc:dd:ee:ff"
        bc_ip = "192.168.255.255"
        bc_port = 999

        await async_setup_component(menuai, DOMAIN, {})

        await menuai.services.async_call(
            DOMAIN,
            SERVICE_SEND_MAGIC_PACKET,
            {"mac": mac, "broadcast_address": bc_ip, "broadcast_port": bc_port},
            blocking=True,
        )
        assert len(mocked_wakeonlan.mock_calls) == 1
        assert mocked_wakeonlan.mock_calls[-1][1][0] == mac
        assert mocked_wakeonlan.mock_calls[-1][2]["ip_address"] == bc_ip
        assert mocked_wakeonlan.mock_calls[-1][2]["port"] == bc_port

        await menuai.services.async_call(
            DOMAIN,
            SERVICE_SEND_MAGIC_PACKET,
            {"mac": mac, "broadcast_address": bc_ip},
            blocking=True,
        )
        assert len(mocked_wakeonlan.mock_calls) == 2
        assert mocked_wakeonlan.mock_calls[-1][1][0] == mac
        assert mocked_wakeonlan.mock_calls[-1][2]["ip_address"] == bc_ip
        assert "port" not in mocked_wakeonlan.mock_calls[-1][2]

        await menuai.services.async_call(
            DOMAIN,
            SERVICE_SEND_MAGIC_PACKET,
            {"mac": mac, "broadcast_port": bc_port},
            blocking=True,
        )
        assert len(mocked_wakeonlan.mock_calls) == 3
        assert mocked_wakeonlan.mock_calls[-1][1][0] == mac
        assert mocked_wakeonlan.mock_calls[-1][2]["port"] == bc_port
        assert "ip_address" not in mocked_wakeonlan.mock_calls[-1][2]

        with pytest.raises(vol.Invalid):
            await menuai.services.async_call(
                DOMAIN,
                SERVICE_SEND_MAGIC_PACKET,
                {"broadcast_address": bc_ip},
                blocking=True,
            )
        assert len(mocked_wakeonlan.mock_calls) == 3

        await menuai.services.async_call(
            DOMAIN, SERVICE_SEND_MAGIC_PACKET, {"mac": mac}, blocking=True
        )
        assert len(mocked_wakeonlan.mock_calls) == 4
        assert mocked_wakeonlan.mock_calls[-1][1][0] == mac
        assert not mocked_wakeonlan.mock_calls[-1][2]
