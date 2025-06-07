"""Test binary sensors of APCUPSd integration."""

from unittest.mock import patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.util import slugify

from . import MOCK_STATUS, async_init_integration

from tests.common import snapshot_platform


async def test_binary_sensor(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test states of binary sensors."""
    with patch("menuai.components.apcupsd.PLATFORMS", [Platform.BINARY_SENSOR]):
        config_entry = await async_init_integration(menuai, status=MOCK_STATUS)
    await snapshot_platform(menuai, entity_registry, snapshot, config_entry.entry_id)


async def test_no_binary_sensor(menuai: menuai) -> None:
    """Test binary sensor when STATFLAG is not available."""
    status = MOCK_STATUS.copy()
    status.pop("STATFLAG")
    await async_init_integration(menuai, status=status)

    device_slug = slugify(MOCK_STATUS["UPSNAME"])
    state = menuai.states.get(f"binary_sensor.{device_slug}_online_status")
    assert state is None


@pytest.mark.parametrize(
    ("override", "expected"),
    [
        ("0x008", "on"),
        ("0x02040010 Status Flag", "off"),
    ],
)
async def test_statflag(menuai: menuai, override: str, expected: str) -> None:
    """Test binary sensor for different STATFLAG values."""
    status = MOCK_STATUS.copy()
    status["STATFLAG"] = override
    await async_init_integration(menuai, status=status)

    device_slug = slugify(MOCK_STATUS["UPSNAME"])
    assert (
        menuai.states.get(f"binary_sensor.{device_slug}_online_status").state == expected
    )
