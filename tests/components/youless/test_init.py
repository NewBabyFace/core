"""Test the setup of the Youless integration."""

from menuai import setup
from menuai.components import youless
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import init_component


async def test_async_setup_entry(menuai: menuai) -> None:
    """Check if the setup of the integration succeeds."""

    entry = await init_component(menuai)

    assert await setup.async_setup_component(menuai, youless.DOMAIN, {})
    assert entry.state is ConfigEntryState.LOADED
    assert len(menuai.states.async_entity_ids()) == 22
