"""The init tests for the UPB platform."""

from unittest.mock import patch

from menuai.components.upb.const import DOMAIN
from menuai.core import menuai

from tests.common import MockConfigEntry


async def test_migrate_entry_minor_version_1_2(menuai: menuai) -> None:
    """Test migrating a 1.1 config entry to 1.2."""
    with patch("menuai.components.upb.async_setup_entry", return_value=True):
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={"protocol": "TCP", "address": "1.2.3.4", "file_path": "upb.upe"},
            version=1,
            minor_version=1,
            unique_id=123456,
        )
        entry.add_to_menuai(menuai)
        assert await menuai.config_entries.async_setup(entry.entry_id)
        assert entry.version == 1
        assert entry.minor_version == 2
        assert entry.unique_id == "123456"
