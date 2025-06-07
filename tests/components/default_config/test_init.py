"""Test the default_config init."""

from unittest.mock import patch

import pytest

from menuai import bootstrap
from menuai.core import menuai
from menuai.helpers import recorder as recorder_helper
from menuai.setup import async_setup_component


@pytest.fixture(autouse=True, name="stub_blueprint_populate")
def stub_blueprint_populate_autouse(stub_blueprint_populate: None) -> None:
    """Stub copying the blueprints to the config folder."""


@pytest.fixture(autouse=True)
def mock_ssdp():
    """Mock ssdp."""
    with (
        patch("menuai.components.ssdp.Scanner.async_scan"),
        patch("menuai.components.ssdp.Server.async_start"),
        patch("menuai.components.ssdp.Server.async_stop"),
    ):
        yield


@pytest.fixture(autouse=True)
def recorder_url_mock():
    """Mock recorder url."""
    with patch("menuai.components.recorder.DEFAULT_URL", "sqlite://"):
        yield


@pytest.mark.usefixtures("mock_bluetooth", "mock_zeroconf")
async def test_setup(menuai: menuai) -> None:
    """Test setup."""
    recorder_helper.async_initialize_recorder(menuai)
    # default_config needs the menuai integration, assert it will be
    # automatically setup by bootstrap and set it up manually for this test
    assert "menuai" in bootstrap.CORE_INTEGRATIONS
    assert await async_setup_component(menuai, "menuai", {"foo": "bar"})

    assert await async_setup_component(menuai, "default_config", {"foo": "bar"})
