"""Test the VLC media player Telnet config flow."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from aiovlc.exceptions import AuthError, ConnectError
import pytest

from menuai import config_entries
from menuai.components.vlc_telnet.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.service_info.menuaiio import menuaiioServiceInfo

from tests.common import MockConfigEntry


@pytest.mark.parametrize(
    ("input_data", "entry_data"),
    [
        (
            {
                "password": "test-password",
                "host": "1.1.1.1",
                "port": 8888,
            },
            {
                "password": "test-password",
                "host": "1.1.1.1",
                "port": 8888,
            },
        ),
        (
            {
                "password": "test-password",
            },
            {
                "password": "test-password",
                "host": "localhost",
                "port": 4212,
            },
        ),
    ],
)
async def test_user_flow(
    menuai: menuai, input_data: dict[str, Any], entry_data: dict[str, Any]
) -> None:
    """Test successful user flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with (
        patch("menuai.components.vlc_telnet.config_flow.Client.connect"),
        patch("menuai.components.vlc_telnet.config_flow.Client.login"),
        patch("menuai.components.vlc_telnet.config_flow.Client.disconnect"),
        patch(
            "menuai.components.vlc_telnet.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            input_data,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == entry_data["host"]
    assert result["data"] == entry_data
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize("source", [config_entries.SOURCE_USER])
async def test_abort_already_configured(menuai: menuai, source: str) -> None:
    """Test we handle already configured host."""
    entry_data = {
        "password": "test-password",
        "host": "1.1.1.1",
        "port": 8888,
        "name": "custom name",
    }

    entry = MockConfigEntry(domain=DOMAIN, data=entry_data)
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": source},
        data=entry_data,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize("source", [config_entries.SOURCE_USER])
@pytest.mark.parametrize(
    ("error", "connect_side_effect", "login_side_effect"),
    [
        ("invalid_auth", None, AuthError),
        ("cannot_connect", ConnectError, None),
        ("unknown", Exception, None),
    ],
)
async def test_errors(
    menuai: menuai,
    error: str,
    connect_side_effect: Exception | None,
    login_side_effect: Exception | None,
    source: str,
) -> None:
    """Test we handle form errors."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": source}
    )

    with (
        patch(
            "menuai.components.vlc_telnet.config_flow.Client.connect",
            side_effect=connect_side_effect,
        ),
        patch(
            "menuai.components.vlc_telnet.config_flow.Client.login",
            side_effect=login_side_effect,
        ),
        patch(
            "menuai.components.vlc_telnet.config_flow.Client.disconnect",
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"password": "test-password"},
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": error}


async def test_reauth_flow(menuai: menuai) -> None:
    """Test successful reauth flow."""
    entry_data: dict[str, Any] = {
        "password": "old-password",
        "host": "1.1.1.1",
        "port": 8888,
        "name": "custom name",
    }

    entry = MockConfigEntry(domain=DOMAIN, data=entry_data)
    entry.add_to_menuai(menuai)

    result = await entry.start_reauth_flow(menuai)

    with (
        patch("menuai.components.vlc_telnet.config_flow.Client.connect"),
        patch("menuai.components.vlc_telnet.config_flow.Client.login"),
        patch("menuai.components.vlc_telnet.config_flow.Client.disconnect"),
        patch(
            "menuai.components.vlc_telnet.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"password": "new-password"},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert len(mock_setup_entry.mock_calls) == 1
    assert dict(entry.data) == {**entry_data, "password": "new-password"}


@pytest.mark.parametrize(
    ("error", "connect_side_effect", "login_side_effect"),
    [
        ("invalid_auth", None, AuthError),
        ("cannot_connect", ConnectError, None),
        ("unknown", Exception, None),
    ],
)
async def test_reauth_errors(
    menuai: menuai,
    error: str,
    connect_side_effect: Exception | None,
    login_side_effect: Exception | None,
) -> None:
    """Test we handle reauth errors."""
    entry_data = {
        "password": "old-password",
        "host": "1.1.1.1",
        "port": 8888,
        "name": "custom name",
    }

    entry = MockConfigEntry(domain=DOMAIN, data=entry_data)
    entry.add_to_menuai(menuai)

    result = await entry.start_reauth_flow(menuai)

    with (
        patch(
            "menuai.components.vlc_telnet.config_flow.Client.connect",
            side_effect=connect_side_effect,
        ),
        patch(
            "menuai.components.vlc_telnet.config_flow.Client.login",
            side_effect=login_side_effect,
        ),
        patch(
            "menuai.components.vlc_telnet.config_flow.Client.disconnect",
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"password": "test-password"},
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": error}


async def test_menuaiio_flow(menuai: menuai) -> None:
    """Test successful menuaiio flow."""
    with (
        patch("menuai.components.vlc_telnet.config_flow.Client.connect"),
        patch("menuai.components.vlc_telnet.config_flow.Client.login"),
        patch("menuai.components.vlc_telnet.config_flow.Client.disconnect"),
        patch(
            "menuai.components.vlc_telnet.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        test_data = menuaiioServiceInfo(
            config={
                "password": "test-password",
                "host": "1.1.1.1",
                "port": 8888,
                "name": "custom name",
                "addon": "VLC",
            },
            name="VLC",
            slug="vlc",
            uuid="1234",
        )

        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_menuaiIO},
            data=test_data,
        )
        await menuai.async_block_till_done()

        assert result["type"] is FlowResultType.FORM

        result2 = await menuai.config_entries.flow.async_configure(result["flow_id"], {})

        assert result2["type"] is FlowResultType.CREATE_ENTRY
        assert result2["title"] == test_data.config["name"]
        assert result2["data"] == test_data.config
        assert len(mock_setup_entry.mock_calls) == 1


async def test_menuaiio_already_configured(menuai: menuai) -> None:
    """Test successful menuaiio flow."""

    entry_data = {
        "password": "test-password",
        "host": "1.1.1.1",
        "port": 8888,
        "name": "custom name",
        "addon": "vlc",
    }

    entry = MockConfigEntry(domain=DOMAIN, data=entry_data, unique_id="menuaiio")
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_menuaiIO},
        data=menuaiioServiceInfo(config=entry_data, name="VLC", slug="vlc", uuid="1234"),
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT


@pytest.mark.parametrize(
    ("error", "connect_side_effect", "login_side_effect"),
    [
        ("invalid_auth", None, AuthError),
        ("cannot_connect", ConnectError, None),
        ("unknown", Exception, None),
    ],
)
async def test_menuaiio_errors(
    menuai: menuai,
    error: str,
    connect_side_effect: Exception | None,
    login_side_effect: Exception | None,
) -> None:
    """Test we handle menuaiio errors."""
    with (
        patch(
            "menuai.components.vlc_telnet.config_flow.Client.connect",
            side_effect=connect_side_effect,
        ),
        patch(
            "menuai.components.vlc_telnet.config_flow.Client.login",
            side_effect=login_side_effect,
        ),
        patch(
            "menuai.components.vlc_telnet.config_flow.Client.disconnect",
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_menuaiIO},
            data=menuaiioServiceInfo(
                config={
                    "password": "test-password",
                    "host": "1.1.1.1",
                    "port": 8888,
                    "name": "custom name",
                    "addon": "VLC",
                },
                name="VLC",
                slug="vlc",
                uuid="1234",
            ),
        )
        await menuai.async_block_till_done()

        assert result["type"] is FlowResultType.FORM

        result2 = await menuai.config_entries.flow.async_configure(result["flow_id"], {})

        assert result2["type"] is FlowResultType.ABORT
        assert result2["reason"] == error
