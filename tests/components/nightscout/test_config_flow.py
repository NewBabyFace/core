"""Test the Nightscout config flow."""

from http import HTTPStatus
from unittest.mock import patch

from aiohttp import ClientConnectionError, ClientResponseError

from menuai import config_entries
from menuai.components.nightscout.const import DOMAIN
from menuai.components.nightscout.utils import hash_from_url
from menuai.const import CONF_URL
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import GLUCOSE_READINGS, SERVER_STATUS, SERVER_STATUS_STATUS_ONLY

from tests.common import MockConfigEntry

CONFIG = {CONF_URL: "https://some.url:1234"}


async def test_form(menuai: menuai) -> None:
    """Test we get the user initiated form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        _patch_glucose_readings(),
        _patch_server_status(),
        _patch_async_setup_entry() as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            CONFIG,
        )

        assert result2["type"] is FlowResultType.CREATE_ENTRY
        assert result2["title"] == SERVER_STATUS.name  # pylint: disable=maybe-no-member
        assert result2["data"] == CONFIG
        await menuai.async_block_till_done()
        assert len(mock_setup_entry.mock_calls) == 1


async def test_user_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.nightscout.NightscoutAPI.get_server_status",
        side_effect=ClientConnectionError(),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_URL: "https://some.url:1234"},
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_user_form_api_key_required(menuai: menuai) -> None:
    """Test we handle an unauthorized error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch(
            "menuai.components.nightscout.NightscoutAPI.get_server_status",
            return_value=SERVER_STATUS_STATUS_ONLY,
        ),
        patch(
            "menuai.components.nightscout.NightscoutAPI.get_sgvs",
            side_effect=ClientResponseError(None, None, status=HTTPStatus.UNAUTHORIZED),
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_URL: "https://some.url:1234"},
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_user_form_unexpected_exception(menuai: menuai) -> None:
    """Test we handle unexpected exception."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.nightscout.NightscoutAPI.get_server_status",
        side_effect=Exception(),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_URL: "https://some.url:1234"},
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_user_form_duplicate(menuai: menuai) -> None:
    """Test duplicate entries."""
    with _patch_glucose_readings(), _patch_server_status():
        unique_id = hash_from_url(CONFIG[CONF_URL])
        entry = MockConfigEntry(domain=DOMAIN, unique_id=unique_id)
        entry.add_to_menuai(menuai)

        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data=CONFIG,
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"


def _patch_async_setup_entry():
    return patch(
        "menuai.components.nightscout.async_setup_entry",
        return_value=True,
    )


def _patch_glucose_readings():
    return patch(
        "menuai.components.nightscout.NightscoutAPI.get_sgvs",
        return_value=GLUCOSE_READINGS,
    )


def _patch_server_status():
    return patch(
        "menuai.components.nightscout.NightscoutAPI.get_server_status",
        return_value=SERVER_STATUS,
    )
