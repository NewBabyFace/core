"""Test the Remember The Milk integration."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from menuai.components.remember_the_milk import DOMAIN
from menuai.core import menuai
from menuai.setup import async_setup_component

from .const import CONFIG, PROFILE, TOKEN


@pytest.fixture(autouse=True)
def configure_id() -> Generator[str]:
    """Fixture to return a configure_id."""
    mock_id = "1-1"
    with patch(
        "menuai.components.configurator.Configurator._generate_unique_id"
    ) as generate_id:
        generate_id.return_value = mock_id
        yield mock_id


@pytest.mark.parametrize(
    ("token", "rtm_entity_exists", "configurator_end_state"),
    [(TOKEN, True, "configured"), (None, False, "configure")],
)
async def test_configurator(
    menuai: menuai,
    client: MagicMock,
    storage: MagicMock,
    configure_id: str,
    token: str | None,
    rtm_entity_exists: bool,
    configurator_end_state: str,
) -> None:
    """Test configurator."""
    storage.get_token.return_value = None
    client.authenticate_desktop.return_value = ("test-url", "test-frob")
    client.token = token
    rtm_entity_id = f"{DOMAIN}.{PROFILE}"
    configure_entity_id = f"configurator.{DOMAIN}_{PROFILE}"

    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: CONFIG})
    await menuai.async_block_till_done()

    assert menuai.states.get(rtm_entity_id) is None
    state = menuai.states.get(configure_entity_id)
    assert state
    assert state.state == "configure"

    await menuai.services.async_call(
        "configurator",
        "configure",
        {"configure_id": configure_id},
        blocking=True,
    )
    await menuai.async_block_till_done()

    assert bool(menuai.states.get(rtm_entity_id)) == rtm_entity_exists
    state = menuai.states.get(configure_entity_id)
    assert state
    assert state.state == configurator_end_state
