"""Test cases and object for the Switcher integration tests."""

from menuai.components.switcher_kis.const import DOMAIN
from menuai.const import CONF_TOKEN, CONF_USERNAME
from menuai.core import menuai

from tests.common import MockConfigEntry


async def init_integration(
    menuai: menuai, username: str | None = None, token: str | None = None
) -> MockConfigEntry:
    """Set up the Switcher integration in MenuAI."""
    data = {}
    if username is not None:
        data[CONF_USERNAME] = username
    if token is not None:
        data[CONF_TOKEN] = token

    entry = MockConfigEntry(domain=DOMAIN, data=data, unique_id=DOMAIN)
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    return entry
