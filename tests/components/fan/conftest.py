"""Fixtures for Fan platform tests."""

from collections.abc import Generator

import pytest

from menuai.config_entries import ConfigFlow
from menuai.core import menuai

from tests.common import mock_config_flow, mock_platform


class MockFlow(ConfigFlow):
    """Test flow."""


@pytest.fixture
def config_flow_fixture(menuai: menuai) -> Generator[None]:
    """Mock config flow."""
    mock_platform(menuai, "test.config_flow")

    with mock_config_flow("test", MockFlow):
        yield
