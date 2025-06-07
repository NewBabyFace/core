"""Test the Downloader config flow."""

from unittest.mock import patch

import pytest

from menuai.components.downloader.const import CONF_DOWNLOAD_DIR, DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

CONFIG = {CONF_DOWNLOAD_DIR: "download_dir"}


async def test_user_form(menuai: menuai) -> None:
    """Test the full user configuration flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=CONFIG,
    )
    assert result["type"] is FlowResultType.FORM

    with patch("os.path.isdir", return_value=False):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=CONFIG,
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": "directory_does_not_exist"}

    with (
        patch(
            "menuai.components.downloader.async_setup_entry", return_value=True
        ),
        patch(
            "os.path.isdir",
            return_value=True,
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=CONFIG,
        )
        await menuai.async_block_till_done()
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "Downloader"
        assert result["data"] == {"download_dir": "download_dir"}


@pytest.mark.parametrize("source", [SOURCE_USER])
async def test_single_instance_allowed(
    menuai: menuai,
    source: str,
) -> None:
    """Test we abort if already setup."""
    mock_config_entry = MockConfigEntry(domain=DOMAIN)
    mock_config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": source}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"
