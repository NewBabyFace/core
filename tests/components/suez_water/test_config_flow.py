"""Test the Suez Water config flow."""

from unittest.mock import AsyncMock

from pysuez.exception import PySuezError
import pytest

from menuai import config_entries
from menuai.components.recorder import Recorder
from menuai.components.suez_water.const import CONF_COUNTER_ID, DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .conftest import MOCK_DATA

from tests.common import MockConfigEntry


async def test_form(
    menuai: menuai, mock_setup_entry: AsyncMock, suez_client: AsyncMock
) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        MOCK_DATA,
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == MOCK_DATA[CONF_COUNTER_ID]
    assert result["result"].unique_id == MOCK_DATA[CONF_COUNTER_ID]
    assert result["data"] == MOCK_DATA
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(
    menuai: menuai, mock_setup_entry: AsyncMock, suez_client: AsyncMock
) -> None:
    """Test we handle invalid auth."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    suez_client.check_credentials.return_value = False
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        MOCK_DATA,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}

    suez_client.check_credentials.return_value = True
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        MOCK_DATA,
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == MOCK_DATA[CONF_COUNTER_ID]
    assert result["result"].unique_id == MOCK_DATA[CONF_COUNTER_ID]
    assert result["data"] == MOCK_DATA
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_already_configured(
    menuai: menuai, recorder_mock: Recorder, suez_client: AsyncMock
) -> None:
    """Test we abort when entry is already configured."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_DATA[CONF_COUNTER_ID],
        data=MOCK_DATA,
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        MOCK_DATA,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    ("exception", "error"), [(PySuezError, "cannot_connect"), (Exception, "unknown")]
)
async def test_form_error(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    exception: Exception,
    suez_client: AsyncMock,
    error: str,
) -> None:
    """Test we handle errors."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    suez_client.check_credentials.side_effect = exception
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        MOCK_DATA,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    suez_client.check_credentials.return_value = True
    suez_client.check_credentials.side_effect = None
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        MOCK_DATA,
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == MOCK_DATA[CONF_COUNTER_ID]
    assert result["data"] == MOCK_DATA
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_auto_counter(
    menuai: menuai, mock_setup_entry: AsyncMock, suez_client: AsyncMock
) -> None:
    """Test form set counter if not set by user."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    partial_form = MOCK_DATA.copy()
    partial_form.pop(CONF_COUNTER_ID)
    suez_client.find_counter.side_effect = PySuezError("test counter not found")

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        partial_form,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "counter_not_found"}

    suez_client.find_counter.side_effect = None
    suez_client.find_counter.return_value = MOCK_DATA[CONF_COUNTER_ID]
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        partial_form,
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == MOCK_DATA[CONF_COUNTER_ID]
    assert result["result"].unique_id == MOCK_DATA[CONF_COUNTER_ID]
    assert result["data"] == MOCK_DATA
    assert len(mock_setup_entry.mock_calls) == 1
