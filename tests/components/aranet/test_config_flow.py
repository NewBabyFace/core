"""Test the Aranet config flow."""

from unittest.mock import patch

from menuai import config_entries
from menuai.components.aranet.const import DOMAIN
from menuai.config_entries import SOURCE_IGNORE, SOURCE_USER
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import (
    DISABLED_INTEGRATIONS_SERVICE_INFO,
    NOT_ARANET4_SERVICE_INFO,
    OLD_FIRMWARE_SERVICE_INFO,
    VALID_DATA_SERVICE_INFO,
    VALID_DATA_SERVICE_INFO_WITH_NO_NAME,
)

from tests.common import MockConfigEntry


async def test_async_step_bluetooth_valid_device(menuai: menuai) -> None:
    """Test discovery via bluetooth with a valid device."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=VALID_DATA_SERVICE_INFO,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"
    with patch("menuai.components.aranet.async_setup_entry", return_value=True):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Aranet4 12345"
    assert result2["data"] == {}
    assert result2["result"].unique_id == "aa:bb:cc:dd:ee:ff"


async def test_async_step_bluetooth_device_without_name(menuai: menuai) -> None:
    """Test discovery via bluetooth with a valid device that has no name."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=VALID_DATA_SERVICE_INFO_WITH_NO_NAME,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"
    with patch("menuai.components.aranet.async_setup_entry", return_value=True):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Aranet (EEFF)"
    assert result2["data"] == {}
    assert result2["result"].unique_id == "aa:bb:cc:dd:ee:ff"


async def test_async_step_bluetooth_not_aranet4(menuai: menuai) -> None:
    """Test that we reject discovery via Bluetooth for an unrelated device."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=NOT_ARANET4_SERVICE_INFO,
    )
    assert result["type"] is FlowResultType.ABORT


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
        data=VALID_DATA_SERVICE_INFO,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_async_step_bluetooth_already_in_progress(menuai: menuai) -> None:
    """Test we can't start a flow for the same device twice."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=VALID_DATA_SERVICE_INFO,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=VALID_DATA_SERVICE_INFO,
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
        data=VALID_DATA_SERVICE_INFO,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"

    with patch(
        "menuai.components.aranet.config_flow.async_discovered_service_info",
        return_value=[VALID_DATA_SERVICE_INFO],
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        assert result["type"] is FlowResultType.FORM

    with patch("menuai.components.aranet.async_setup_entry", return_value=True):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"address": "aa:bb:cc:dd:ee:ff"},
        )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Aranet4 12345"
    assert result2["data"] == {}
    assert result2["result"].unique_id == "aa:bb:cc:dd:ee:ff"

    # Verify the original one was aborted
    assert not menuai.config_entries.flow.async_progress(DOMAIN)


async def test_async_step_user_no_devices_found(menuai: menuai) -> None:
    """Test setup from service info cache with no devices found."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


async def test_async_step_user_only_other_devices_found(menuai: menuai) -> None:
    """Test setup from service info cache with only other devices found."""
    with patch(
        "menuai.components.aranet.config_flow.async_discovered_service_info",
        return_value=[NOT_ARANET4_SERVICE_INFO],
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


async def test_async_step_user_with_found_devices(menuai: menuai) -> None:
    """Test setup from service info cache with devices found."""
    with patch(
        "menuai.components.aranet.config_flow.async_discovered_service_info",
        return_value=[VALID_DATA_SERVICE_INFO],
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    with patch("menuai.components.aranet.async_setup_entry", return_value=True):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"address": "aa:bb:cc:dd:ee:ff"},
        )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Aranet4 12345"
    assert result2["data"] == {}
    assert result2["result"].unique_id == "aa:bb:cc:dd:ee:ff"


async def test_async_step_user_device_added_between_steps(menuai: menuai) -> None:
    """Test the device gets added via another flow between steps."""
    with patch(
        "menuai.components.aranet.config_flow.async_discovered_service_info",
        return_value=[VALID_DATA_SERVICE_INFO],
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

    with patch("menuai.components.aranet.async_setup_entry", return_value=True):
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
        "menuai.components.aranet.config_flow.async_discovered_service_info",
        return_value=[VALID_DATA_SERVICE_INFO],
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


async def test_async_step_user_old_firmware(menuai: menuai) -> None:
    """Test we can't set up a device with firmware too old to report measurements."""
    with patch(
        "menuai.components.aranet.config_flow.async_discovered_service_info",
        return_value=[OLD_FIRMWARE_SERVICE_INFO],
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    with patch("menuai.components.aranet.async_setup_entry", return_value=True):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"address": "aa:bb:cc:dd:ee:ff"},
        )
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "outdated_version"


async def test_async_step_user_integrations_disabled(menuai: menuai) -> None:
    """Test we can't set up a device the device's integration setting disabled."""
    with patch(
        "menuai.components.aranet.config_flow.async_discovered_service_info",
        return_value=[DISABLED_INTEGRATIONS_SERVICE_INFO],
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    with patch("menuai.components.aranet.async_setup_entry", return_value=True):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"address": "aa:bb:cc:dd:ee:ff"},
        )
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "integrations_disabled"


async def test_user_setup_replaces_ignored_device(menuai: menuai) -> None:
    """Test the user initiated form can replace an ignored device."""
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="aa:bb:cc:dd:ee:ff", source=SOURCE_IGNORE
    )
    entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.aranet.config_flow.async_discovered_service_info",
        return_value=[VALID_DATA_SERVICE_INFO],
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch("menuai.components.aranet.async_setup_entry", return_value=True):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={"address": "aa:bb:cc:dd:ee:ff"}
        )
    await menuai.async_block_till_done()
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Aranet4 12345"
    assert result2["data"] == {}
    assert result2["result"].unique_id == "aa:bb:cc:dd:ee:ff"
