"""Test deCONZ gateway."""

from unittest.mock import patch

from pydeconz.websocket import State
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.deconz.config_flow import DECONZ_MANUFACTURERURL
from menuai.components.deconz.const import DOMAIN
from menuai.config_entries import SOURCE_SSDP
from menuai.const import STATE_OFF, STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.helpers import device_registry as dr
from menuai.helpers.service_info.ssdp import (
    ATTR_UPNP_MANUFACTURER_URL,
    ATTR_UPNP_SERIAL,
    ATTR_UPNP_UDN,
    SsdpServiceInfo,
)

from .conftest import BRIDGE_ID

from tests.common import MockConfigEntry


async def test_device_registry_entry(
    config_entry_setup: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Successful setup."""
    device_entry = device_registry.async_get_device(
        identifiers={(DOMAIN, config_entry_setup.unique_id)}
    )
    assert device_entry == snapshot


@pytest.mark.parametrize(
    "sensor_payload",
    [
        {
            "name": "presence",
            "type": "ZHAPresence",
            "state": {"presence": False},
            "config": {"on": True, "reachable": True},
            "uniqueid": "00:00:00:00:00:00:00:00-00",
        }
    ],
)
@pytest.mark.usefixtures("config_entry_setup")
async def test_connection_status_signalling(
    menuai: menuai, mock_websocket_state
) -> None:
    """Make sure that connection status triggers a dispatcher send."""
    assert menuai.states.get("binary_sensor.presence").state == STATE_OFF

    await mock_websocket_state(State.RETRYING)
    await menuai.async_block_till_done()

    assert menuai.states.get("binary_sensor.presence").state == STATE_UNAVAILABLE

    await mock_websocket_state(State.RUNNING)
    await menuai.async_block_till_done()

    assert menuai.states.get("binary_sensor.presence").state == STATE_OFF


async def test_update_address(
    menuai: menuai, config_entry_setup: MockConfigEntry
) -> None:
    """Make sure that connection status triggers a dispatcher send."""
    assert config_entry_setup.data["host"] == "1.2.3.4"

    with (
        patch(
            "menuai.components.deconz.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
        patch("pydeconz.gateway.WSClient") as ws_mock,
    ):
        await menuai.config_entries.flow.async_init(
            DOMAIN,
            data=SsdpServiceInfo(
                ssdp_st="mock_st",
                ssdp_usn="mock_usn",
                ssdp_location="http://2.3.4.5:80/",
                upnp={
                    ATTR_UPNP_MANUFACTURER_URL: DECONZ_MANUFACTURERURL,
                    ATTR_UPNP_SERIAL: BRIDGE_ID,
                    ATTR_UPNP_UDN: "uuid:456DEF",
                },
            ),
            context={"source": SOURCE_SSDP},
        )
        await menuai.async_block_till_done()

    assert ws_mock.call_args[0][1] == "2.3.4.5"
    assert config_entry_setup.data["host"] == "2.3.4.5"
    assert len(mock_setup_entry.mock_calls) == 1
