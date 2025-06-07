"""Test the epson init."""

from unittest.mock import patch

from menuai.components.epson.const import CONF_CONNECTION_TYPE, DOMAIN
from menuai.const import CONF_HOST
from menuai.core import menuai

from tests.common import MockConfigEntry


async def test_migrate_entry(menuai: menuai) -> None:
    """Test successful migration of entry data from version 1 to 1.2."""

    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Epson",
        version=1,
        minor_version=1,
        data={CONF_HOST: "1.1.1.1"},
        entry_id="1cb78c095906279574a0442a1f0003ef",
    )
    assert mock_entry.version == 1

    mock_entry.add_to_menuai(menuai)

    # Create entity entry to migrate to new unique ID
    with patch("menuai.components.epson.Projector.get_power"):
        await menuai.config_entries.async_setup(mock_entry.entry_id)
        await menuai.async_block_till_done()

    # Check that is now has connection_type
    assert mock_entry
    assert mock_entry.version == 1
    assert mock_entry.minor_version == 2
    assert mock_entry.data.get(CONF_CONNECTION_TYPE) == "http"
    assert mock_entry.data.get(CONF_HOST) == "1.1.1.1"
