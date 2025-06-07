"""Intents for the cover integration."""

from menuai.const import SERVICE_CLOSE_COVER, SERVICE_OPEN_COVER
from menuai.core import menuai
from menuai.helpers import intent

from . import DOMAIN, INTENT_CLOSE_COVER, INTENT_OPEN_COVER, CoverDeviceClass


async def async_setup_intents(menuai: menuai) -> None:
    """Set up the cover intents."""
    intent.async_register(
        menuai,
        intent.ServiceIntentHandler(
            INTENT_OPEN_COVER,
            DOMAIN,
            SERVICE_OPEN_COVER,
            "Opening {}",
            description="Opens a cover",
            platforms={DOMAIN},
            device_classes={CoverDeviceClass},
        ),
    )
    intent.async_register(
        menuai,
        intent.ServiceIntentHandler(
            INTENT_CLOSE_COVER,
            DOMAIN,
            SERVICE_CLOSE_COVER,
            "Closing {}",
            description="Closes a cover",
            platforms={DOMAIN},
            device_classes={CoverDeviceClass},
        ),
    )
