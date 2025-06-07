"""The repairs integration."""

from __future__ import annotations

from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.typing import ConfigType

from . import issue_handler, websocket_api
from .const import DOMAIN
from .issue_handler import ConfirmRepairFlow, RepairsFlowManager
from .models import RepairsFlow

__all__ = [
    "DOMAIN",
    "ConfirmRepairFlow",
    "RepairsFlow",
    "RepairsFlowManager",
    "repairs_flow_manager",
]
CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


def repairs_flow_manager(menuai: menuai) -> RepairsFlowManager | None:
    """Return the repairs flow manager."""
    if (domain_data := menuai.data.get(DOMAIN)) is None:
        return None

    flow_manager: RepairsFlowManager | None = domain_data.get("flow_manager")
    return flow_manager


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up Repairs."""
    menuai.data[DOMAIN] = {}

    issue_handler.async_setup(menuai)
    websocket_api.async_setup(menuai)

    return True
