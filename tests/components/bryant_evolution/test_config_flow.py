"""Test the Bryant Evolution config flow."""

from unittest.mock import DEFAULT, AsyncMock, patch

from evolutionhttp import BryantEvolutionLocalClient, ZoneInfo

from menuai import config_entries
from menuai.components.bryant_evolution.const import CONF_SYSTEM_ZONE, DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_FILENAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_form_success(menuai: menuai, mock_setup_entry: AsyncMock) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch.object(
            BryantEvolutionLocalClient,
            "enumerate_zones",
            return_value=DEFAULT,
        ) as mock_call,
    ):
        mock_call.side_effect = lambda system_id, filename: {
            1: [ZoneInfo(1, 1, "S1Z1"), ZoneInfo(1, 2, "S1Z2")],
            2: [ZoneInfo(2, 3, "S2Z2"), ZoneInfo(2, 4, "S2Z3")],
        }.get(system_id, [])
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_FILENAME: "test_form_success",
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY, result
    assert result["title"] == "SAM at test_form_success"
    assert result["data"] == {
        CONF_FILENAME: "test_form_success",
        CONF_SYSTEM_ZONE: [(1, 1), (1, 2), (2, 3), (2, 4)],
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(
    menuai: menuai,
    mock_evolution_client_factory: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with (
        patch.object(
            BryantEvolutionLocalClient,
            "enumerate_zones",
            return_value=DEFAULT,
        ) as mock_call,
    ):
        mock_call.return_value = []
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_FILENAME: "test_form_cannot_connect",
            },
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}

    with (
        patch.object(
            BryantEvolutionLocalClient,
            "enumerate_zones",
            return_value=DEFAULT,
        ) as mock_call,
    ):
        mock_call.side_effect = lambda system_id, filename: {
            1: [ZoneInfo(1, 1, "S1Z1"), ZoneInfo(1, 2, "S1Z2")],
            2: [ZoneInfo(2, 3, "S2Z3"), ZoneInfo(2, 4, "S2Z4")],
        }.get(system_id, [])
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_FILENAME: "some-serial",
            },
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "SAM at some-serial"
    assert result["data"] == {
        CONF_FILENAME: "some-serial",
        CONF_SYSTEM_ZONE: [(1, 1), (1, 2), (2, 3), (2, 4)],
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect_bad_file(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    mock_evolution_client_factory: AsyncMock,
) -> None:
    """Test we handle cannot connect error from a missing file."""
    mock_evolution_client_factory.side_effect = FileNotFoundError("test error")
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            # This file does not exist.
            CONF_FILENAME: "test_form_cannot_connect_bad_file",
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_reconfigure(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    mock_evolution_entry: MockConfigEntry,
) -> None:
    """Test that reconfigure discovers additional systems and zones."""

    # Reconfigure with additional systems and zones.
    result = await mock_evolution_entry.start_reconfigure_flow(menuai)
    with (
        patch.object(
            BryantEvolutionLocalClient,
            "enumerate_zones",
            return_value=DEFAULT,
        ) as mock_call,
    ):
        mock_call.side_effect = lambda system_id, filename: {
            1: [ZoneInfo(1, 1, "S1Z1")],
            2: [ZoneInfo(2, 3, "S2Z3"), ZoneInfo(2, 4, "S2Z4"), ZoneInfo(2, 5, "S2Z5")],
        }.get(system_id, [])
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_FILENAME: "test_reconfigure",
            },
        )
    await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT, result
    assert result["reason"] == "reconfigure_successful"
    config_entry = menuai.config_entries.async_entries()[0]
    assert config_entry.data[CONF_SYSTEM_ZONE] == [
        (1, 1),
        (2, 3),
        (2, 4),
        (2, 5),
    ]
