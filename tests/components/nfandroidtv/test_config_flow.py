"""Test NFAndroidTV config flow."""

from unittest.mock import patch

from notifications_android_tv.notifications import ConnectError

from menuai import config_entries
from menuai.components.nfandroidtv.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import (
    CONF_CONFIG_FLOW,
    CONF_DATA,
    HOST,
    NAME,
    _create_mocked_tv,
    _patch_config_flow_tv,
)

from tests.common import MockConfigEntry


def _patch_setup():
    return patch(
        "menuai.components.nfandroidtv.async_setup_entry",
        return_value=True,
    )


async def test_flow_user(menuai: menuai) -> None:
    """Test user initialized flow."""
    mocked_tv = await _create_mocked_tv()
    with _patch_config_flow_tv(mocked_tv), _patch_setup():
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=CONF_CONFIG_FLOW,
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == NAME
        assert result["data"] == CONF_DATA


async def test_flow_user_already_configured(menuai: menuai) -> None:
    """Test user initialized flow with duplicate server."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=CONF_CONFIG_FLOW,
        unique_id=HOST,
    )

    entry.add_to_menuai(menuai)

    mocked_tv = await _create_mocked_tv()
    with _patch_config_flow_tv(mocked_tv), _patch_setup():
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=CONF_CONFIG_FLOW,
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"


async def test_flow_user_cannot_connect(menuai: menuai) -> None:
    """Test user initialized flow with unreachable server."""
    mocked_tv = await _create_mocked_tv(True)
    with _patch_config_flow_tv(mocked_tv) as tvmock:
        tvmock.side_effect = ConnectError
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data=CONF_CONFIG_FLOW,
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": "cannot_connect"}


async def test_flow_user_unknown_error(menuai: menuai) -> None:
    """Test user initialized flow with unreachable server."""
    mocked_tv = await _create_mocked_tv(True)
    with _patch_config_flow_tv(mocked_tv) as tvmock:
        tvmock.side_effect = Exception
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data=CONF_CONFIG_FLOW,
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": "unknown"}
