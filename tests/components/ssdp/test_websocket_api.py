"""The tests for the ssdp WebSocket API."""

import asyncio
from unittest.mock import ANY, AsyncMock, Mock, patch

from menuai.core import EVENT_menuai_STARTED, menuai

from . import _ssdp_headers, init_ssdp_component

from tests.test_util.aiohttp import AiohttpClientMocker
from tests.typing import WebSocketGenerator


@patch(
    "menuai.components.ssdp.async_get_ssdp",
    return_value={"mock-domain": [{"deviceType": "Paulus"}]},
)
async def test_subscribe_discovery(
    mock_get_ssdp: Mock,
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    mock_flow_init: AsyncMock,
    menuai_ws_client: WebSocketGenerator,
) -> None:
    """Test ssdp subscribe_discovery."""
    aioclient_mock.get(
        "http://1.1.1.1",
        text="""
<root>
  <device>
    <deviceType>Paulus</deviceType>
    <friendlyName>Bedroom TV</friendlyName>
  </device>
</root>
    """,
    )
    ssdp_listener = await init_ssdp_component(menuai)
    menuai.bus.async_fire(EVENT_menuai_STARTED)
    await menuai.async_block_till_done()

    mock_ssdp_search_response = _ssdp_headers(
        {
            "st": "mock-st",
            "location": "http://1.1.1.1",
            "usn": "uuid:mock-udn::mock-st",
            "_source": "search",
        }
    )
    ssdp_listener._on_search(mock_ssdp_search_response)
    await menuai.async_block_till_done(wait_background_tasks=True)

    client = await menuai_ws_client()
    await client.send_json(
        {
            "id": 1,
            "type": "ssdp/subscribe_discovery",
        }
    )
    async with asyncio.timeout(1):
        response = await client.receive_json()
    assert response["success"]

    async with asyncio.timeout(1):
        response = await client.receive_json()

    assert response["event"]["add"] == [
        {
            "ssdp_all_locations": ["http://1.1.1.1"],
            "ssdp_ext": None,
            "ssdp_headers": {
                "_source": "search",
                "_timestamp": ANY,
                "_udn": "uuid:mock-udn",
                "location": "http://1.1.1.1",
                "st": "mock-st",
                "usn": "uuid:mock-udn::mock-st",
            },
            "ssdp_location": "http://1.1.1.1",
            "ssdp_nt": None,
            "ssdp_server": None,
            "ssdp_st": "mock-st",
            "ssdp_udn": "uuid:mock-udn",
            "ssdp_usn": "uuid:mock-udn::mock-st",
            "upnp": {
                "UDN": "uuid:mock-udn",
                "deviceType": "Paulus",
                "friendlyName": "Bedroom TV",
            },
            "name": "Bedroom TV",
            "x_menuai_matching_domains": [],
        }
    ]

    mock_ssdp_advertisement = _ssdp_headers(
        {
            "location": "http://1.1.1.1",
            "usn": "uuid:mock-udn::mock-st",
            "nt": "upnp:rootdevice",
            "nts": "ssdp:alive",
            "_source": "advertisement",
        }
    )
    ssdp_listener._on_alive(mock_ssdp_advertisement)
    await menuai.async_block_till_done(wait_background_tasks=True)

    async with asyncio.timeout(1):
        response = await client.receive_json()

    assert response["event"]["add"] == [
        {
            "ssdp_all_locations": ["http://1.1.1.1"],
            "ssdp_ext": None,
            "ssdp_headers": {
                "_source": "advertisement",
                "_timestamp": ANY,
                "_udn": "uuid:mock-udn",
                "location": "http://1.1.1.1",
                "nt": "upnp:rootdevice",
                "nts": "ssdp:alive",
                "usn": "uuid:mock-udn::mock-st",
            },
            "ssdp_location": "http://1.1.1.1",
            "ssdp_nt": "upnp:rootdevice",
            "ssdp_server": None,
            "ssdp_st": "upnp:rootdevice",
            "ssdp_udn": "uuid:mock-udn",
            "ssdp_usn": "uuid:mock-udn::mock-st",
            "upnp": {
                "UDN": "uuid:mock-udn",
                "deviceType": "Paulus",
                "friendlyName": "Bedroom TV",
            },
            "name": "Bedroom TV",
            "x_menuai_matching_domains": ["mock-domain"],
        }
    ]

    mock_ssdp_advertisement["nts"] = "ssdp:byebye"
    ssdp_listener._on_byebye(mock_ssdp_advertisement)
    await menuai.async_block_till_done(wait_background_tasks=True)

    async with asyncio.timeout(1):
        response = await client.receive_json()

    assert response["event"]["remove"] == [
        {"ssdp_location": "http://1.1.1.1", "ssdp_st": "upnp:rootdevice"}
    ]
