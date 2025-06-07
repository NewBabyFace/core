"""Tests for the Rituals Perfume Genie number platform."""

from __future__ import annotations

import pytest

from menuai.components.menuai import SERVICE_UPDATE_ENTITY
from menuai.components.number import (
    ATTR_MAX,
    ATTR_MIN,
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai
from menuai.exceptions import ServiceValidationError
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component

from .common import (
    init_integration,
    mock_config_entry,
    mock_diffuser,
    mock_diffuser_v1_battery_cartridge,
)


async def test_number_entity(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test the creation and values of the diffuser number entity."""
    config_entry = mock_config_entry(unique_id="number_test")
    diffuser = mock_diffuser(hublot="lot123", perfume_amount=2)
    await init_integration(menuai, config_entry, [diffuser])

    state = menuai.states.get("number.genie_perfume_amount")
    assert state
    assert state.state == str(diffuser.perfume_amount)
    assert state.attributes[ATTR_MIN] == 1
    assert state.attributes[ATTR_MAX] == 3

    entry = entity_registry.async_get("number.genie_perfume_amount")
    assert entry
    assert entry.unique_id == f"{diffuser.hublot}-perfume_amount"


async def test_set_number_value(menuai: menuai) -> None:
    """Test setting the diffuser number entity value."""
    config_entry = mock_config_entry(unique_id="number_set_value_test")
    diffuser = mock_diffuser_v1_battery_cartridge()
    await init_integration(menuai, config_entry, [diffuser])
    await async_setup_component(menuai, "menuai", {})
    diffuser.perfume_amount = 1

    state = menuai.states.get("number.genie_perfume_amount")
    assert state
    assert state.state == "2"

    await menuai.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: "number.genie_perfume_amount", ATTR_VALUE: 1},
        blocking=True,
    )
    await menuai.services.async_call(
        "menuai",
        SERVICE_UPDATE_ENTITY,
        {ATTR_ENTITY_ID: ["number.genie_perfume_amount"]},
        blocking=True,
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("number.genie_perfume_amount")
    assert state
    assert state.state == "1"


async def test_set_number_value_out_of_range(menuai: menuai) -> None:
    """Test setting the diffuser number entity value out of range."""
    config_entry = mock_config_entry(unique_id="number_set_value_out_of_range_test")
    diffuser = mock_diffuser(hublot="lot123", perfume_amount=2)
    await init_integration(menuai, config_entry, [diffuser])
    await async_setup_component(menuai, "menuai", {})

    state = menuai.states.get("number.genie_perfume_amount")
    assert state
    assert state.state == "2"

    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: "number.genie_perfume_amount", ATTR_VALUE: 4},
            blocking=True,
        )
    await menuai.services.async_call(
        "menuai",
        SERVICE_UPDATE_ENTITY,
        {ATTR_ENTITY_ID: ["number.genie_perfume_amount"]},
        blocking=True,
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("number.genie_perfume_amount")
    assert state
    assert state.state == "2"

    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: "number.genie_perfume_amount", ATTR_VALUE: 0},
            blocking=True,
        )
    await menuai.services.async_call(
        "menuai",
        SERVICE_UPDATE_ENTITY,
        {ATTR_ENTITY_ID: ["number.genie_perfume_amount"]},
        blocking=True,
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("number.genie_perfume_amount")
    assert state
    assert state.state == "2"


async def test_set_number_value_to_float(menuai: menuai) -> None:
    """Test setting the diffuser number entity value to a float."""
    config_entry = mock_config_entry(unique_id="number_set_value_to_float_test")
    diffuser = mock_diffuser(hublot="lot123", perfume_amount=3)
    await init_integration(menuai, config_entry, [diffuser])
    await async_setup_component(menuai, "menuai", {})

    state = menuai.states.get("number.genie_perfume_amount")
    assert state
    assert state.state == "3"

    with pytest.raises(ValueError):
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: "number.genie_perfume_amount", ATTR_VALUE: 1.5},
            blocking=True,
        )
    await menuai.services.async_call(
        "menuai",
        SERVICE_UPDATE_ENTITY,
        {ATTR_ENTITY_ID: ["number.genie_perfume_amount"]},
        blocking=True,
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("number.genie_perfume_amount")
    assert state
    assert state.state == "3"
