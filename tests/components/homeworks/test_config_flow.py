"""Test Lutron Homeworks Series 4 and 8 config flow."""

from unittest.mock import ANY, MagicMock

from pyhomeworks import exceptions as hw_exceptions
import pytest
from pytest_unordered import unordered

from menuai.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from menuai.components.button import DOMAIN as BUTTON_DOMAIN
from menuai.components.homeworks.const import (
    CONF_ADDR,
    CONF_INDEX,
    CONF_LED,
    CONF_NUMBER,
    CONF_RATE,
    CONF_RELEASE_DELAY,
    DOMAIN,
)
from menuai.config_entries import SOURCE_USER
from menuai.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
)
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_user_flow(
    menuai: menuai, mock_homeworks: MagicMock, mock_setup_entry
) -> None:
    """Test the user configuration flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    mock_controller = MagicMock()
    mock_homeworks.return_value = mock_controller
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: "192.168.0.1",
            CONF_NAME: "Main controller",
            CONF_PORT: 1234,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Main controller"
    assert result["data"] == {"password": None, "username": None}
    assert result["options"] == {
        "controller_id": "main_controller",
        "dimmers": [],
        "host": "192.168.0.1",
        "keypads": [],
        "port": 1234,
    }
    mock_homeworks.assert_called_once_with("192.168.0.1", 1234, ANY, None, None)
    mock_controller.close.assert_called_once_with()
    mock_controller.join.assert_not_called()


async def test_user_flow_credentials(
    menuai: menuai, mock_homeworks: MagicMock, mock_setup_entry
) -> None:
    """Test the user configuration flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    mock_controller = MagicMock()
    mock_homeworks.return_value = mock_controller
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: "192.168.0.1",
            CONF_NAME: "Main controller",
            CONF_PASSWORD: "hunter2",
            CONF_PORT: 1234,
            CONF_USERNAME: "username",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Main controller"
    assert result["data"] == {"password": "hunter2", "username": "username"}
    assert result["options"] == {
        "controller_id": "main_controller",
        "dimmers": [],
        "host": "192.168.0.1",
        "keypads": [],
        "port": 1234,
    }
    mock_homeworks.assert_called_once_with(
        "192.168.0.1", 1234, ANY, "username", "hunter2"
    )
    mock_controller.close.assert_called_once_with()
    mock_controller.join.assert_not_called()


async def test_user_flow_credentials_user_only(
    menuai: menuai, mock_homeworks: MagicMock, mock_setup_entry
) -> None:
    """Test the user configuration flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    mock_controller = MagicMock()
    mock_homeworks.return_value = mock_controller
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: "192.168.0.1",
            CONF_NAME: "Main controller",
            CONF_PORT: 1234,
            CONF_USERNAME: "username",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Main controller"
    assert result["data"] == {"password": None, "username": "username"}
    assert result["options"] == {
        "controller_id": "main_controller",
        "dimmers": [],
        "host": "192.168.0.1",
        "keypads": [],
        "port": 1234,
    }
    mock_homeworks.assert_called_once_with("192.168.0.1", 1234, ANY, "username", None)
    mock_controller.close.assert_called_once_with()
    mock_controller.join.assert_not_called()


async def test_user_flow_credentials_password_only(
    menuai: menuai, mock_homeworks: MagicMock, mock_setup_entry
) -> None:
    """Test the user configuration flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    mock_controller = MagicMock()
    mock_homeworks.return_value = mock_controller
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: "192.168.0.1",
            CONF_NAME: "Main controller",
            CONF_PASSWORD: "hunter2",
            CONF_PORT: 1234,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "need_username_with_password"}


async def test_user_flow_already_exists(
    menuai: menuai, mock_empty_config_entry: MockConfigEntry, mock_setup_entry
) -> None:
    """Test the user configuration flow."""
    mock_empty_config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: "192.168.0.1",
            CONF_NAME: "Main controller",
            CONF_PORT: 1234,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "duplicated_host_port"}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: "192.168.0.2",
            CONF_NAME: "Main controller",
            CONF_PORT: 1234,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "duplicated_controller_id"}


