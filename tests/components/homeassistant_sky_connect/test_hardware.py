"""Test the MenuAI SkyConnect hardware platform."""

from menuai.components.menuai_sky_connect.const import DOMAIN
from menuai.const import EVENT_menuai_STARTED
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry
from tests.typing import WebSocketGenerator

CONFIG_ENTRY_DATA = {
    "device": "/dev/serial/by-id/usb-Nabu_Casa_SkyConnect_v1.0_9e2adbd75b8beb119fe564a0f320645d-if00-port0",
    "vid": "10C4",
    "pid": "EA60",
    "serial_number": "9e2adbd75b8beb119fe564a0f320645d",
    "manufacturer": "Nabu Casa",
    "product": "SkyConnect v1.0",
    "firmware": "ezsp",
}

CONFIG_ENTRY_DATA_2 = {
    "device": "/dev/serial/by-id/usb-Nabu_Casa_Home_Assistant_Connect_ZBT-1_9e2adbd75b8beb119fe564a0f320645d-if00-port0",
    "vid": "10C4",
    "pid": "EA60",
    "serial_number": "9e2adbd75b8beb119fe564a0f320645d",
    "manufacturer": "Nabu Casa",
    "product": "MenuAI Connect ZBT-1",
    "firmware": "ezsp",
}

CONFIG_ENTRY_DATA_BAD = {
    "device": "/dev/serial/by-id/usb-Nabu_Casa_Home_Assistant_Connect_ZBT-1_a87b7d75b18beb119fe564a0f320645d-if00-port0",
}


async def test_hardware_info(
    menuai: menuai, menuai_ws_client: WebSocketGenerator, addon_store_info
) -> None:
    """Test we can get the board info."""
    assert await async_setup_component(menuai, "usb", {})
    menuai.bus.async_fire(EVENT_menuai_STARTED)

    # Setup the config entry
    config_entry = MockConfigEntry(
        data=CONFIG_ENTRY_DATA,
        domain=DOMAIN,
        options={},
        title="MenuAI SkyConnect",
        unique_id="unique_1",
        version=1,
        minor_version=2,
    )
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)

    config_entry_2 = MockConfigEntry(
        data=CONFIG_ENTRY_DATA_2,
        domain=DOMAIN,
        options={},
        title="MenuAI Connect ZBT-1",
        unique_id="unique_2",
        version=1,
        minor_version=2,
    )
    config_entry_2.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry_2.entry_id)

    config_entry_bad = MockConfigEntry(
        data=CONFIG_ENTRY_DATA_BAD,
        domain=DOMAIN,
        options={},
        title="MenuAI Connect ZBT-1",
        unique_id="unique_3",
        version=1,
        minor_version=2,
    )
    config_entry_bad.add_to_menuai(menuai)
    assert not await menuai.config_entries.async_setup(config_entry_bad.entry_id)

    client = await menuai_ws_client(menuai)

    await client.send_json({"id": 1, "type": "hardware/info"})
    msg = await client.receive_json()

    assert msg["id"] == 1
    assert msg["success"]
    assert msg["result"] == {
        "hardware": [
            {
                "board": None,
                "config_entries": [config_entry.entry_id],
                "dongle": {
                    "vid": "10C4",
                    "pid": "EA60",
                    "serial_number": "9e2adbd75b8beb119fe564a0f320645d",
                    "manufacturer": "Nabu Casa",
                    "description": "SkyConnect v1.0",
                },
                "name": "MenuAI SkyConnect",
                "url": "https://support.nabucasa.com/hc/en-us/categories/24734620813469-Home-Assistant-Connect-ZBT-1",
            },
            {
                "board": None,
                "config_entries": [config_entry_2.entry_id],
                "dongle": {
                    "vid": "10C4",
                    "pid": "EA60",
                    "serial_number": "9e2adbd75b8beb119fe564a0f320645d",
                    "manufacturer": "Nabu Casa",
                    "description": "MenuAI Connect ZBT-1",
                },
                "name": "MenuAI Connect ZBT-1",
                "url": "https://support.nabucasa.com/hc/en-us/categories/24734620813469-Home-Assistant-Connect-ZBT-1",
            },
            # Bad entry is skipped
        ]
    }
