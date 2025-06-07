"""Test the Google Translate text-to-speech config flow."""

from unittest.mock import AsyncMock

import pytest

from menuai import config_entries
from menuai.components.google_translate.const import CONF_TLD, DOMAIN
from menuai.components.tts import CONF_LANG
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


async def test_user_step(menuai: menuai, mock_setup_entry: AsyncMock) -> None:
    """Test user step create entry result."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_LANG: "de",
            CONF_TLD: "de",
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Google Translate text-to-speech"
    assert result["data"] == {
        CONF_LANG: "de",
        CONF_TLD: "de",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_already_configured(
    menuai: menuai, mock_setup_entry: AsyncMock
) -> None:
    """Test user step already configured entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_LANG: "de", CONF_TLD: "de"}
    )
    config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_LANG: "de",
            CONF_TLD: "de",
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert len(mock_setup_entry.mock_calls) == 0


async def test_onboarding_flow(
    menuai: menuai, mock_setup_entry: AsyncMock
) -> None:
    """Test the onboarding configuration flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": "onboarding"}
    )

    assert result.get("type") is FlowResultType.CREATE_ENTRY
    assert result.get("title") == "Google Translate text-to-speech"
    assert result.get("data") == {
        CONF_LANG: "en",
        CONF_TLD: "com",
    }

    assert len(mock_setup_entry.mock_calls) == 1