@pytest.mark.parametrize(
    ("side_effect", "error"),
    [
        (hw_exceptions.HomeworksConnectionFailed, "connection_error"),
        (hw_exceptions.HomeworksInvalidCredentialsProvided, "invalid_credentials"),
        (hw_exceptions.HomeworksNoCredentialsProvided, "credentials_needed"),
        (Exception, "unknown_error"),
    ],
)
async def test_user_flow_cannot_connect(
    menuai: menuai,
    mock_homeworks: MagicMock,
    mock_setup_entry,
    side_effect: type[Exception],
    error: str,
) -> None:
    """Test handling invalid connection."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    mock_homeworks.side_effect = side_effect
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: "192.168.0.1",
            CONF_NAME: "Main controller",
            CONF_PORT: 1234,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}
    assert result["step_id"] == "user"


async def test_reconfigure_flow(
    menuai: menuai, mock_config_entry: MockConfigEntry, mock_homeworks: MagicMock
) -> None:
    """Test reconfigure flow."""
    mock_config_entry.add_to_menuai(menuai)

    result = await mock_config_entry.start_reconfigure_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: "192.168.0.2",
            CONF_PORT: 1234,
        },
    )
    await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.options == {
        "controller_id": "main_controller",
        "dimmers": [
            {"addr": "[02:08:01:01]", "name": "Foyer Sconces", "rate": 1.0},
        ],
        "host": "192.168.0.2",
        "keypads": [
            {
                "addr": "[02:08:02:01]",
                "buttons": [
                    {
                        "led": True,
                        "name": "Morning",
                        "number": 1,
                        "release_delay": None,
                    },
                    {"led": True, "name": "Relax", "number": 2, "release_delay": None},
                    {"led": False, "name": "Dim up", "number": 3, "release_delay": 0.2},
                ],
                "name": "Foyer Keypad",
            },
        ],
        "port": 1234,
    }


async def test_reconfigure_flow_flow_duplicate(
    menuai: menuai, mock_homeworks: MagicMock
) -> None:
    """Test reconfigure flow."""
    entry1 = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            "controller_id": "controller_1",
            "host": "192.168.0.1",
            "port": 1234,
        },
    )
    entry1.add_to_menuai(menuai)
    entry2 = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            "controller_id": "controller_2",
            "host": "192.168.0.2",
            "port": 1234,
        },
    )
    entry2.add_to_menuai(menuai)

    result = await entry1.start_reconfigure_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: "192.168.0.2",
            CONF_PORT: 1234,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    assert result["errors"] == {"base": "duplicated_host_port"}


async def test_reconfigure_flow_flow_no_change(
    menuai: menuai, mock_config_entry: MockConfigEntry, mock_homeworks: MagicMock
) -> None:
    """Test reconfigure flow."""
    mock_config_entry.add_to_menuai(menuai)

    result = await mock_config_entry.start_reconfigure_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: "192.168.0.1",
            CONF_PORT: 1234,
        },
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.options == {
        "controller_id": "main_controller",
        "dimmers": [
            {"addr": "[02:08:01:01]", "name": "Foyer Sconces", "rate": 1.0},
        ],
        "host": "192.168.0.1",
        "keypads": [
            {
                "addr": "[02:08:02:01]",
                "buttons": [
                    {
                        "led": True,
                        "name": "Morning",
                        "number": 1,
                        "release_delay": None,
                    },
                    {"led": True, "name": "Relax", "number": 2, "release_delay": None},
                    {"led": False, "name": "Dim up", "number": 3, "release_delay": 0.2},
                ],
                "name": "Foyer Keypad",
            }
        ],
        "port": 1234,
    }


async def test_reconfigure_flow_credentials_password_only(
    menuai: menuai, mock_config_entry: MockConfigEntry, mock_homeworks: MagicMock
) -> None:
    """Test reconfigure flow."""
    mock_config_entry.add_to_menuai(menuai)

    result = await mock_config_entry.start_reconfigure_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: "192.168.0.2",
            CONF_PASSWORD: "hunter2",
            CONF_PORT: 1234,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    assert result["errors"] == {"base": "need_username_with_password"}


async def test_options_add_light_flow(
    menuai: menuai,
    mock_empty_config_entry: MockConfigEntry,
    mock_homeworks: MagicMock,
) -> None:
    """Test options flow to add a light."""
    mock_empty_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_empty_config_entry.entry_id)
    await menuai.async_block_till_done()
    assert menuai.states.async_entity_ids("light") == unordered([])

    result = await menuai.config_entries.options.async_init(
        mock_empty_config_entry.entry_id
    )
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        {"next_step_id": "add_light"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "add_light"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_ADDR: "[02:08:01:02]",
            CONF_NAME: "Foyer Downlights",
            CONF_RATE: 2.0,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "controller_id": "main_controller",
        "dimmers": [
            {"addr": "[02:08:01:02]", "name": "Foyer Downlights", "rate": 2.0},
        ],
        "host": "192.168.0.1",
        "keypads": [],
        "port": 1234,
    }

    await menuai.async_block_till_done()

    # Check the entry was updated with the new entity
    assert menuai.states.async_entity_ids("light") == unordered(
        ["light.foyer_downlights"]
    )


async def test_options_add_remove_light_flow(
    menuai: menuai, mock_config_entry: MockConfigEntry, mock_homeworks: MagicMock
) -> None:
    """Test options flow to add and remove a light."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()
    assert menuai.states.async_entity_ids("light") == unordered(["light.foyer_sconces"])

    result = await menuai.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        {"next_step_id": "add_light"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "add_light"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_ADDR: "[02:08:01:02]",
            CONF_NAME: "Foyer Downlights",
            CONF_RATE: 2.0,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "controller_id": "main_controller",
        "dimmers": [
            {"addr": "[02:08:01:01]", "name": "Foyer Sconces", "rate": 1.0},
            {"addr": "[02:08:01:02]", "name": "Foyer Downlights", "rate": 2.0},
        ],
        "host": "192.168.0.1",
        "keypads": [
            {
                "addr": "[02:08:02:01]",
                "buttons": [
                    {
                        "led": True,
                        "name": "Morning",
                        "number": 1,
                        "release_delay": None,
                    },
                    {"led": True, "name": "Relax", "number": 2, "release_delay": None},
                    {"led": False, "name": "Dim up", "number": 3, "release_delay": 0.2},
                ],
                "name": "Foyer Keypad",
            }
        ],
        "port": 1234,
    }

    await menuai.async_block_till_done()

    # Check the entry was updated with the new entity
    assert menuai.states.async_entity_ids("light") == unordered(
        ["light.foyer_sconces", "light.foyer_downlights"]
    )

    # Now remove the original light
    result = await menuai.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        {"next_step_id": "remove_light"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "remove_light"
    assert result["data_schema"].schema["index"].options == {
        "0": "Foyer Sconces ([02:08:01:01])",
        "1": "Foyer Downlights ([02:08:01:02])",
    }

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_INDEX: ["0"]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "controller_id": "main_controller",
        "dimmers": [
            {"addr": "[02:08:01:02]", "name": "Foyer Downlights", "rate": 2.0},
        ],
        "host": "192.168.0.1",
        "keypads": [
            {
                "addr": "[02:08:02:01]",
                "buttons": [
                    {
                        "led": True,
                        "name": "Morning",
                        "number": 1,
                        "release_delay": None,
                    },
                    {"led": True, "name": "Relax", "number": 2, "release_delay": None},
                    {"led": False, "name": "Dim up", "number": 3, "release_delay": 0.2},
                ],
                "name": "Foyer Keypad",
            }
        ],
        "port": 1234,
    }

    await menuai.async_block_till_done()

    # Check the original entity was removed, with only the new entity left
    assert menuai.states.async_entity_ids("light") == unordered(
        ["light.foyer_downlights"]
    )


