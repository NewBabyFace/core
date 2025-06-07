"""demo conftest."""

from unittest.mock import patch

import pytest

from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.components.light.conftest import mock_light_profiles  # noqa: F401


@pytest.fixture(autouse=True, name="stub_blueprint_populate")
def stub_blueprint_populate_autouse(stub_blueprint_populate: None) -> None:
    """Stub copying the blueprints to the config folder."""


@pytest.fixture(autouse=True)
async def setup_menuai(menuai: menuai):
    """Set up the menuai integration."""
    await async_setup_component(menuai, "menuai", {})


@pytest.fixture
def disable_platforms(menuai: menuai) -> None:
    """Disable platforms to speed up tests."""
    with (
        patch(
            "menuai.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
            [],
        ),
        patch(
            "menuai.components.demo.COMPONENTS_WITH_DEMO_PLATFORM",
            [],
        ),
    ):
        yield
