"""The Screenlogic integration."""

from menuai.config_entries import ConfigEntry

from .coordinator import ScreenlogicDataUpdateCoordinator

type ScreenLogicConfigEntry = ConfigEntry[ScreenlogicDataUpdateCoordinator]