@pytest.mark.parametrize(
    "keypad_address",
    [
        "[02:08:03]",
        "[02:08:03:01]",
        "[02:08:03:01:00]",
    ],
)
async def test_options_add_remove_keypad_flow(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_homeworks: MagicMock,
    keypad_address: str,
) -> None:
    """Test options flow to add and remove a keypad."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    result = await menuai.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        {"next_step_id": "add_keypad"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "add_keypad"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_ADDR: keypad_address,
            CONF_NAME: "Hall Keypad",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "controller_id": "main_controller",
        "dimmers": [
            {"addr": "[02:08:01:01]", "name": "Foyer Sconces", "rate": 1.0},
        ],
        "host": "192.168.0.1",
        "keypads": [
            {
                "addr": "[02:08:02:01]",
                "buttons": [
                    {
                        "led": True,
                        "name": "Morning",
                        "number": 1,
                        "release_delay": None,
                    },
                    {"led": True, "name": "Relax", "number": 2, "release_delay": None},
                    {"led": False, "name": "Dim up", "number": 3, "release_delay": 0.2},
                ],
                "name": "Foyer Keypad",
            },
            {"addr": keypad_address, "buttons": [], "name": "Hall Keypad"},
        ],
        "port": 1234,
    }

    await menuai.async_block_till_done()

    # Now remove the original keypad
    result = await menuai.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        {"next_step_id": "remove_keypad"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "remove_keypad"
    assert result["data_schema"].schema["index"].options == {
        "0": "Foyer Keypad ([02:08:02:01])",
        "1": f"Hall Keypad ({keypad_address})",
    }

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_INDEX: ["0"]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "controller_id": "main_controller",
        "dimmers": [
            {"addr": "[02:08:01:01]", "name": "Foyer Sconces", "rate": 1.0},
        ],
        "host": "192.168.0.1",
        "keypads": [{"addr": keypad_address, "buttons": [], "name": "Hall Keypad"}],
        "port": 1234,
    }
    await menuai.async_block_till_done()


async def test_options_add_keypad_with_error(
    menuai: menuai, mock_config_entry: MockConfigEntry, mock_homeworks: MagicMock
) -> None:
    """Test options flow to add and remove a keypad."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    result = await menuai.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        {"next_step_id": "add_keypad"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "add_keypad"

    # Try an invalid address
    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_ADDR: "[02:08:03:01",
            CONF_NAME: "Hall Keypad",
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "add_keypad"
    assert result["errors"] == {"base": "invalid_addr"}

    # Try an address claimed by another keypad
    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_ADDR: "[02:08:02:01]",
            CONF_NAME: "Hall Keypad",
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "add_keypad"
    assert result["errors"] == {"base": "duplicated_addr"}

    # Try an address claimed by a light
    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_ADDR: "[02:08:01:01]",
            CONF_NAME: "Hall Keypad",
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "add_keypad"
    assert result["errors"] == {"base": "duplicated_addr"}


