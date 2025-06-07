"""Tests for Broadlink select."""

from menuai.components.broadlink.const import DOMAIN
from menuai.components.select import (
    ATTR_OPTION,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.helpers.entity_component import async_update_entity

from . import get_device


async def test_select(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test Broadlink select."""
    await menuai.config.async_set_time_zone("UTC")

    device = get_device("Guest room")
    mock_setup = await device.setup_entry(menuai)

    device_entry = device_registry.async_get_device(
        identifiers={(DOMAIN, mock_setup.entry.unique_id)}
    )
    entries = er.async_entries_for_device(entity_registry, device_entry.id)
    selects = [entry for entry in entries if entry.domain == Platform.SELECT]
    assert len(selects) == 1

    select = selects[0]

    mock_setup.api.get_full_status.return_value = {
        "dayofweek": 3,
        "hour": 2,
        "min": 3,
        "sec": 4,
    }
    await async_update_entity(menuai, select.entity_id)
    assert mock_setup.api.get_full_status.call_count == 2
    state = menuai.states.get(select.entity_id)
    assert state.state == "wednesday"

    # set value
    await menuai.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {
            ATTR_ENTITY_ID: select.entity_id,
            ATTR_OPTION: "tuesday",
        },
        blocking=True,
    )
    state = menuai.states.get(select.entity_id)
    assert state.state == "tuesday"
    assert mock_setup.api.set_time.call_count == 1
    call_args = mock_setup.api.set_time.call_args.kwargs
    assert call_args == {
        "hour": 2,
        "minute": 3,
        "second": 4,
        "day": 2,
    }
