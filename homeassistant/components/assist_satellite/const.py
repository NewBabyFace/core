"""Constants for assist satellite."""

from __future__ import annotations

import asyncio
from enum import IntFlag
from typing import TYPE_CHECKING

from menuai.util.menuai_dict import menuaiKey

if TYPE_CHECKING:
    from menuai.helpers.entity_component import EntityComponent

    from .entity import AssistSatelliteEntity

DOMAIN = "assist_satellite"

DATA_COMPONENT: menuaiKey[EntityComponent[AssistSatelliteEntity]] = menuaiKey(DOMAIN)
CONNECTION_TEST_DATA: menuaiKey[dict[str, asyncio.Event]] = menuaiKey(
    f"{DOMAIN}_connection_tests"
)

PREANNOUNCE_FILENAME = "preannounce.mp3"
PREANNOUNCE_URL = f"/api/assist_satellite/static/{PREANNOUNCE_FILENAME}"


class AssistSatelliteEntityFeature(IntFlag):
    """Supported features of Assist satellite entity."""

    ANNOUNCE = 1
    """Device supports remotely triggered announcements."""

    START_CONVERSATION = 2
    """Device supports starting conversations."""