async def test_options_edit_light_no_lights_flow(
    menuai: menuai, mock_config_entry: MockConfigEntry, mock_homeworks: MagicMock
) -> None:
    """Test options flow to edit a light."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()
    assert menuai.states.async_entity_ids("light") == unordered(["light.foyer_sconces"])

    result = await menuai.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "select_edit_light"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select_edit_light"
    assert result["data_schema"].schema["index"].container == {
        "0": "Foyer Sconces ([02:08:01:01])"
    }

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        {"index": "0"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "edit_light"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_RATE: 3.0}
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "controller_id": "main_controller",
        "dimmers": [{"addr": "[02:08:01:01]", "name": "Foyer Sconces", "rate": 3.0}],
        "host": "192.168.0.1",
        "keypads": [
            {
                "addr": "[02:08:02:01]",
                "buttons": [
                    {
                        "led": True,
                        "name": "Morning",
                        "number": 1,
                        "release_delay": None,
                    },
                    {"led": True, "name": "Relax", "number": 2, "release_delay": None},
                    {"led": False, "name": "Dim up", "number": 3, "release_delay": 0.2},
                ],
                "name": "Foyer Keypad",
            }
        ],
        "port": 1234,
    }

    await menuai.async_block_till_done()

    # Check the entity was updated
    assert len(menuai.states.async_entity_ids("light")) == 1


async def test_options_edit_light_flow_empty(
    menuai: menuai,
    mock_empty_config_entry: MockConfigEntry,
    mock_homeworks: MagicMock,
) -> None:
    """Test options flow to edit a light."""
    mock_empty_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_empty_config_entry.entry_id)
    await menuai.async_block_till_done()
    assert menuai.states.async_entity_ids("light") == unordered([])

    result = await menuai.config_entries.options.async_init(
        mock_empty_config_entry.entry_id
    )
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "select_edit_light"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select_edit_light"
    assert result["data_schema"].schema["index"].container == {}


async def test_options_add_button_flow(
    menuai: menuai, mock_config_entry: MockConfigEntry, mock_homeworks: MagicMock
) -> None:
    """Test options flow to add a button."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()
    assert len(menuai.states.async_entity_ids(BINARY_SENSOR_DOMAIN)) == 2
    assert len(menuai.states.async_entity_ids(BUTTON_DOMAIN)) == 3

    result = await menuai.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "select_edit_keypad"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select_edit_keypad"
    assert result["data_schema"].schema["index"].container == {
        "0": "Foyer Keypad ([02:08:02:01])"
    }

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        {"index": "0"},
    )
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "edit_keypad"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_button"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "add_button"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "Dim down",
            CONF_NUMBER: 4,
            CONF_RELEASE_DELAY: 0.2,
            CONF_LED: True,
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "controller_id": "main_controller",
        "dimmers": [{"addr": "[02:08:01:01]", "name": "Foyer Sconces", "rate": 1.0}],
        "host": "192.168.0.1",
        "keypads": [
            {
                "addr": "[02:08:02:01]",
                "buttons": [
                    {
                        "led": True,
                        "name": "Morning",
                        "number": 1,
                        "release_delay": None,
                    },
                    {"led": True, "name": "Relax", "number": 2, "release_delay": None},
                    {"led": False, "name": "Dim up", "number": 3, "release_delay": 0.2},
                    {
                        "led": True,
                        "name": "Dim down",
                        "number": 4,
                        "release_delay": 0.2,
                    },
                ],
                "name": "Foyer Keypad",
            }
        ],
        "port": 1234,
    }

    await menuai.async_block_till_done()

    # Check the new entities were added
    assert len(menuai.states.async_entity_ids(BINARY_SENSOR_DOMAIN)) == 3
    assert len(menuai.states.async_entity_ids(BUTTON_DOMAIN)) == 4


