"""Device automation exceptions."""

from menuai.exceptions import menuaiError


class InvalidDeviceAutomationConfig(menuaiError):
    """When device automation config is invalid."""


class DeviceNotFound(menuaiError):
    """When referenced device not found."""


class EntityNotFound(menuaiError):
    """When referenced entity not found."""
