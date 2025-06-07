"""Tests for the Open-Meteo config flow."""

from unittest.mock import MagicMock

from menuai.components.open_meteo.const import DOMAIN
from menuai.components.zone import ENTITY_ID_HOME
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_ZONE
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType


async def test_full_user_flow(
    menuai: menuai,
    mock_setup_entry: MagicMock,
) -> None:
    """Test the full user configuration flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "user"

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_ZONE: ENTITY_ID_HOME},
    )

    assert result2.get("type") is FlowResultType.CREATE_ENTRY
    assert result2.get("title") == "test home"
    assert result2.get("data") == {CONF_ZONE: ENTITY_ID_HOME}
