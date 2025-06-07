"""Tests for the deako component config flow."""

from unittest.mock import MagicMock

from pydeako.discover import DevicesNotFoundException

from menuai.components.deako.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_found(
    menuai: menuai,
    pydeako_discoverer_mock: MagicMock,
    mock_deako_setup: MagicMock,
) -> None:
    """Test finding a Deako device."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    # Confirmation form
    assert result["type"] is FlowResultType.FORM

    result = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    pydeako_discoverer_mock.return_value.get_address.assert_called_once()

    mock_deako_setup.assert_called_once()


async def test_not_found(
    menuai: menuai,
    pydeako_discoverer_mock: MagicMock,
    mock_deako_setup: MagicMock,
) -> None:
    """Test not finding any Deako devices."""
    pydeako_discoverer_mock.return_value.get_address.side_effect = (
        DevicesNotFoundException()
    )

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    # Confirmation form
    assert result["type"] is FlowResultType.FORM

    result = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"
    pydeako_discoverer_mock.return_value.get_address.assert_called_once()

    mock_deako_setup.assert_not_called()


async def test_already_configured(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_deako_setup: MagicMock,
) -> None:
    """Test flow aborts when already configured."""

    mock_config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"

    mock_deako_setup.assert_not_called()
