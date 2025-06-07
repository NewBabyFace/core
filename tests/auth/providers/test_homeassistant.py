"""Test the MenuAI local auth provider."""

import asyncio
from typing import Any
from unittest.mock import Mock, patch

import pytest
import voluptuous as vol

from menuai import data_entry_flow
from menuai.auth import auth_manager_from_config, auth_store
from menuai.auth.providers import (
    auth_provider_from_config,
    menuai as menuai_auth,
)
from menuai.core import menuai
from menuai.helpers import issue_registry as ir
from menuai.setup import async_setup_component


@pytest.fixture
async def data(menuai: menuai) -> menuai_auth.Data:
    """Create a loaded data class."""
    data = menuai_auth.Data(menuai)
    await data.async_load()
    return data


@pytest.fixture
async def legacy_data(menuai: menuai) -> menuai_auth.Data:
    """Create a loaded legacy data class."""
    data = menuai_auth.Data(menuai)
    await data.async_load()
    data.is_legacy = True
    return data


@pytest.fixture
async def load_auth_component(menuai: menuai) -> None:
    """Load the auth component for translations."""
    await async_setup_component(menuai, "auth", {})


async def test_validating_password_invalid_user(data: menuai_auth.Data) -> None:
    """Test validating an invalid user."""
    with pytest.raises(menuai_auth.InvalidAuth):
        data.validate_login("non-existing", "pw")


async def test_not_allow_set_id() -> None:
    """Test we are not allowed to set an ID in config."""
    menuai = Mock()
    menuai.data = {}
    with pytest.raises(vol.Invalid):
        await auth_provider_from_config(
            menuai, None, {"type": "menuai", "id": "invalid"}
        )


async def test_new_users_populate_values(
    menuai: menuai, data: menuai_auth.Data
) -> None:
    """Test that we populate data for new users."""
    data.add_auth("hello", "test-pass")
    await data.async_save()

    manager = await auth_manager_from_config(menuai, [{"type": "menuai"}], [])
    provider = manager.auth_providers[0]
    credentials = await provider.async_get_or_create_credentials({"username": "hello"})
    user = await manager.async_get_or_create_user(credentials)
    assert user.name == "hello"
    assert user.is_active


async def test_changing_password_raises_invalid_user(data: menuai_auth.Data) -> None:
    """Test that changing password raises invalid user."""
    with pytest.raises(menuai_auth.InvalidUser):
        data.change_password("non-existing", "pw")


# Modern mode


async def test_adding_user(data: menuai_auth.Data) -> None:
    """Test adding a user."""
    data.add_auth("test-user", "test-pass")
    data.validate_login(" test-user ", "test-pass")


@pytest.mark.parametrize("username", ["test-user ", "TEST-USER"])
@pytest.mark.usefixtures("load_auth_component")
def test_adding_user_not_normalized(data: menuai_auth.Data, username: str) -> None:
    """Test adding a user."""
    with pytest.raises(
        menuai_auth.InvalidUsername, match=f'Username "{username}" is not normalized'
    ):
        data.add_auth(username, "test-pass")


@pytest.mark.usefixtures("load_auth_component")
def test_adding_user_duplicate_username(data: menuai_auth.Data) -> None:
    """Test adding a user with duplicate username."""
    data.add_auth("test-user", "test-pass")

    with pytest.raises(
        menuai_auth.InvalidUsername, match='Username "test-user" already exists'
    ):
        data.add_auth("test-user", "other-pass")


async def test_validating_password_invalid_password(data: menuai_auth.Data) -> None:
    """Test validating an invalid password."""
    data.add_auth("test-user", "test-pass")

    with pytest.raises(menuai_auth.InvalidAuth):
        data.validate_login(" test-user ", "invalid-pass")

    with pytest.raises(menuai_auth.InvalidAuth):
        data.validate_login("test-user", "test-pass ")

    with pytest.raises(menuai_auth.InvalidAuth):
        data.validate_login("test-user", "Test-pass")


