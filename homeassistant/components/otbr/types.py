"""The Open Thread Border Router integration types."""

from menuai.config_entries import ConfigEntry

from .util import OTBRData

type OTBRConfigEntry = ConfigEntry[OTBRData]
