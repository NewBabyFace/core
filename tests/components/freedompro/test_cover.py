"""Tests for the Freedompro cover."""

from datetime import timedelta
from unittest.mock import ANY, patch

import pytest

from menuai.components.cover import (
    ATTR_POSITION,
    DOMAIN as COVER_DOMAIN,
    CoverState,
)
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    SERVICE_SET_COVER_POSITION,
)
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.helpers.entity_component import async_update_entity
from menuai.util.dt import utcnow

from .conftest import get_states_response_for_uid

from tests.common import MockConfigEntry, async_fire_time_changed


@pytest.mark.parametrize(
    ("entity_id", "uid", "name", "model"),
    [
        (
            "cover.blind",
            "3WRRJR6RCZQZSND8VP0YTO3YXCSOFPKBMW8T51TU-LQ*3XSSVIJWK-65HILWTC4WINQK46SP4OEZRCNO25VGWAS",
            "blind",
            "windowCovering",
        )
    ],
)
async def test_cover_get_state(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
    init_integration: MockConfigEntry,
    entity_id: str,
    uid: str,
    name: str,
    model: str,
) -> None:
    """Test states of the cover."""

    device = device_registry.async_get_device(identifiers={("freedompro", uid)})
    assert device is not None
    assert device.identifiers == {("freedompro", uid)}
    assert device.manufacturer == "Freedompro"
    assert device.name == name
    assert device.model == model

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == CoverState.CLOSED
    assert state.attributes.get("friendly_name") == name

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == uid

    states_response = get_states_response_for_uid(uid)
    states_response[0]["state"]["position"] = 100
    with patch(
        "menuai.components.freedompro.coordinator.get_states",
        return_value=states_response,
    ):
        async_fire_time_changed(menuai, utcnow() + timedelta(hours=2))
        await menuai.async_block_till_done()

        state = menuai.states.get(entity_id)
        assert state
        assert state.attributes.get("friendly_name") == name

        entry = entity_registry.async_get(entity_id)
        assert entry
        assert entry.unique_id == uid

        assert state.state == CoverState.OPEN


@pytest.mark.parametrize(
    ("entity_id", "uid", "name", "model"),
    [
        (
            "cover.blind",
            "3WRRJR6RCZQZSND8VP0YTO3YXCSOFPKBMW8T51TU-LQ*3XSSVIJWK-65HILWTC4WINQK46SP4OEZRCNO25VGWAS",
            "blind",
            "windowCovering",
        )
    ],
)
async def test_cover_set_position(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
    entity_id: str,
    uid: str,
    name: str,
    model: str,
) -> None:
    """Test set position of the cover."""

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == CoverState.CLOSED
    assert state.attributes.get("friendly_name") == name

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == uid

    with patch("menuai.components.freedompro.cover.put_state") as mock_put_state:
        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_SET_COVER_POSITION,
            {ATTR_ENTITY_ID: [entity_id], ATTR_POSITION: 33},
            blocking=True,
        )
    mock_put_state.assert_called_once_with(ANY, ANY, ANY, '{"position": 33}')

    states_response = get_states_response_for_uid(uid)
    states_response[0]["state"]["position"] = 33
    with patch(
        "menuai.components.freedompro.coordinator.get_states",
        return_value=states_response,
    ):
        async_fire_time_changed(menuai, utcnow() + timedelta(hours=2))
        await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state.state == CoverState.OPEN
    assert state.attributes["current_position"] == 33


@pytest.mark.parametrize(
    ("entity_id", "uid", "name", "model"),
    [
        (
            "cover.blind",
            "3WRRJR6RCZQZSND8VP0YTO3YXCSOFPKBMW8T51TU-LQ*3XSSVIJWK-65HILWTC4WINQK46SP4OEZRCNO25VGWAS",
            "blind",
            "windowCovering",
        )
    ],
)
async def test_cover_close(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
    entity_id: str,
    uid: str,
    name: str,
    model: str,
) -> None:
    """Test close cover."""

    states_response = get_states_response_for_uid(uid)
    states_response[0]["state"]["position"] = 100
    with patch(
        "menuai.components.freedompro.coordinator.get_states",
        return_value=states_response,
    ):
        await async_update_entity(menuai, entity_id)
        async_fire_time_changed(menuai, utcnow() + timedelta(hours=2))
        await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == CoverState.OPEN
    assert state.attributes.get("friendly_name") == name

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == uid

    with patch("menuai.components.freedompro.cover.put_state") as mock_put_state:
        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_CLOSE_COVER,
            {ATTR_ENTITY_ID: [entity_id]},
            blocking=True,
        )
    mock_put_state.assert_called_once_with(ANY, ANY, ANY, '{"position": 0}')

    states_response[0]["state"]["position"] = 0
    with patch(
        "menuai.components.freedompro.coordinator.get_states",
        return_value=states_response,
    ):
        async_fire_time_changed(menuai, utcnow() + timedelta(hours=2))
        await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state.state == CoverState.CLOSED


@pytest.mark.parametrize(
    ("entity_id", "uid", "name", "model"),
    [
        (
            "cover.blind",
            "3WRRJR6RCZQZSND8VP0YTO3YXCSOFPKBMW8T51TU-LQ*3XSSVIJWK-65HILWTC4WINQK46SP4OEZRCNO25VGWAS",
            "blind",
            "windowCovering",
        )
    ],
)
async def test_cover_open(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
    entity_id: str,
    uid: str,
    name: str,
    model: str,
) -> None:
    """Test open cover."""

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == CoverState.CLOSED
    assert state.attributes.get("friendly_name") == name

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == uid

    with patch("menuai.components.freedompro.cover.put_state") as mock_put_state:
        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_OPEN_COVER,
            {ATTR_ENTITY_ID: [entity_id]},
            blocking=True,
        )
    mock_put_state.assert_called_once_with(ANY, ANY, ANY, '{"position": 100}')

    states_response = get_states_response_for_uid(uid)
    states_response[0]["state"]["position"] = 100
    with patch(
        "menuai.components.freedompro.coordinator.get_states",
        return_value=states_response,
    ):
        async_fire_time_changed(menuai, utcnow() + timedelta(hours=2))
        await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state.state == CoverState.OPEN
