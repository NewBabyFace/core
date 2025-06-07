"""Test the Mopeka config flow."""

from unittest.mock import patch

import voluptuous as vol

from menuai import config_entries
from menuai.components.mopeka.const import CONF_MEDIUM_TYPE, DOMAIN, MediumType
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import NOT_MOPEKA_SERVICE_INFO, PRO_SERVICE_INFO

from tests.common import MockConfigEntry


async def test_async_step_bluetooth_valid_device(menuai: menuai) -> None:
    """Test discovery via bluetooth with a valid device."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=PRO_SERVICE_INFO,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"

    with patch("menuai.components.mopeka.async_setup_entry", return_value=True):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_MEDIUM_TYPE: MediumType.PROPANE.value}
        )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Pro Plus EEFF"
    assert result2["data"] == {CONF_MEDIUM_TYPE: MediumType.PROPANE.value}
    assert result2["result"].unique_id == "aa:bb:cc:dd:ee:ff"


async def test_async_step_bluetooth_not_mopeka(menuai: menuai) -> None:
    """Test discovery via bluetooth not mopeka."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=NOT_MOPEKA_SERVICE_INFO,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_supported"


async def test_async_step_user_no_devices_found(menuai: menuai) -> None:
    """Test setup from service info cache with no devices found."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


async def test_async_step_user_with_found_devices(menuai: menuai) -> None:
    """Test setup from service info cache with devices found."""
    with patch(
        "menuai.components.mopeka.config_flow.async_discovered_service_info",
        return_value=[PRO_SERVICE_INFO],
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    with patch("menuai.components.mopeka.async_setup_entry", return_value=True):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"address": "aa:bb:cc:dd:ee:ff"},
        )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Pro Plus EEFF"
    assert CONF_MEDIUM_TYPE in result2["data"]
    assert result2["data"][CONF_MEDIUM_TYPE] in [
        medium_type.value for medium_type in MediumType
    ]
    assert result2["result"].unique_id == "aa:bb:cc:dd:ee:ff"


async def test_async_step_user_replace_ignored(menuai: menuai) -> None:
    """Test setup from service info can replace an ignored entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=PRO_SERVICE_INFO.address,
        data={},
        source=config_entries.SOURCE_IGNORE,
    )
    entry.add_to_menuai(menuai)
    with patch(
        "menuai.components.mopeka.config_flow.async_discovered_service_info",
        return_value=[PRO_SERVICE_INFO],
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    with patch("menuai.components.mopeka.async_setup_entry", return_value=True):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"address": "aa:bb:cc:dd:ee:ff"},
        )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Pro Plus EEFF"
    assert CONF_MEDIUM_TYPE in result2["data"]
    assert result2["data"][CONF_MEDIUM_TYPE] in [
        medium_type.value for medium_type in MediumType
    ]
    assert result2["result"].unique_id == "aa:bb:cc:dd:ee:ff"


async def test_async_step_user_device_added_between_steps(menuai: menuai) -> None:
    """Test the device gets added via another flow between steps."""
    with patch(
        "menuai.components.mopeka.config_flow.async_discovered_service_info",
        return_value=[PRO_SERVICE_INFO],
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="aa:bb:cc:dd:ee:ff",
    )
    entry.add_to_menuai(menuai)

    with patch("menuai.components.mopeka.async_setup_entry", return_value=True):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"address": "aa:bb:cc:dd:ee:ff"},
        )
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_async_step_user_with_found_devices_already_setup(
    menuai: menuai,
) -> None:
    """Test setup from service info cache with devices found."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="aa:bb:cc:dd:ee:ff",
    )
    entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.mopeka.config_flow.async_discovered_service_info",
        return_value=[PRO_SERVICE_INFO],
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


async def test_async_step_bluetooth_devices_already_setup(menuai: menuai) -> None:
    """Test we can't start a flow if there is already a config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="aa:bb:cc:dd:ee:ff",
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=PRO_SERVICE_INFO,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_async_step_bluetooth_already_in_progress(menuai: menuai) -> None:
    """Test we can't start a flow for the same device twice."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=PRO_SERVICE_INFO,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=PRO_SERVICE_INFO,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_in_progress"


async def test_async_step_user_takes_precedence_over_discovery(
    menuai: menuai,
) -> None:
    """Test manual setup takes precedence over discovery."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=PRO_SERVICE_INFO,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"

    with patch(
        "menuai.components.mopeka.config_flow.async_discovered_service_info",
        return_value=[PRO_SERVICE_INFO],
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        assert result["type"] is FlowResultType.FORM

    with patch("menuai.components.mopeka.async_setup_entry", return_value=True):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"address": "aa:bb:cc:dd:ee:ff"},
        )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Pro Plus EEFF"
    assert CONF_MEDIUM_TYPE in result2["data"]
    assert result2["data"][CONF_MEDIUM_TYPE] in [
        medium_type.value for medium_type in MediumType
    ]
    assert result2["result"].unique_id == "aa:bb:cc:dd:ee:ff"

    # Verify the original one was aborted
    assert not menuai.config_entries.flow.async_progress(DOMAIN)


async def test_async_step_reconfigure_options(menuai: menuai) -> None:
    """Test reconfig options: change MediumType from air to fresh water."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="aa:bb:cc:dd:75:10",
        title="TD40/TD200 7510",
        data={CONF_MEDIUM_TYPE: MediumType.AIR.value},
    )
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.data[CONF_MEDIUM_TYPE] == MediumType.AIR.value

    result = await menuai.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"
    schema: vol.Schema = result["data_schema"]
    medium_type_key = next(
        iter(key for key in schema.schema if key == CONF_MEDIUM_TYPE)
    )
    assert medium_type_key.default() == MediumType.AIR.value

    result2 = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_MEDIUM_TYPE: MediumType.FRESH_WATER.value},
    )
    assert result2["type"] == FlowResultType.CREATE_ENTRY

    # Verify the new configuration
    assert entry.data[CONF_MEDIUM_TYPE] == MediumType.FRESH_WATER.value
