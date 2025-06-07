"""Adds constants for Trafikverket Weather integration."""

from menuai.const import Platform

DOMAIN = "trafikverket_weatherstation"
CONF_STATION = "station"
PLATFORMS = [Platform.SENSOR]
ATTRIBUTION = "Data provided by Trafikverket"
