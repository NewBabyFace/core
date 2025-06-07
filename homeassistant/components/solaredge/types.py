"""Typing for the SolarEdge Monitoring API."""

from __future__ import annotations

from typing import TypedDict

from aiosolaredge import SolarEdge

from menuai.config_entries import ConfigEntry

type SolarEdgeConfigEntry = ConfigEntry[SolarEdgeData]


class SolarEdgeData(TypedDict):
    """Data for the solaredge integration."""

    api_client: SolarEdge
