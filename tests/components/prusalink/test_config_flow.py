"""Test the PrusaLink config flow."""

from unittest.mock import patch

from menuai import config_entries
from menuai.components.prusalink.config_flow import InvalidAuth
from menuai.components.prusalink.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType


async def test_form(menuai: menuai, mock_version_api) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with patch(
        "menuai.components.prusalink.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "http://1.1.1.1/",
                "username": "abcdefg",
                "password": "abcdefg",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "PrusaXL"
    assert result2["data"] == {
        "host": "http://1.1.1.1",
        "username": "abcdefg",
        "password": "abcdefg",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_mk3(menuai: menuai, mock_version_api) -> None:
    """Test it works for MK2/MK3."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_version_api["api"] = "0.9.0-legacy"
    mock_version_api["server"] = "0.7.2"
    mock_version_api["original"] = "PrusaLink I3MK3S"

    with patch(
        "menuai.components.prusalink.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "http://1.1.1.1/",
                "username": "abcdefg",
                "password": "abcdefg",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(menuai: menuai) -> None:
    """Test we handle invalid auth."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.prusalink.config_flow.PrusaLink.get_version",
        side_effect=InvalidAuth,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
                "username": "abcdefg",
                "password": "abcdefg",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_unknown(menuai: menuai) -> None:
    """Test we handle unknown error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.prusalink.config_flow.PrusaLink.get_version",
        side_effect=ValueError,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
                "username": "abcdefg",
                "password": "abcdefg",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_form_too_low_version(menuai: menuai, mock_version_api) -> None:
    """Test we handle too low API version."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_version_api["api"] = "1.2.0"

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "host": "1.1.1.1",
            "username": "abcdefg",
            "password": "abcdefg",
        },
    )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "not_supported"}


async def test_form_invalid_version_2(menuai: menuai, mock_version_api) -> None:
    """Test we handle invalid version."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_version_api["api"] = "i am not a version"

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "host": "1.1.1.1",
            "username": "abcdefg",
            "password": "abcdefg",
        },
    )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "not_supported"}


async def test_form_invalid_mk3_server_version(
    menuai: menuai, mock_version_api
) -> None:
    """Test we handle invalid version for MK2/MK3."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_version_api["api"] = "0.7.2"
    mock_version_api["server"] = "i am not a version"
    mock_version_api["original"] = "PrusaLink I3MK3S"

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "host": "1.1.1.1",
            "username": "abcdefg",
            "password": "abcdefg",
        },
    )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "not_supported"}


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.prusalink.config_flow.PrusaLink.get_version",
        side_effect=TimeoutError,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
                "username": "abcdefg",
                "password": "abcdefg",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}
