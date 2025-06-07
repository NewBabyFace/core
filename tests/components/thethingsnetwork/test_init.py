"""Define tests for the The Things Network init."""

import pytest
from ttn_client import TTNAuthError

from menuai.core import menuai


@pytest.mark.parametrize(("exception_class"), [TTNAuthError, Exception])
async def test_init_exceptions(
    menuai: menuai, mock_ttnclient, exception_class, mock_config_entry
) -> None:
    """Test TTN Exceptions."""

    mock_ttnclient.return_value.fetch_data.side_effect = exception_class
    mock_config_entry.add_to_menuai(menuai)
    assert not await menuai.config_entries.async_setup(mock_config_entry.entry_id)
