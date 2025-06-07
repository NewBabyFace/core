"""Sonos specific exceptions."""

from menuai.components.media_player import BrowseError
from menuai.exceptions import menuaiError


class UnknownMediaType(BrowseError):
    """Unknown media type."""


class SonosSubscriptionsFailed(menuaiError):
    """Subscription creation failed."""


class SonosUpdateError(menuaiError):
    """Update failed."""


class S1BatteryMissing(SonosUpdateError):
    """Battery update failed on S1 firmware."""
