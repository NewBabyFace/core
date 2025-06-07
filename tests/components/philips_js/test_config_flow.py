"""Test the Philips TV config flow."""

from unittest.mock import ANY

from haphilipsjs import PairingFailure
import pytest

from menuai import config_entries
from menuai.components.philips_js.const import CONF_ALLOW_NOTIFY, DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import (
    MOCK_CONFIG,
    MOCK_CONFIG_PAIRED,
    MOCK_PASSWORD,
    MOCK_SYSTEM,
    MOCK_SYSTEM_UNPAIRED,
    MOCK_USERINPUT,
    MOCK_USERNAME,
)

from tests.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


@pytest.fixture
async def mock_tv_pairable(mock_tv):
    """Return a mock tv that is pariable."""
    mock_tv.system = MOCK_SYSTEM_UNPAIRED
    mock_tv.pairing_type = "digest_auth_pairing"
    mock_tv.api_version = 6
    mock_tv.api_version_detected = 6
    mock_tv.secured_transport = True

    mock_tv.pairRequest.return_value = {}
    mock_tv.pairGrant.return_value = MOCK_USERNAME, MOCK_PASSWORD
    return mock_tv


async def test_form(menuai: menuai, mock_setup_entry) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        MOCK_USERINPUT,
    )
    await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Philips TV (1234567890)"
    assert result2["data"] == MOCK_CONFIG
    assert len(mock_setup_entry.mock_calls) == 1


async def test_reauth(
    menuai: menuai, mock_setup_entry, mock_config_entry: MockConfigEntry, mock_tv
) -> None:
    """Test we get the form."""

    mock_tv.system = MOCK_SYSTEM | {"model": "changed"}

    assert await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    assert len(mock_setup_entry.mock_calls) == 1

    result = await mock_config_entry.start_reauth_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        MOCK_USERINPUT,
    )
    await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"
    assert mock_config_entry.data == MOCK_CONFIG | {"system": mock_tv.system}
    assert len(mock_setup_entry.mock_calls) == 2


async def test_form_cannot_connect(menuai: menuai, mock_tv) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_tv.system = None
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], MOCK_USERINPUT
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_form_unexpected_error(menuai: menuai, mock_tv) -> None:
    """Test we handle unexpected exceptions."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_tv.getSystem.side_effect = Exception("Unexpected exception")
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], MOCK_USERINPUT
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


async def test_pairing(menuai: menuai, mock_tv_pairable, mock_setup_entry) -> None:
    """Test we get the form."""
    mock_tv = mock_tv_pairable

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        MOCK_USERINPUT,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    mock_tv.setTransport.assert_called_with(True)
    mock_tv.pairRequest.assert_called()

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {"pin": "1234"}
    )

    assert result == {
        "context": {"source": "user", "unique_id": "ABCDEFGHIJKLF"},
        "flow_id": ANY,
        "type": "create_entry",
        "description": None,
        "description_placeholders": None,
        "handler": "philips_js",
        "result": ANY,
        "title": "55PUS7181/12 (ABCDEFGHIJKLF)",
        "data": MOCK_CONFIG_PAIRED,
        "version": 1,
        "options": {},
        "minor_version": 1,
        "subentries": (),
    }

    await menuai.async_block_till_done()
    assert len(mock_setup_entry.mock_calls) == 1


async def test_pair_request_failed(
    menuai: menuai, mock_tv_pairable, mock_setup_entry
) -> None:
    """Test we get the form."""
    mock_tv = mock_tv_pairable
    mock_tv.pairRequest.side_effect = PairingFailure({})

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        MOCK_USERINPUT,
    )

    assert result == {
        "flow_id": ANY,
        "description_placeholders": {"error_id": None},
        "handler": "philips_js",
        "reason": "pairing_failure",
        "type": "abort",
    }


async def test_pair_grant_failed(
    menuai: menuai, mock_tv_pairable, mock_setup_entry
) -> None:
    """Test we get the form."""
    mock_tv = mock_tv_pairable

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        MOCK_USERINPUT,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    mock_tv.setTransport.assert_called_with(True)
    mock_tv.pairRequest.assert_called()

    # Test with invalid pin
    mock_tv.pairGrant.side_effect = PairingFailure({"error_id": "INVALID_PIN"})
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {"pin": "1234"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"pin": "invalid_pin"}

    # Test with unexpected failure
    mock_tv.pairGrant.side_effect = PairingFailure({})
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {"pin": "1234"}
    )

    assert result == {
        "flow_id": ANY,
        "description_placeholders": {"error_id": None},
        "handler": "philips_js",
        "reason": "pairing_failure",
        "type": "abort",
    }


async def test_options_flow(menuai: menuai) -> None:
    """Test config flow options."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="123456",
        data=MOCK_CONFIG_PAIRED,
    )
    config_entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    result = await menuai.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_ALLOW_NOTIFY: True}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {CONF_ALLOW_NOTIFY: True}