async def test_changing_password(data: menuai_auth.Data) -> None:
    """Test adding a user."""
    data.add_auth("test-user", "test-pass")
    data.change_password("TEST-USER ", "new-pass")

    with pytest.raises(menuai_auth.InvalidAuth):
        data.validate_login("test-user", "test-pass")

    data.validate_login("test-UsEr", "new-pass")


async def test_login_flow_validates(data: menuai_auth.Data, menuai: menuai) -> None:
    """Test login flow."""
    data.add_auth("test-user", "test-pass")
    await data.async_save()

    provider = menuai_auth.menuaiAuthProvider(
        menuai, auth_store.AuthStore(menuai), {"type": "menuai"}
    )
    flow = await provider.async_login_flow({})
    result = await flow.async_step_init()
    assert result["type"] == data_entry_flow.FlowResultType.FORM

    result = await flow.async_step_init(
        {"username": "incorrect-user", "password": "test-pass"}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_auth"

    result = await flow.async_step_init(
        {"username": "TEST-user ", "password": "incorrect-pass"}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_auth"

    result = await flow.async_step_init(
        {"username": "test-USER", "password": "test-pass"}
    )
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"]["username"] == "test-USER"


async def test_saving_loading(data: menuai_auth.Data, menuai: menuai) -> None:
    """Test saving and loading JSON."""
    data.add_auth("test-user", "test-pass")
    data.add_auth("second-user", "second-pass")
    await data.async_save()

    data = menuai_auth.Data(menuai)
    await data.async_load()
    data.validate_login("test-user ", "test-pass")
    data.validate_login("second-user ", "second-pass")


async def test_get_or_create_credentials(
    menuai: menuai, data: menuai_auth.Data
) -> None:
    """Test that we can get or create credentials."""
    manager = await auth_manager_from_config(menuai, [{"type": "menuai"}], [])
    provider = manager.auth_providers[0]
    provider.data = data
    credentials1 = await provider.async_get_or_create_credentials({"username": "hello"})
    with patch.object(provider, "async_credentials", return_value=[credentials1]):
        credentials2 = await provider.async_get_or_create_credentials(
            {"username": "hello "}
        )
    assert credentials1 is credentials2


# Legacy mode


async def test_legacy_adding_user(legacy_data: menuai_auth.Data) -> None:
    """Test in legacy mode adding a user."""
    legacy_data.add_auth("test-user", "test-pass")
    legacy_data.validate_login("test-user", "test-pass")


async def test_legacy_validating_password_invalid_password(
    legacy_data: menuai_auth.Data,
) -> None:
    """Test in legacy mode validating an invalid password."""
    legacy_data.add_auth("test-user", "test-pass")

    with pytest.raises(menuai_auth.InvalidAuth):
        legacy_data.validate_login("test-user", "invalid-pass")


async def test_legacy_changing_password(legacy_data: menuai_auth.Data) -> None:
    """Test in legacy mode adding a user."""
    user = "test-user"
    legacy_data.add_auth(user, "test-pass")
    legacy_data.change_password(user, "new-pass")

    with pytest.raises(menuai_auth.InvalidAuth):
        legacy_data.validate_login(user, "test-pass")

    legacy_data.validate_login(user, "new-pass")


async def test_legacy_changing_password_raises_invalid_user(
    legacy_data: menuai_auth.Data,
) -> None:
    """Test in legacy mode that we initialize an empty config."""
    with pytest.raises(menuai_auth.InvalidUser):
        legacy_data.change_password("non-existing", "pw")


async def test_legacy_login_flow_validates(
    legacy_data: menuai_auth.Data, menuai: menuai
) -> None:
    """Test in legacy mode login flow."""
    legacy_data.add_auth("test-user", "test-pass")
    await legacy_data.async_save()

    provider = menuai_auth.menuaiAuthProvider(
        menuai, auth_store.AuthStore(menuai), {"type": "menuai"}
    )
    flow = await provider.async_login_flow({})
    result = await flow.async_step_init()
    assert result["type"] == data_entry_flow.FlowResultType.FORM

    result = await flow.async_step_init(
        {"username": "incorrect-user", "password": "test-pass"}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_auth"

    result = await flow.async_step_init(
        {"username": "test-user", "password": "incorrect-pass"}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_auth"

    result = await flow.async_step_init(
        {"username": "test-user", "password": "test-pass"}
    )
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"]["username"] == "test-user"


async def test_legacy_saving_loading(
    legacy_data: menuai_auth.Data, menuai: menuai
) -> None:
    """Test in legacy mode saving and loading JSON."""
    legacy_data.add_auth("test-user", "test-pass")
    legacy_data.add_auth("second-user", "second-pass")
    await legacy_data.async_save()

    legacy_data = menuai_auth.Data(menuai)
    await legacy_data.async_load()
    legacy_data.is_legacy = True
    legacy_data.validate_login("test-user", "test-pass")
    legacy_data.validate_login("second-user", "second-pass")

    with pytest.raises(menuai_auth.InvalidAuth):
        legacy_data.validate_login("test-user ", "test-pass")


async def test_legacy_get_or_create_credentials(
    menuai: menuai, legacy_data: menuai_auth.Data
) -> None:
    """Test in legacy mode that we can get or create credentials."""
    manager = await auth_manager_from_config(menuai, [{"type": "menuai"}], [])
    provider = manager.auth_providers[0]
    provider.data = legacy_data
    credentials1 = await provider.async_get_or_create_credentials({"username": "hello"})

    with patch.object(provider, "async_credentials", return_value=[credentials1]):
        credentials2 = await provider.async_get_or_create_credentials(
            {"username": "hello"}
        )
    assert credentials1 is credentials2

    with patch.object(provider, "async_credentials", return_value=[credentials1]):
        credentials3 = await provider.async_get_or_create_credentials(
            {"username": "hello "}
        )
    assert credentials1 is not credentials3


async def test_race_condition_in_data_loading(menuai: menuai) -> None:
    """Test race condition in the menuai_auth.Data loading.

    Ref issue: https://github.com/home-assistant/core/issues/21569
    """
    counter = 0

    async def mock_load(_):
        """Mock of menuai.helpers.storage.Store.async_load."""
        nonlocal counter
        counter += 1
        await asyncio.sleep(0)

    provider = menuai_auth.menuaiAuthProvider(
        menuai, auth_store.AuthStore(menuai), {"type": "menuai"}
    )
    with patch("menuai.helpers.storage.Store.async_load", new=mock_load):
        task1 = provider.async_validate_login("user", "pass")
        task2 = provider.async_validate_login("user", "pass")
        results = await asyncio.gather(task1, task2, return_exceptions=True)
        assert counter == 1
        assert isinstance(results[0], menuai_auth.InvalidAuth)
        # results[1] will be a TypeError if race condition occurred
        assert isinstance(results[1], menuai_auth.InvalidAuth)


def test_change_username(data: menuai_auth.Data) -> None:
    """Test changing username."""
    data.add_auth("test-user", "test-pass")
    users = data.users
    assert len(users) == 1
    assert users[0]["username"] == "test-user"

    data.change_username("test-user", "new-user")

    users = data.users
    assert len(users) == 1
    assert users[0]["username"] == "new-user"


@pytest.mark.parametrize("username", ["test-user ", "TEST-USER"])
def test_change_username_legacy(legacy_data: menuai_auth.Data, username: str) -> None:
    """Test changing username."""
    # Cannot use add_auth as it normalizes username
    legacy_data.users.append(
        {
            "username": username,
            "password": legacy_data.hash_password("test-pass", True).decode(),
        }
    )

    users = legacy_data.users
    assert len(users) == 1
    assert users[0]["username"] == username

    legacy_data.change_username(username, "test-user")

    users = legacy_data.users
    assert len(users) == 1
    assert users[0]["username"] == "test-user"


def test_change_username_invalid_user(data: menuai_auth.Data) -> None:
    """Test changing username raises on invalid user."""
    data.add_auth("test-user", "test-pass")
    users = data.users
    assert len(users) == 1
    assert users[0]["username"] == "test-user"

    with pytest.raises(menuai_auth.InvalidUser):
        data.change_username("non-existing", "new-user")

    users = data.users
    assert len(users) == 1
    assert users[0]["username"] == "test-user"


@pytest.mark.usefixtures("load_auth_component")
async def test_change_username_not_normalized(
    data: menuai_auth.Data, menuai: menuai
) -> None:
    """Test changing username raises on not normalized username."""
    data.add_auth("test-user", "test-pass")

    with pytest.raises(
        menuai_auth.InvalidUsername, match='Username "TEST-user " is not normalized'
    ):
        data.change_username("test-user", "TEST-user ")


@pytest.mark.parametrize(
    ("usernames_in_storage", "usernames_in_repair"),
    [
        (["Uppercase"], '- "Uppercase"'),
        ([" leading"], '- " leading"'),
        (["trailing "], '- "trailing "'),
        (["Test", "test", "Fritz "], '- "Fritz "\n- "Test"'),
    ],
)
async def test_create_repair_on_legacy_usernames(
    menuai: menuai,
    menuai_storage: dict[str, Any],
    issue_registry: ir.IssueRegistry,
    usernames_in_storage: list[str],
    usernames_in_repair: str,
) -> None:
    """Test that we create a repair issue for legacy usernames."""
    assert not issue_registry.issues.get(
        ("auth", "menuai_provider_not_normalized_usernames")
    ), "Repair issue already exists"

    menuai_storage[menuai_auth.STORAGE_KEY] = {
        "version": 1,
        "minor_version": 1,
        "key": "auth_provider.menuai",
        "data": {
            "users": [
                {
                    "username": username,
                    "password": "onlyherebecauseweneedapasswordstring",
                }
                for username in usernames_in_storage
            ]
        },
    }
    data = menuai_auth.Data(menuai)
    await data.async_load()
    issue = issue_registry.issues.get(
        ("auth", "menuai_provider_not_normalized_usernames")
    )
    assert issue, "Repair issue not created"
    assert issue.translation_placeholders == {"usernames": usernames_in_repair}


async def test_delete_repair_after_fixing_usernames(
    menuai: menuai,
    menuai_storage: dict[str, Any],
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test that the repair is deleted after fixing the usernames."""
    menuai_storage[menuai_auth.STORAGE_KEY] = {
        "version": 1,
        "minor_version": 1,
        "key": "auth_provider.menuai",
        "data": {
            "users": [
                {
                    "username": "Test",
                    "password": "onlyherebecauseweneedapasswordstring",
                },
                {
                    "username": "bla ",
                    "password": "onlyherebecauseweneedapasswordstring",
                },
            ]
        },
    }
    data = menuai_auth.Data(menuai)
    await data.async_load()
    issue = issue_registry.issues.get(
        ("auth", "menuai_provider_not_normalized_usernames")
    )
    assert issue, "Repair issue not created"
    assert issue.translation_placeholders == {"usernames": '- "Test"\n- "bla "'}

    data.change_username("Test", "test")
    issue = issue_registry.issues.get(
        ("auth", "menuai_provider_not_normalized_usernames")
    )
    assert issue
    assert issue.translation_placeholders == {"usernames": '- "bla "'}

    data.change_username("bla ", "bla")
    assert not issue_registry.issues.get(
        ("auth", "menuai_provider_not_normalized_usernames")
    ), "Repair issue should be deleted"
