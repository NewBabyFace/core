"""Unit test for CCM15 coordinator component."""

from datetime import timedelta
from unittest.mock import patch

from ccm15 import CCM15DeviceState
from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.ccm15.const import DOMAIN
from menuai.components.climate import (
    ATTR_FAN_MODE,
    ATTR_HVAC_MODE,
    ATTR_TEMPERATURE,
    DOMAIN as CLIMATE_DOMAIN,
    FAN_HIGH,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
    SERVICE_TURN_ON,
    HVACMode,
)
from menuai.const import ATTR_ENTITY_ID, CONF_HOST, CONF_PORT, SERVICE_TURN_OFF
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry, async_fire_time_changed


@pytest.mark.usefixtures("ccm15_device")
async def test_climate_state(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the coordinator."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="1.1.1.1",
        data={
            CONF_HOST: "1.1.1.1",
            CONF_PORT: 80,
        },
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert entity_registry.async_get("climate.midea_0") == snapshot
    assert entity_registry.async_get("climate.midea_1") == snapshot

    assert menuai.states.get("climate.midea_0") == snapshot
    assert menuai.states.get("climate.midea_1") == snapshot

    with patch(
        "menuai.components.ccm15.coordinator.CCM15Device.async_set_state"
    ) as mock_set_state:
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_FAN_MODE,
            {ATTR_ENTITY_ID: ["climate.midea_0"], ATTR_FAN_MODE: FAN_HIGH},
            blocking=True,
        )
        await menuai.async_block_till_done()
        mock_set_state.assert_called_once()

    with patch(
        "menuai.components.ccm15.coordinator.CCM15Device.async_set_state"
    ) as mock_set_state:
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            {ATTR_ENTITY_ID: ["climate.midea_0"], ATTR_HVAC_MODE: HVACMode.COOL},
            blocking=True,
        )
        await menuai.async_block_till_done()
        mock_set_state.assert_called_once()

    with patch(
        "menuai.components.ccm15.coordinator.CCM15Device.async_set_state"
    ) as mock_set_state:
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {ATTR_ENTITY_ID: ["climate.midea_0"], ATTR_TEMPERATURE: 25},
            blocking=True,
        )
        await menuai.async_block_till_done()
        mock_set_state.assert_called_once()

    with patch(
        "menuai.components.ccm15.coordinator.CCM15Device.async_set_state"
    ) as mock_set_state:
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: ["climate.midea_0"]},
            blocking=True,
        )
        await menuai.async_block_till_done()
        mock_set_state.assert_called_once()

    with patch(
        "menuai.components.ccm15.coordinator.CCM15Device.async_set_state"
    ) as mock_set_state:
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: ["climate.midea_0"]},
            blocking=True,
        )
        await menuai.async_block_till_done()
        mock_set_state.assert_called_once()

    # Create an instance of the CCM15DeviceState class
    device_state = CCM15DeviceState(devices={})
    with patch(
        "ccm15.CCM15Device.CCM15Device.get_status_async",
        return_value=device_state,
    ):
        freezer.tick(timedelta(minutes=15))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()

    assert entity_registry.async_get("climate.midea_0") == snapshot
    assert entity_registry.async_get("climate.midea_1") == snapshot

    assert menuai.states.get("climate.midea_0") == snapshot
    assert menuai.states.get("climate.midea_1") == snapshot
