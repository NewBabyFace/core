"""Test the NZBGet switches."""

from unittest.mock import MagicMock

from menuai.components.switch import DOMAIN as SWITCH_DOMAIN
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.helpers.entity_component import async_update_entity

from . import init_integration


async def test_download_switch(
    menuai: menuai, entity_registry: er.EntityRegistry, nzbget_api: MagicMock
) -> None:
    """Test the creation and values of the download switch."""
    instance = nzbget_api.return_value

    entry = await init_integration(menuai)
    assert entry

    entity_id = "switch.nzbgettest_download"
    entity_entry = entity_registry.async_get(entity_id)
    assert entity_entry
    assert entity_entry.unique_id == f"{entry.entry_id}_download"

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_ON

    # test download paused
    instance.status.return_value["DownloadPaused"] = True

    await async_update_entity(menuai, entity_id)
    await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_OFF


async def test_download_switch_services(
    menuai: menuai, nzbget_api: MagicMock
) -> None:
    """Test download switch services."""
    instance = nzbget_api.return_value

    entry = await init_integration(menuai)
    entity_id = "switch.nzbgettest_download"
    assert entry

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    instance.pausedownload.assert_called_once()

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    instance.resumedownload.assert_called_once()
