"""Test the Epic Games Store config flow."""

from http.client import HTTPException
from unittest.mock import patch

from menuai import config_entries
from menuai.components.epic_games_store.config_flow import get_default_language
from menuai.components.epic_games_store.const import DOMAIN
from menuai.const import CONF_COUNTRY, CONF_LANGUAGE
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .const import (
    DATA_ERROR_ATTRIBUTE_NOT_FOUND,
    DATA_ERROR_WRONG_COUNTRY,
    DATA_FREE_GAMES,
    MOCK_COUNTRY,
    MOCK_LANGUAGE,
)


async def test_default_language(menuai: menuai) -> None:
    """Test we get the form."""
    menuai.config.language = "fr"
    menuai.config.country = "FR"
    assert get_default_language(menuai) == "fr"

    menuai.config.language = "es"
    menuai.config.country = "ES"
    assert get_default_language(menuai) == "es-ES"

    menuai.config.language = "en"
    menuai.config.country = "AZ"
    assert get_default_language(menuai) is None


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] is None

    with patch(
        "menuai.components.epic_games_store.config_flow.EpicGamesStoreAPI.get_free_games",
        return_value=DATA_FREE_GAMES,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_LANGUAGE: MOCK_LANGUAGE,
                CONF_COUNTRY: MOCK_COUNTRY,
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["result"].unique_id == f"freegames-{MOCK_LANGUAGE}-{MOCK_COUNTRY}"
    assert (
        result2["title"]
        == f"Epic Games Store - Free Games ({MOCK_LANGUAGE}-{MOCK_COUNTRY})"
    )
    assert result2["data"] == {
        CONF_LANGUAGE: MOCK_LANGUAGE,
        CONF_COUNTRY: MOCK_COUNTRY,
    }


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.epic_games_store.config_flow.EpicGamesStoreAPI.get_free_games",
        side_effect=HTTPException,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_LANGUAGE: MOCK_LANGUAGE,
                CONF_COUNTRY: MOCK_COUNTRY,
            },
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_form_cannot_connect_wrong_param(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.epic_games_store.config_flow.EpicGamesStoreAPI.get_free_games",
        return_value=DATA_ERROR_WRONG_COUNTRY,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_LANGUAGE: MOCK_LANGUAGE,
                CONF_COUNTRY: MOCK_COUNTRY,
            },
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_form_service_error(menuai: menuai) -> None:
    """Test we handle service error gracefully."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.epic_games_store.config_flow.EpicGamesStoreAPI.get_free_games",
        return_value=DATA_ERROR_ATTRIBUTE_NOT_FOUND,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_LANGUAGE: MOCK_LANGUAGE,
                CONF_COUNTRY: MOCK_COUNTRY,
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["result"].unique_id == f"freegames-{MOCK_LANGUAGE}-{MOCK_COUNTRY}"
    assert (
        result2["title"]
        == f"Epic Games Store - Free Games ({MOCK_LANGUAGE}-{MOCK_COUNTRY})"
    )
    assert result2["data"] == {
        CONF_LANGUAGE: MOCK_LANGUAGE,
        CONF_COUNTRY: MOCK_COUNTRY,
    }
