"""template conftest."""

from enum import Enum

import pytest

from menuai.core import menuai, ServiceCall
from menuai.helpers.typing import ConfigType
from menuai.setup import async_setup_component

from tests.common import assert_setup_component, async_mock_service


class ConfigurationStyle(Enum):
    """Configuration Styles for template testing."""

    LEGACY = "Legacy"
    MODERN = "Modern"
    TRIGGER = "Trigger"


@pytest.fixture
def calls(menuai: menuai) -> list[ServiceCall]:
    """Track calls to a mock service."""
    return async_mock_service(menuai, "test", "automation")


@pytest.fixture
async def start_ha(
    menuai: menuai, count: int, domain: str, config: ConfigType
) -> None:
    """Do setup of integration."""
    with assert_setup_component(count, domain):
        assert await async_setup_component(
            menuai,
            domain,
            config,
        )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()


@pytest.fixture
async def caplog_setup_text(caplog: pytest.LogCaptureFixture) -> str:
    """Return setup log of integration."""
    return caplog.text


@pytest.fixture(autouse=True, name="stub_blueprint_populate")
def stub_blueprint_populate_autouse(stub_blueprint_populate: None) -> None:
    """Stub copying the blueprints to the config folder."""
