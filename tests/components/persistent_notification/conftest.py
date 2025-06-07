"""The tests for the persistent notification component."""

import pytest

from menuai.components import persistent_notification as pn
from menuai.core import menuai
from menuai.setup import async_setup_component


@pytest.fixture(autouse=True)
async def setup_integration(menuai: menuai) -> None:
    """Set up persistent notification integration."""
    assert await async_setup_component(menuai, pn.DOMAIN, {})
