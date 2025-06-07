"""Test diagnostics."""

from unittest.mock import patch

import pytest
from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai import setup
from menuai.components import google_assistant as ga, switch
from menuai.const import Platform
from menuai.core import menuai
from menuai.setup import async_setup_component

from .test_http import DUMMY_CONFIG

from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


@pytest.fixture(autouse=True)
async def switch_only() -> None:
    """Enable only the switch platform."""
    with patch(
        "menuai.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.SWITCH],
    ):
        yield


async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test diagnostics v1."""

    await async_setup_component(menuai, "menuai", {})
    await setup.async_setup_component(
        menuai, switch.DOMAIN, {"switch": [{"platform": "demo"}]}
    )

    await async_setup_component(
        menuai,
        ga.DOMAIN,
        {"google_assistant": DUMMY_CONFIG},
    )
    await menuai.async_block_till_done()

    config_entry = menuai.config_entries.async_entries("google_assistant")[0]
    assert await get_diagnostics_for_config_entry(
        menuai, menuai_client, config_entry
    ) == snapshot(exclude=props("entry_id", "created_at", "modified_at"))
