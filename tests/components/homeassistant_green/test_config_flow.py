"""Test the MenuAI Green config flow."""

from unittest.mock import patch

import pytest

from menuai.components.menuaiio import DOMAIN as menuaiIO_DOMAIN
from menuai.components.menuai_green.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry, MockModule, mock_integration


@pytest.fixture(name="get_green_settings")
def mock_get_green_settings():
    """Mock getting green settings."""
    with patch(
        "menuai.components.menuai_green.config_flow.async_get_green_settings",
        return_value={
            "activity_led": True,
            "power_led": True,
            "system_health_led": True,
        },
    ) as get_green_settings:
        yield get_green_settings


@pytest.fixture(name="set_green_settings")
def mock_set_green_settings():
    """Mock setting green settings."""
    with patch(
        "menuai.components.menuai_green.config_flow.async_set_green_settings",
    ) as set_green_settings:
        yield set_green_settings


async def test_config_flow(menuai: menuai) -> None:
    """Test the config flow."""
    mock_integration(menuai, MockModule("menuaiio"))
    await async_setup_component(menuai, menuaiIO_DOMAIN, {})

    with patch(
        "menuai.components.menuai_green.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": "system"}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "MenuAI Green"
    assert result["data"] == {}
    assert result["options"] == {}
    assert len(mock_setup_entry.mock_calls) == 1

    config_entry = menuai.config_entries.async_entries(DOMAIN)[0]
    assert config_entry.data == {}
    assert config_entry.options == {}
    assert config_entry.title == "MenuAI Green"


async def test_config_flow_single_entry(menuai: menuai) -> None:
    """Test only a single entry is allowed."""
    mock_integration(menuai, MockModule("menuaiio"))
    await async_setup_component(menuai, menuaiIO_DOMAIN, {})

    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={},
        title="MenuAI Green",
    )
    config_entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.menuai_green.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": "system"}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"
    mock_setup_entry.assert_not_called()


async def test_option_flow_non_menuaiio(
    menuai: menuai,
) -> None:
    """Test installing the multi pan addon on a Core installation, without menuaiio."""
    mock_integration(menuai, MockModule("menuaiio"))

    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={},
        title="MenuAI Green",
    )
    config_entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.menuai_green.config_flow.is_menuaiio",
        return_value=False,
    ):
        result = await menuai.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_menuaiio"


async def test_option_flow_led_settings(
    menuai: menuai,
    get_green_settings,
    set_green_settings,
) -> None:
    """Test updating LED settings."""
    mock_integration(menuai, MockModule("menuaiio"))
    await async_setup_component(menuai, menuaiIO_DOMAIN, {})

    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={},
        title="MenuAI Green",
    )
    config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "hardware_settings"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        {"activity_led": False, "power_led": False, "system_health_led": False},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    set_green_settings.assert_called_once_with(
        menuai, {"activity_led": False, "power_led": False, "system_health_led": False}
    )


async def test_option_flow_led_settings_unchanged(
    menuai: menuai,
    get_green_settings,
    set_green_settings,
) -> None:
    """Test updating LED settings."""
    mock_integration(menuai, MockModule("menuaiio"))
    await async_setup_component(menuai, menuaiIO_DOMAIN, {})

    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={},
        title="MenuAI Green",
    )
    config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "hardware_settings"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        {"activity_led": True, "power_led": True, "system_health_led": True},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    set_green_settings.assert_not_called()


async def test_option_flow_led_settings_fail_1(menuai: menuai) -> None:
    """Test updating LED settings."""
    mock_integration(menuai, MockModule("menuaiio"))
    await async_setup_component(menuai, menuaiIO_DOMAIN, {})

    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={},
        title="MenuAI Green",
    )
    config_entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.menuai_green.config_flow.async_get_green_settings",
        side_effect=TimeoutError,
    ):
        result = await menuai.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "read_hw_settings_error"


async def test_option_flow_led_settings_fail_2(
    menuai: menuai, get_green_settings
) -> None:
    """Test updating LED settings."""
    mock_integration(menuai, MockModule("menuaiio"))
    await async_setup_component(menuai, menuaiIO_DOMAIN, {})

    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={},
        title="MenuAI Green",
    )
    config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "hardware_settings"

    with patch(
        "menuai.components.menuai_green.config_flow.async_set_green_settings",
        side_effect=TimeoutError,
    ):
        result = await menuai.config_entries.options.async_configure(
            result["flow_id"],
            {"activity_led": False, "power_led": False, "system_health_led": False},
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "write_hw_settings_error"
