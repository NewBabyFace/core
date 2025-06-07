"""Test Anova config flow."""

from unittest.mock import patch

from anova_wifi import AnovaApi, InvalidLogin

from menuai import config_entries
from menuai.components.anova.const import DOMAIN
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import CONF_INPUT


async def test_flow_user(menuai: menuai, anova_api: AnovaApi) -> None:
    """Test user initialized flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=CONF_INPUT,
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_USERNAME: "sample@gmail.com",
        CONF_PASSWORD: "sample",
    }


async def test_flow_wrong_login(menuai: menuai) -> None:
    """Test incorrect login throwing error."""
    with patch(
        "menuai.components.anova.config_flow.AnovaApi.authenticate",
        side_effect=InvalidLogin,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=CONF_INPUT,
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "invalid_auth"}


async def test_flow_unknown_error(menuai: menuai) -> None:
    """Test unknown error throwing error."""
    with patch(
        "menuai.components.anova.config_flow.AnovaApi.authenticate",
        side_effect=Exception(),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=CONF_INPUT,
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "unknown"}
