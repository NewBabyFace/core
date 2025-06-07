"""Tests for the Huawei LTE switches."""

from unittest.mock import MagicMock, patch

from menuai.components.huawei_lte.const import DOMAIN
from menuai.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from menuai.const import ATTR_ENTITY_ID, CONF_URL, STATE_OFF, STATE_ON
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import magic_client

from tests.common import MockConfigEntry

SWITCH_WIFI_GUEST_NETWORK = "switch.lte_wi_fi_guest_network"


@patch("menuai.components.huawei_lte.Connection", MagicMock())
@patch("menuai.components.huawei_lte.Client", return_value=magic_client({}))
async def test_huawei_lte_wifi_guest_network_config_entry_when_network_is_not_present(
    client,
    menuai: menuai,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test switch wifi guest network config entry when network is not present."""
    huawei_lte = MockConfigEntry(domain=DOMAIN, data={CONF_URL: "http://huawei-lte"})
    huawei_lte.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(huawei_lte.entry_id)
    await menuai.async_block_till_done()
    assert not entity_registry.async_is_registered(SWITCH_WIFI_GUEST_NETWORK)


@patch("menuai.components.huawei_lte.Connection", MagicMock())
@patch(
    "menuai.components.huawei_lte.Client",
    return_value=magic_client(
        {"Ssids": {"Ssid": [{"wifiisguestnetwork": "1", "WifiEnable": "0"}]}}
    ),
)
async def test_huawei_lte_wifi_guest_network_config_entry_when_network_is_present(
    client,
    menuai: menuai,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test switch wifi guest network config entry when network is present."""
    huawei_lte = MockConfigEntry(domain=DOMAIN, data={CONF_URL: "http://huawei-lte"})
    huawei_lte.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(huawei_lte.entry_id)
    await menuai.async_block_till_done()
    assert entity_registry.async_is_registered(SWITCH_WIFI_GUEST_NETWORK)


@patch("menuai.components.huawei_lte.Connection", MagicMock())
@patch("menuai.components.huawei_lte.Client")
async def test_turn_on_switch_wifi_guest_network(client, menuai: menuai) -> None:
    """Test switch wifi guest network turn on method."""
    client.return_value = magic_client(
        {"Ssids": {"Ssid": [{"wifiisguestnetwork": "1", "WifiEnable": "0"}]}}
    )
    huawei_lte = MockConfigEntry(domain=DOMAIN, data={CONF_URL: "http://huawei-lte"})
    huawei_lte.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(huawei_lte.entry_id)
    await menuai.async_block_till_done()
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: SWITCH_WIFI_GUEST_NETWORK},
        blocking=True,
    )
    await menuai.async_block_till_done()
    assert menuai.states.is_state(SWITCH_WIFI_GUEST_NETWORK, STATE_ON)
    client.return_value.wlan.wifi_guest_network_switch.assert_called_once_with(True)


@patch("menuai.components.huawei_lte.Connection", MagicMock())
@patch("menuai.components.huawei_lte.Client")
async def test_turn_off_switch_wifi_guest_network(client, menuai: menuai) -> None:
    """Test switch wifi guest network turn off method."""
    client.return_value = magic_client(
        {"Ssids": {"Ssid": [{"wifiisguestnetwork": "1", "WifiEnable": "1"}]}}
    )
    huawei_lte = MockConfigEntry(domain=DOMAIN, data={CONF_URL: "http://huawei-lte"})
    huawei_lte.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(huawei_lte.entry_id)
    await menuai.async_block_till_done()
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: SWITCH_WIFI_GUEST_NETWORK},
        blocking=True,
    )
    await menuai.async_block_till_done()
    assert menuai.states.is_state(SWITCH_WIFI_GUEST_NETWORK, STATE_OFF)
    client.return_value.wlan.wifi_guest_network_switch.assert_called_with(False)


@patch("menuai.components.huawei_lte.Connection", MagicMock())
@patch(
    "menuai.components.huawei_lte.Client",
    return_value=magic_client({"Ssids": {"Ssid": "str"}}),
)
async def test_huawei_lte_wifi_guest_network_config_entry_when_ssid_is_str(
    client,
    menuai: menuai,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test switch wifi guest network config entry when ssid is a str.

    Issue #76244. Huawai models: H312-371, E5372 and E8372.
    """
    huawei_lte = MockConfigEntry(domain=DOMAIN, data={CONF_URL: "http://huawei-lte"})
    huawei_lte.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(huawei_lte.entry_id)
    await menuai.async_block_till_done()
    assert not entity_registry.async_is_registered(SWITCH_WIFI_GUEST_NETWORK)


@patch("menuai.components.huawei_lte.Connection", MagicMock())
@patch(
    "menuai.components.huawei_lte.Client",
    return_value=magic_client({"Ssids": {"Ssid": None}}),
)
async def test_huawei_lte_wifi_guest_network_config_entry_when_ssid_is_none(
    client,
    menuai: menuai,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test switch wifi guest network config entry when ssid is a None.

    Issue #76244.
    """
    huawei_lte = MockConfigEntry(domain=DOMAIN, data={CONF_URL: "http://huawei-lte"})
    huawei_lte.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(huawei_lte.entry_id)
    await menuai.async_block_till_done()
    assert not entity_registry.async_is_registered(SWITCH_WIFI_GUEST_NETWORK)
