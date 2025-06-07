"""Tests for the Remember The Milk integration."""

import json
from unittest.mock import mock_open, patch

import pytest

from menuai.components import remember_the_milk as rtm
from menuai.core import menuai

from .const import JSON_STRING, PROFILE, TOKEN


def test_set_get_delete_token(menuai: menuai) -> None:
    """Test set, get and delete token."""
    open_mock = mock_open()
    with patch(
        "menuai.components.remember_the_milk.storage.Path.open", open_mock
    ):
        config = rtm.RememberTheMilkConfiguration(menuai)
        assert open_mock.return_value.write.call_count == 0
        assert config.get_token(PROFILE) is None
        assert open_mock.return_value.write.call_count == 0
        config.set_token(PROFILE, TOKEN)
        assert open_mock.return_value.write.call_count == 1
        assert open_mock.return_value.write.call_args[0][0] == json.dumps(
            {
                "myprofile": {
                    "id_map": {},
                    "token": "mytoken",
                }
            }
        )
        assert config.get_token(PROFILE) == TOKEN
        assert open_mock.return_value.write.call_count == 1
        config.delete_token(PROFILE)
        assert open_mock.return_value.write.call_count == 2
        assert open_mock.return_value.write.call_args[0][0] == json.dumps({})
        assert config.get_token(PROFILE) is None
        assert open_mock.return_value.write.call_count == 2


def test_config_load(menuai: menuai) -> None:
    """Test loading from the file."""
    with (
        patch(
            "menuai.components.remember_the_milk.storage.Path.open",
            mock_open(read_data=JSON_STRING),
        ),
    ):
        config = rtm.RememberTheMilkConfiguration(menuai)

    rtm_id = config.get_rtm_id(PROFILE, "123")
    assert rtm_id is not None
    assert rtm_id == ("1", "2", "3")


@pytest.mark.parametrize(
    "side_effect", [FileNotFoundError("Missing file"), OSError("IO error")]
)
def test_config_load_file_error(menuai: menuai, side_effect: Exception) -> None:
    """Test loading with file error."""
    config = rtm.RememberTheMilkConfiguration(menuai)
    with (
        patch(
            "menuai.components.remember_the_milk.storage.Path.open",
            side_effect=side_effect,
        ),
    ):
        config = rtm.RememberTheMilkConfiguration(menuai)

    # The config should be empty and we should not have any errors
    # when trying to access it.
    rtm_id = config.get_rtm_id(PROFILE, "123")
    assert rtm_id is None


def test_config_load_invalid_data(menuai: menuai) -> None:
    """Test loading invalid data."""
    config = rtm.RememberTheMilkConfiguration(menuai)
    with (
        patch(
            "menuai.components.remember_the_milk.storage.Path.open",
            mock_open(read_data="random characters"),
        ),
    ):
        config = rtm.RememberTheMilkConfiguration(menuai)

    # The config should be empty and we should not have any errors
    # when trying to access it.
    rtm_id = config.get_rtm_id(PROFILE, "123")
    assert rtm_id is None


def test_config_set_delete_id(menuai: menuai) -> None:
    """Test setting and deleting an id from the config."""
    menuai_id = "123"
    list_id = "1"
    timeseries_id = "2"
    rtm_id = "3"
    open_mock = mock_open()
    config = rtm.RememberTheMilkConfiguration(menuai)
    with patch(
        "menuai.components.remember_the_milk.storage.Path.open", open_mock
    ):
        config = rtm.RememberTheMilkConfiguration(menuai)
        assert open_mock.return_value.write.call_count == 0
        assert config.get_rtm_id(PROFILE, menuai_id) is None
        assert open_mock.return_value.write.call_count == 0
        config.set_rtm_id(PROFILE, menuai_id, list_id, timeseries_id, rtm_id)
        assert (list_id, timeseries_id, rtm_id) == config.get_rtm_id(PROFILE, menuai_id)
        assert open_mock.return_value.write.call_count == 1
        assert open_mock.return_value.write.call_args[0][0] == json.dumps(
            {
                "myprofile": {
                    "id_map": {
                        "123": {"list_id": "1", "timeseries_id": "2", "task_id": "3"}
                    }
                }
            }
        )
        config.delete_rtm_id(PROFILE, menuai_id)
        assert config.get_rtm_id(PROFILE, menuai_id) is None
        assert open_mock.return_value.write.call_count == 2
        assert open_mock.return_value.write.call_args[0][0] == json.dumps(
            {
                "myprofile": {
                    "id_map": {},
                }
            }
        )
