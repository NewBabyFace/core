"""The sensor tests for the Airzone platform."""

from collections.abc import Generator
import copy
from unittest.mock import patch

from aioairzone.const import API_DATA, API_SYSTEMS
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.airzone.coordinator import SCAN_INTERVAL
from menuai.const import STATE_UNAVAILABLE, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.util.dt import utcnow

from .util import (
    HVAC_DHW_MOCK,
    HVAC_MOCK,
    HVAC_SYSTEMS_MOCK,
    HVAC_VERSION_MOCK,
    HVAC_WEBSERVER_MOCK,
    async_init_integration,
)

from tests.common import async_fire_time_changed, snapshot_platform


@pytest.fixture(autouse=True)
def override_platforms() -> Generator[None]:
    """Override PLATFORMS."""
    with patch("menuai.components.airzone.PLATFORMS", [Platform.SENSOR]):
        yield


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_airzone_create_sensors(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test creation of sensors."""

    config_entry = await async_init_integration(menuai)

    await snapshot_platform(menuai, entity_registry, snapshot, config_entry.entry_id)

    state = menuai.states.get("sensor.dkn_plus_humidity")
    assert state is None


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_airzone_sensors_availability(menuai: menuai) -> None:
    """Test sensors availability."""

    await async_init_integration(menuai)

    HVAC_MOCK_UNAVAILABLE_ZONE = copy.deepcopy(HVAC_MOCK)
    del HVAC_MOCK_UNAVAILABLE_ZONE[API_SYSTEMS][0][API_DATA][1]

    with (
        patch(
            "menuai.components.airzone.AirzoneLocalApi.get_dhw",
            return_value=HVAC_DHW_MOCK,
        ),
        patch(
            "menuai.components.airzone.AirzoneLocalApi.get_hvac",
            return_value=HVAC_MOCK_UNAVAILABLE_ZONE,
        ),
        patch(
            "menuai.components.airzone.AirzoneLocalApi.get_hvac_systems",
            return_value=HVAC_SYSTEMS_MOCK,
        ),
        patch(
            "menuai.components.airzone.AirzoneLocalApi.get_version",
            return_value=HVAC_VERSION_MOCK,
        ),
        patch(
            "menuai.components.airzone.AirzoneLocalApi.get_webserver",
            return_value=HVAC_WEBSERVER_MOCK,
        ),
    ):
        async_fire_time_changed(menuai, utcnow() + SCAN_INTERVAL)
        await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get("sensor.dorm_ppal_temperature")
    assert state.state == STATE_UNAVAILABLE

    state = menuai.states.get("sensor.dorm_ppal_humidity")
    assert state.state == STATE_UNAVAILABLE
