"""Test the Plum Lightpad config flow."""

from unittest.mock import patch

from requests.exceptions import ConnectTimeout

from menuai import config_entries
from menuai.components.plum_lightpad.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch("menuai.components.plum_lightpad.utils.Plum.loadCloudData"),
        patch(
            "menuai.components.plum_lightpad.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": "test-plum-username", "password": "test-plum-password"},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "test-plum-username"
    assert result2["data"] == {
        "username": "test-plum-username",
        "password": "test-plum-password",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle invalid auth."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.plum_lightpad.utils.Plum.loadCloudData",
        side_effect=ConnectTimeout,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": "test-plum-username", "password": "test-plum-password"},
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_one_entry_per_email_allowed(menuai: menuai) -> None:
    """Test that only one entry allowed per Plum cloud email address."""
    MockConfigEntry(
        domain=DOMAIN,
        unique_id="test-plum-username",
        data={"username": "test-plum-username", "password": "test-plum-password"},
    ).add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch("menuai.components.plum_lightpad.utils.Plum.loadCloudData"),
        patch(
            "menuai.components.plum_lightpad.async_setup_entry"
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": "test-plum-username", "password": "test-plum-password"},
        )

    assert result2["type"] is FlowResultType.ABORT
    await menuai.async_block_till_done()
    assert len(mock_setup_entry.mock_calls) == 0
