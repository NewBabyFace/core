"""Tests for Vallox binary sensor platform."""

from typing import Any

import pytest

from menuai.core import menuai

from tests.common import MockConfigEntry


@pytest.mark.parametrize(
    ("metrics", "expected_state"),
    [
        ({"A_CYC_IO_HEATER": 1}, "on"),
        ({"A_CYC_IO_HEATER": 0}, "off"),
    ],
)
async def test_binary_sensor_entitity(
    metrics: dict[str, Any],
    expected_state: str,
    mock_entry: MockConfigEntry,
    setup_fetch_metric_data_mock,
    menuai: menuai,
) -> None:
    """Test binary sensor with metrics."""

    # Arrange
    fetch_metric_data_mock = setup_fetch_metric_data_mock(metrics)

    # Act
    await menuai.config_entries.async_setup(mock_entry.entry_id)
    await menuai.async_block_till_done()

    # Assert
    fetch_metric_data_mock.assert_called_once()
    sensor = menuai.states.get("binary_sensor.vallox_post_heater")
    assert sensor.state == expected_state
