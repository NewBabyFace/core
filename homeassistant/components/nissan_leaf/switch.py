"""Charge and Climate Control Support for the Nissan Leaf."""

from __future__ import annotations

import logging
from typing import Any

from menuai.components.switch import SwitchEntity
from menuai.core import menuai
from menuai.helpers.entity_platform import AddEntitiesCallback
from menuai.helpers.typing import ConfigType, DiscoveryInfoType

from . import LeafDataStore
from .const import DATA_CLIMATE, DATA_LEAF
from .entity import LeafEntity

_LOGGER = logging.getLogger(__name__)


def setup_platform(
    menuai: menuai,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Nissan Leaf switch platform setup."""
    if discovery_info is None:
        return

    entities: list[LeafEntity] = []
    for vin, datastore in menuai.data[DATA_LEAF].items():
        _LOGGER.debug("Adding switch for vin=%s", vin)
        entities.append(LeafClimateSwitch(datastore))

    add_entities(entities, True)


class LeafClimateSwitch(LeafEntity, SwitchEntity):
    """Nissan Leaf Climate Control switch."""

    def __init__(self, car: LeafDataStore) -> None:
        """Set up climate control switch."""
        super().__init__(car)
        self._attr_unique_id = f"{self.car.leaf.vin.lower()}_climatecontrol"

    @property
    def name(self) -> str:
        """Switch name."""
        return f"{self.car.leaf.nickname} Climate Control"

    def log_registration(self) -> None:
        """Log registration."""
        _LOGGER.debug(
            "Registered LeafClimateSwitch integration with MenuAI for VIN %s",
            self.car.leaf.vin,
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return climate control attributes."""
        attrs = super().extra_state_attributes
        attrs["updated_on"] = self.car.last_climate_response
        return attrs

    @property
    def is_on(self) -> bool:
        """Return true if climate control is on."""
        return bool(self.car.data[DATA_CLIMATE])

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on climate control."""
        if await self.car.async_set_climate(True):
            self.car.data[DATA_CLIMATE] = True

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off climate control."""
        if await self.car.async_set_climate(False):
            self.car.data[DATA_CLIMATE] = False
