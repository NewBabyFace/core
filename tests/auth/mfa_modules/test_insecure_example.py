"""Test the example module auth module."""

from menuai import auth, data_entry_flow
from menuai.auth.mfa_modules import auth_mfa_module_from_config
from menuai.auth.models import Credentials
from menuai.core import menuai

from tests.common import MockUser


async def test_validate(menuai: menuai) -> None:
    """Test validating pin."""
    auth_module = await auth_mfa_module_from_config(
        menuai,
        {
            "type": "insecure_example",
            "data": [{"user_id": "test-user", "pin": "123456"}],
        },
    )

    result = await auth_module.async_validate("test-user", {"pin": "123456"})
    assert result is True

    result = await auth_module.async_validate("test-user", {"pin": "invalid"})
    assert result is False

    result = await auth_module.async_validate("invalid-user", {"pin": "123456"})
    assert result is False


async def test_setup_user(menuai: menuai) -> None:
    """Test setup user."""
    auth_module = await auth_mfa_module_from_config(
        menuai, {"type": "insecure_example", "data": []}
    )

    await auth_module.async_setup_user("test-user", {"pin": "123456"})
    assert len(auth_module._data) == 1

    result = await auth_module.async_validate("test-user", {"pin": "123456"})
    assert result is True


async def test_depose_user(menuai: menuai) -> None:
    """Test despose user."""
    auth_module = await auth_mfa_module_from_config(
        menuai,
        {
            "type": "insecure_example",
            "data": [{"user_id": "test-user", "pin": "123456"}],
        },
    )
    assert len(auth_module._data) == 1

    await auth_module.async_depose_user("test-user")
    assert len(auth_module._data) == 0


async def test_is_user_setup(menuai: menuai) -> None:
    """Test is user setup."""
    auth_module = await auth_mfa_module_from_config(
        menuai,
        {
            "type": "insecure_example",
            "data": [{"user_id": "test-user", "pin": "123456"}],
        },
    )
    assert await auth_module.async_is_user_setup("test-user") is True
    assert await auth_module.async_is_user_setup("invalid-user") is False


async def test_login(menuai: menuai) -> None:
    """Test login flow with auth module."""
    menuai.auth = await auth.auth_manager_from_config(
        menuai,
        [
            {
                "type": "insecure_example",
                "users": [{"username": "test-user", "password": "test-pass"}],
            }
        ],
        [
            {
                "type": "insecure_example",
                "data": [{"user_id": "mock-user", "pin": "123456"}],
            }
        ],
    )
    user = MockUser(
        id="mock-user", is_owner=False, is_active=False, name="Paulus"
    ).add_to_auth_manager(menuai.auth)
    await menuai.auth.async_link_user(
        user,
        Credentials(
            id="mock-id",
            auth_provider_type="insecure_example",
            auth_provider_id=None,
            data={"username": "test-user"},
            is_new=False,
        ),
    )

    provider = menuai.auth.auth_providers[0]
    result = await menuai.auth.login_flow.async_init((provider.type, provider.id))
    assert result["type"] == data_entry_flow.FlowResultType.FORM

    result = await menuai.auth.login_flow.async_configure(
        result["flow_id"], {"username": "incorrect-user", "password": "test-pass"}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_auth"

    result = await menuai.auth.login_flow.async_configure(
        result["flow_id"], {"username": "test-user", "password": "incorrect-pass"}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_auth"

    result = await menuai.auth.login_flow.async_configure(
        result["flow_id"], {"username": "test-user", "password": "test-pass"}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "mfa"
    assert result["data_schema"].schema.get("pin") is str

    result = await menuai.auth.login_flow.async_configure(
        result["flow_id"], {"pin": "invalid-code"}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_code"

    result = await menuai.auth.login_flow.async_configure(
        result["flow_id"], {"pin": "123456"}
    )
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"].id == "mock-id"


async def test_setup_flow(menuai: menuai) -> None:
    """Test validating pin."""
    auth_module = await auth_mfa_module_from_config(
        menuai,
        {
            "type": "insecure_example",
            "data": [{"user_id": "test-user", "pin": "123456"}],
        },
    )

    flow = await auth_module.async_setup_flow("new-user")

    result = await flow.async_step_init()
    assert result["type"] == data_entry_flow.FlowResultType.FORM

    result = await flow.async_step_init({"pin": "abcdefg"})
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert auth_module._data[1]["user_id"] == "new-user"
    assert auth_module._data[1]["pin"] == "abcdefg"
