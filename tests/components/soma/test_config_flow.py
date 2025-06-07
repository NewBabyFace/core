"""Tests for the Soma config flow."""

from unittest.mock import patch

from api.soma_api import SomaApi
from requests import RequestException

from menuai.components.soma import DOMAIN
from menuai.config_entries import SOURCE_IMPORT, SOURCE_USER
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

MOCK_HOST = "123.45.67.89"
MOCK_PORT = 3000


async def test_form(menuai: menuai) -> None:
    """Test user form showing."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM


async def test_import_abort(menuai: menuai) -> None:
    """Test configuration from YAML aborting with existing entity."""
    MockConfigEntry(domain=DOMAIN).add_to_menuai(menuai)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_IMPORT}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_setup"


async def test_import_create(menuai: menuai) -> None:
    """Test configuration from YAML."""
    with patch.object(SomaApi, "list_devices", return_value={"result": "success"}):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data={"host": MOCK_HOST, "port": MOCK_PORT},
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_error_status(menuai: menuai) -> None:
    """Test Connect successfully returning error status."""
    with patch.object(SomaApi, "list_devices", return_value={"result": "error"}):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data={"host": MOCK_HOST, "port": MOCK_PORT},
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "result_error"


async def test_key_error(menuai: menuai) -> None:
    """Test Connect returning empty string."""

    with patch.object(SomaApi, "list_devices", return_value={}):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data={"host": MOCK_HOST, "port": MOCK_PORT},
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "connection_error"


async def test_exception(menuai: menuai) -> None:
    """Test if RequestException fires when no connection can be made."""
    with patch.object(SomaApi, "list_devices", side_effect=RequestException()):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data={"host": MOCK_HOST, "port": MOCK_PORT},
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "connection_error"


async def test_full_flow(menuai: menuai) -> None:
    """Check classic use case."""
    menuai.data[DOMAIN] = {}
    with patch.object(SomaApi, "list_devices", return_value={"result": "success"}):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={"host": MOCK_HOST, "port": MOCK_PORT},
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
