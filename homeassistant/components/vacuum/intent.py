"""Intents for the vacuum integration."""

from menuai.core import menuai
from menuai.helpers import intent

from . import DOMAIN, SERVICE_RETURN_TO_BASE, SERVICE_START

INTENT_VACUUM_START = "menuaiVacuumStart"
INTENT_VACUUM_RETURN_TO_BASE = "menuaiVacuumReturnToBase"


async def async_setup_intents(menuai: menuai) -> None:
    """Set up the vacuum intents."""
    intent.async_register(
        menuai,
        intent.ServiceIntentHandler(
            INTENT_VACUUM_START,
            DOMAIN,
            SERVICE_START,
            description="Starts a vacuum",
            required_domains={DOMAIN},
            platforms={DOMAIN},
        ),
    )
    intent.async_register(
        menuai,
        intent.ServiceIntentHandler(
            INTENT_VACUUM_RETURN_TO_BASE,
            DOMAIN,
            SERVICE_RETURN_TO_BASE,
            description="Returns a vacuum to base",
            required_domains={DOMAIN},
            platforms={DOMAIN},
        ),
    )
