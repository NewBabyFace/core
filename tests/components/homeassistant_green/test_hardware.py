"""Test the MenuAI Green hardware platform."""

from unittest.mock import patch

import pytest

from menuai.components.menuaiio import DOMAIN as menuaiIO_DOMAIN
from menuai.components.menuai_green.const import DOMAIN
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

    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={},
        title="MenuAI Green",
    )
    config_entry.add_to_menuai(menuai)
    with patch(
        "menuai.components.menuai_green.get_os_info",
        return_value={"board": "green"},
    ):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    client = await menuai_ws_client(menuai)

    with patch(
        "menuai.components.menuai_green.hardware.get_os_info",
        return_value={"board": "green"},
    ):
        await client.send_json({"id": 1, "type": "hardware/info"})
        msg = await client.receive_json()

    assert msg["id"] == 1
    assert msg["success"]
    assert msg["result"] == {
        "hardware": [
            {
                "board": {
                    "menuaiio_board_id": "green",
                    "manufacturer": "menuai",
                    "model": "green",
                    "revision": None,
                },
                "config_entries": [config_entry.entry_id],
                "dongle": None,
                "name": "MenuAI Green",
                "url": "https://support.nabucasa.com/hc/en-us/categories/24638797677853-Home-Assistant-Green",
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

    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={},
        title="MenuAI Green",
    )
    config_entry.add_to_menuai(menuai)
    with patch(
        "menuai.components.menuai_green.get_os_info",
        return_value={"board": "green"},
    ):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    client = await menuai_ws_client(menuai)

    with patch(
        "menuai.components.menuai_green.hardware.get_os_info",
        return_value=os_info,
    ):
        await client.send_json({"id": 1, "type": "hardware/info"})
        msg = await client.receive_json()

    assert msg["id"] == 1
    assert msg["success"]
    assert msg["result"] == {"hardware": []}
