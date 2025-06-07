"""WebSocket API related errors."""

from menuai.exceptions import menuaiError


class Disconnect(menuaiError):
    """Disconnect the current session."""
