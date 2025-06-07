"""Snooz test fixtures and configuration."""

from __future__ import annotations

import pytest

from menuai.core import menuai

from . import SnoozFixture, create_mock_snooz, create_mock_snooz_config_entry


@pytest.fixture(autouse=True)
def mock_bluetooth(enable_bluetooth: None) -> None:
    """Auto mock bluetooth."""


@pytest.fixture
async def mock_connected_snooz(menuai: menuai):
    """Mock a Snooz configuration entry and device."""

    device = await create_mock_snooz()
    entry = await create_mock_snooz_config_entry(menuai, device)

    return SnoozFixture(entry, device)