async def test_options_add_button_flow_duplicate(
    menuai: menuai, mock_config_entry: MockConfigEntry, mock_homeworks: MagicMock
) -> None:
    """Test options flow to add a button."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()
    assert len(menuai.states.async_entity_ids(BINARY_SENSOR_DOMAIN)) == 2
    assert len(menuai.states.async_entity_ids(BUTTON_DOMAIN)) == 3

    result = await menuai.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "select_edit_keypad"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select_edit_keypad"
    assert result["data_schema"].schema["index"].container == {
        "0": "Foyer Keypad ([02:08:02:01])"
    }

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        {"index": "0"},
    )
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "edit_keypad"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_button"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "add_button"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "Dim down",
            CONF_NUMBER: 1,
            CONF_RELEASE_DELAY: 0.2,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "duplicated_number"}


async def test_options_edit_button_flow(
    menuai: menuai, mock_config_entry: MockConfigEntry, mock_homeworks: MagicMock
) -> None:
    """Test options flow to add a button."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()
    assert len(menuai.states.async_entity_ids(BINARY_SENSOR_DOMAIN)) == 2
    assert len(menuai.states.async_entity_ids(BUTTON_DOMAIN)) == 3

    result = await menuai.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "select_edit_keypad"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select_edit_keypad"
    assert result["data_schema"].schema["index"].container == {
        "0": "Foyer Keypad ([02:08:02:01])"
    }

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        {"index": "0"},
    )
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "edit_keypad"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "select_edit_button"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select_edit_button"
    assert result["data_schema"].schema["index"].container == {
        "0": "Morning (1)",
        "1": "Relax (2)",
        "2": "Dim up (3)",
    }

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        {"index": "0"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "edit_button"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_RELEASE_DELAY: 0,
            CONF_LED: False,
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "controller_id": "main_controller",
        "dimmers": [{"addr": "[02:08:01:01]", "name": "Foyer Sconces", "rate": 1.0}],
        "host": "192.168.0.1",
        "keypads": [
            {
                "addr": "[02:08:02:01]",
                "buttons": [
                    {
                        "led": False,
                        "name": "Morning",
                        "number": 1,
                        "release_delay": 0.0,
                    },
                    {"led": True, "name": "Relax", "number": 2, "release_delay": None},
                    {"led": False, "name": "Dim up", "number": 3, "release_delay": 0.2},
                ],
                "name": "Foyer Keypad",
            }
        ],
        "port": 1234,
    }

    await menuai.async_block_till_done()

    # Check the new entities were added
    assert len(menuai.states.async_entity_ids(BINARY_SENSOR_DOMAIN)) == 2
    assert len(menuai.states.async_entity_ids(BUTTON_DOMAIN)) == 3


async def test_options_remove_button_flow(
    menuai: menuai, mock_config_entry: MockConfigEntry, mock_homeworks: MagicMock
) -> None:
    """Test options flow to remove a button."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()
    assert len(menuai.states.async_entity_ids(BUTTON_DOMAIN)) == 3

    result = await menuai.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "select_edit_keypad"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select_edit_keypad"
    assert result["data_schema"].schema["index"].container == {
        "0": "Foyer Keypad ([02:08:02:01])"
    }

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        {"index": "0"},
    )
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "edit_keypad"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "remove_button"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "remove_button"
    assert result["data_schema"].schema["index"].options == {
        "0": "Morning (1)",
        "1": "Relax (2)",
        "2": "Dim up (3)",
    }

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_INDEX: ["0"]}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "controller_id": "main_controller",
        "dimmers": [{"addr": "[02:08:01:01]", "name": "Foyer Sconces", "rate": 1.0}],
        "host": "192.168.0.1",
        "keypads": [
            {
                "addr": "[02:08:02:01]",
                "buttons": [
                    {"led": True, "name": "Relax", "number": 2, "release_delay": None},
                    {"led": False, "name": "Dim up", "number": 3, "release_delay": 0.2},
                ],
                "name": "Foyer Keypad",
            }
        ],
        "port": 1234,
    }

    await menuai.async_block_till_done()

    # Check the entities were removed
    assert len(menuai.states.async_entity_ids(BINARY_SENSOR_DOMAIN)) == 1
    assert len(menuai.states.async_entity_ids(BUTTON_DOMAIN)) == 2
