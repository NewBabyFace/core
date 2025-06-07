"""Test the Fully Kiosk Browser diagnostics."""

from unittest.mock import MagicMock

from menuai.components.diagnostics import REDACTED
from menuai.components.fully_kiosk.const import DOMAIN
from menuai.components.fully_kiosk.diagnostics import (
    DEVICE_INFO_TO_REDACT,
    SETTINGS_TO_REDACT,
)
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_device
from tests.typing import ClientSessionGenerator


async def test_diagnostics(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    menuai_client: ClientSessionGenerator,
    mock_fully_kiosk: MagicMock,
    init_integration: MockConfigEntry,
) -> None:
    """Test Fully Kiosk diagnostics."""
    device = device_registry.async_get_device(identifiers={(DOMAIN, "abcdef-123456")})

    diagnostics = await get_diagnostics_for_device(
        menuai, menuai_client, init_integration, device
    )

    assert diagnostics
    for key in DEVICE_INFO_TO_REDACT:
        if hasattr(diagnostics, key):
            assert diagnostics[key] == REDACTED
    for key in SETTINGS_TO_REDACT:
        if hasattr(diagnostics["settings"], key):
            assert (
                diagnostics["settings"][key] == REDACTED
                or diagnostics["settings"][key] == ""
            )
