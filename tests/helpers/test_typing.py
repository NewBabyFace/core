"""Test typing helper module."""

from __future__ import annotations

from typing import Any

import pytest

from menuai.core import Context, Event, menuai, ServiceCall
from menuai.helpers import typing as ha_typing

from tests.common import import_and_test_deprecated_alias


@pytest.mark.parametrize(
    ("alias_name", "replacement", "breaks_in_ha_version"),
    [
        ("ContextType", Context, "2025.5"),
        ("EventType", Event, "2025.5"),
        ("menuaiType", menuai, "2025.5"),
        ("ServiceCallType", ServiceCall, "2025.5"),
    ],
)
def test_deprecated_aliases(
    caplog: pytest.LogCaptureFixture,
    alias_name: str,
    replacement: Any,
    breaks_in_ha_version: str,
) -> None:
    """Test deprecated aliases."""
    import_and_test_deprecated_alias(
        caplog,
        ha_typing,
        alias_name,
        replacement,
        breaks_in_ha_version,
    )
