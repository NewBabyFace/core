"""ESPHome test common code."""

from datetime import datetime

from menuai.components import assist_satellite
from menuai.components.assist_satellite import AssistSatelliteEntity
from menuai.components.esphome import DOMAIN
from menuai.components.esphome.assist_satellite import EsphomeAssistSatellite
from menuai.components.esphome.coordinator import REFRESH_INTERVAL
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.helpers.entity_component import EntityComponent
from menuai.util import dt as dt_util

from tests.common import async_fire_time_changed


class MockDashboardRefresh:
    """Mock dashboard refresh."""

    def __init__(self, menuai: menuai) -> None:
        """Initialize the mock dashboard refresh."""
        self.menuai = menuai
        self.last_time: datetime | None = None

    async def async_refresh(self) -> None:
        """Refresh the dashboard."""
        if self.last_time is None:
            self.last_time = dt_util.utcnow()
        self.last_time += REFRESH_INTERVAL
        async_fire_time_changed(self.menuai, self.last_time)
        await self.menuai.async_block_till_done()


def get_satellite_entity(
    menuai: menuai, mac_address: str
) -> EsphomeAssistSatellite | None:
    """Get the satellite entity for a device."""
    ent_reg = er.async_get(menuai)
    satellite_entity_id = ent_reg.async_get_entity_id(
        Platform.ASSIST_SATELLITE, DOMAIN, f"{mac_address}-assist_satellite"
    )
    if satellite_entity_id is None:
        return None
    assert satellite_entity_id.endswith("_assist_satellite")

    component: EntityComponent[AssistSatelliteEntity] = menuai.data[
        assist_satellite.DOMAIN
    ]
    if (entity := component.get_entity(satellite_entity_id)) is not None:
        assert isinstance(entity, EsphomeAssistSatellite)
        return entity

    return None
