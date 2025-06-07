"""Tests for the numato switch platform."""

import pytest

from menuai.components import switch
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    Platform,
)
from menuai.core import menuai
from menuai.helpers import discovery
from menuai.setup import async_setup_component

from .common import NUMATO_CFG, mockup_raise

MOCKUP_ENTITY_IDS = {
    "switch.numato_switch_mock_port5",
    "switch.numato_switch_mock_port6",
}


async def test_failing_setups_no_entities(
    menuai: menuai, numato_fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When port setup fails, no entity shall be created."""
    monkeypatch.setattr(numato_fixture.NumatoDeviceMock, "setup", mockup_raise)
    assert await async_setup_component(menuai, "numato", NUMATO_CFG)
    await menuai.async_block_till_done()
    for entity_id in MOCKUP_ENTITY_IDS:
        assert entity_id not in menuai.states.async_entity_ids()


async def test_regular_menuai_operations(menuai: menuai, numato_fixture) -> None:
    """Test regular operations from within MenuAI."""
    assert await async_setup_component(menuai, "numato", NUMATO_CFG)
    await menuai.async_block_till_done()  # wait until services are registered
    await menuai.services.async_call(
        switch.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "switch.numato_switch_mock_port5"},
        blocking=True,
    )
    assert menuai.states.get("switch.numato_switch_mock_port5").state == "on"
    assert numato_fixture.devices[0].values[5] == 1
    await menuai.services.async_call(
        switch.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "switch.numato_switch_mock_port6"},
        blocking=True,
    )
    assert menuai.states.get("switch.numato_switch_mock_port6").state == "on"
    assert numato_fixture.devices[0].values[6] == 1
    await menuai.services.async_call(
        switch.DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "switch.numato_switch_mock_port5"},
        blocking=True,
    )
    assert menuai.states.get("switch.numato_switch_mock_port5").state == "off"
    assert numato_fixture.devices[0].values[5] == 0
    await menuai.services.async_call(
        switch.DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "switch.numato_switch_mock_port6"},
        blocking=True,
    )
    assert menuai.states.get("switch.numato_switch_mock_port6").state == "off"
    assert numato_fixture.devices[0].values[6] == 0


async def test_failing_menuai_operations(
    menuai: menuai, numato_fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test failing operations called from within MenuAI.

    Switches remain in their initial 'off' state when the device can't
    be written to.
    """
    assert await async_setup_component(menuai, "numato", NUMATO_CFG)

    await menuai.async_block_till_done()  # wait until services are registered
    monkeypatch.setattr(numato_fixture.devices[0], "write", mockup_raise)
    await menuai.services.async_call(
        switch.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "switch.numato_switch_mock_port5"},
        blocking=True,
    )
    assert menuai.states.get("switch.numato_switch_mock_port5").state == "off"
    assert not numato_fixture.devices[0].values[5]
    await menuai.services.async_call(
        switch.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "switch.numato_switch_mock_port6"},
        blocking=True,
    )
    assert menuai.states.get("switch.numato_switch_mock_port6").state == "off"
    assert not numato_fixture.devices[0].values[6]
    await menuai.services.async_call(
        switch.DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "switch.numato_switch_mock_port5"},
        blocking=True,
    )
    assert menuai.states.get("switch.numato_switch_mock_port5").state == "off"
    assert not numato_fixture.devices[0].values[5]
    await menuai.services.async_call(
        switch.DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "switch.numato_switch_mock_port6"},
        blocking=True,
    )
    assert menuai.states.get("switch.numato_switch_mock_port6").state == "off"
    assert not numato_fixture.devices[0].values[6]


async def test_switch_setup_without_discovery_info(
    menuai: menuai, config, numato_fixture
) -> None:
    """Test handling of empty discovery_info."""
    numato_fixture.discover()
    await discovery.async_load_platform(menuai, Platform.SWITCH, "numato", None, config)
    for entity_id in MOCKUP_ENTITY_IDS:
        assert entity_id not in menuai.states.async_entity_ids()
    await menuai.async_block_till_done()  # wait for numato platform to be loaded
    for entity_id in MOCKUP_ENTITY_IDS:
        assert entity_id in menuai.states.async_entity_ids()
