"""Common fixtures for the PG LAB Electronics tests."""

import pytest

from menuai.components.pglab.const import DISCOVERY_TOPIC, DOMAIN
from menuai.core import menuai

from tests.common import MockConfigEntry, mock_device_registry, mock_registry

CONF_DISCOVERY_PREFIX = "discovery_prefix"


@pytest.fixture
def device_reg(menuai: menuai):
    """Return an empty, loaded, registry."""
    return mock_device_registry(menuai)


@pytest.fixture
def entity_reg(menuai: menuai):
    """Return an empty, loaded, registry."""
    return mock_registry(menuai)


@pytest.fixture
async def setup_pglab(menuai: menuai):
    """Set up PG LAB Electronics."""
    menuai.config.components.add("pglab")

    entry = MockConfigEntry(
        data={CONF_DISCOVERY_PREFIX: DISCOVERY_TOPIC},
        domain=DOMAIN,
        title="PG LAB Electronics",
    )

    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert "pglab" in menuai.config.components
