"""Test the ibeacon config flow."""

from unittest.mock import patch

import pytest

from menuai import config_entries
from menuai.components.ibeacon.const import CONF_ALLOW_NAMELESS_UUIDS, DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


@pytest.mark.usefixtures("mock_bluetooth_adapters")
async def test_setup_user_no_bluetooth(menuai: menuai) -> None:
    """Test setting up via user interaction when bluetooth is not enabled."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "bluetooth_not_available"


@pytest.mark.usefixtures("enable_bluetooth")
async def test_setup_user(menuai: menuai) -> None:
    """Test setting up via user interaction with bluetooth enabled."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    with patch("menuai.components.ibeacon.async_setup_entry", return_value=True):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "iBeacon Tracker"
    assert result2["data"] == {}


@pytest.mark.usefixtures("enable_bluetooth")
async def test_setup_user_already_setup(menuai: menuai) -> None:
    """Test setting up via user when already setup ."""
    MockConfigEntry(domain=DOMAIN).add_to_menuai(menuai)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


@pytest.mark.usefixtures("enable_bluetooth")
async def test_options_flow(menuai: menuai) -> None:
    """Test config flow options."""
    config_entry = MockConfigEntry(domain=DOMAIN)
    config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    result = await menuai.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    # test save invalid uuid
    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "new_uuid": "invalid",
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    assert result["errors"] == {"new_uuid": "invalid_uuid_format"}

    # test save new uuid
    uuid = "daa4b6bb-b77a-4662-aeb8-b3ed56454091"
    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "new_uuid": uuid,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_ALLOW_NAMELESS_UUIDS: [uuid]}

    # test save duplicate uuid
    result = await menuai.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_ALLOW_NAMELESS_UUIDS: [uuid],
            "new_uuid": uuid,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_ALLOW_NAMELESS_UUIDS: [uuid]}

    # delete
    result = await menuai.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_ALLOW_NAMELESS_UUIDS: [],
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_ALLOW_NAMELESS_UUIDS: []}
