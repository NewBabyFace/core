"""Test the Raspberry Pi hardware platform."""

from unittest.mock import patch

import pytest

from menuai.components.menuaiio import DOMAIN as menuaiIO_DOMAIN
from menuai.components.raspberry_pi.const import DOMAIN
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry, MockModule, mock_integration
from tests.typing import WebSocketGenerator


async def test_hardware_info(
    menuai: menuai, menuai_ws_client: WebSocketGenerator
) -> None:
    """Test we can get the board info."""
    mock_integration(menuai, MockModule("menuaiio"))
    await async_setup_component(menuai, menuaiIO_DOMAIN, {})
    await menuai.async_block_till_done()

    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={},
        title="Raspberry Pi",
    )
    config_entry.add_to_menuai(menuai)
    with patch(
        "menuai.components.raspberry_pi.get_os_info",
        return_value={"board": "rpi"},
    ):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    client = await menuai_ws_client(menuai)

    with patch(
        "menuai.components.raspberry_pi.hardware.get_os_info",
        return_value={"board": "rpi"},
    ):
        await client.send_json({"id": 1, "type": "hardware/info"})
        msg = await client.receive_json()

    assert msg["id"] == 1
    assert msg["success"]
    assert msg["result"] == {
        "hardware": [
            {
                "board": {
                    "menuaiio_board_id": "rpi",
                    "manufacturer": "raspberry_pi",
                    "model": "1",
                    "revision": None,
                },
                "config_entries": [config_entry.entry_id],
                "dongle": None,
                "name": "Raspberry Pi",
                "url": None,
            }
        ]
    }


@pytest.mark.parametrize("os_info", [None, {"board": None}, {"board": "other"}])
async def test_hardware_info_fail(
    menuai: menuai, menuai_ws_client: WebSocketGenerator, os_info
) -> None:
    """Test async_info raises if os_info is not as expected."""
    mock_integration(menuai, MockModule("menuaiio"))
    await async_setup_component(menuai, menuaiIO_DOMAIN, {})
    await menuai.async_block_till_done()

    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={},
        title="Raspberry Pi",
    )
    config_entry.add_to_menuai(menuai)
    with patch(
        "menuai.components.raspberry_pi.get_os_info",
        return_value={"board": "rpi"},
    ):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    client = await menuai_ws_client(menuai)

    with patch(
        "menuai.components.raspberry_pi.hardware.get_os_info",
        return_value=os_info,
    ):
        await client.send_json({"id": 1, "type": "hardware/info"})
        msg = await client.receive_json()

    assert msg["id"] == 1
    assert msg["success"]
    assert msg["result"] == {"hardware": []}
