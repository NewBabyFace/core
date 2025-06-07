"""Types for the Model Context Protocol integration."""

from menuai.config_entries import ConfigEntry

from .coordinator import ModelContextProtocolCoordinator

type ModelContextProtocolConfigEntry = ConfigEntry[ModelContextProtocolCoordinator]
