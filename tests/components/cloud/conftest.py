"""Fixtures for cloud tests."""

from collections.abc import AsyncGenerator, Callable, Coroutine, Generator
from pathlib import Path
from typing import Any
from unittest.mock import DEFAULT, AsyncMock, MagicMock, PropertyMock, patch

from menuai_nabucasa import Cloud
from menuai_nabucasa.auth import CognitoAuth
from menuai_nabucasa.cloudhooks import Cloudhooks
from menuai_nabucasa.const import DEFAULT_SERVERS, DEFAULT_VALUES, STATE_CONNECTED
from menuai_nabucasa.files import Files
from menuai_nabucasa.google_report_state import GoogleReportState
from menuai_nabucasa.ice_servers import IceServers
from menuai_nabucasa.iot import CloudIoT
from menuai_nabucasa.remote import RemoteUI
from menuai_nabucasa.voice import Voice
import jwt
import pytest

from menuai.components.cloud.client import CloudClient
from menuai.components.cloud.const import DATA_CLOUD
from menuai.components.cloud.prefs import (
    PREF_ALEXA_DEFAULT_EXPOSE,
    PREF_GOOGLE_DEFAULT_EXPOSE,
    CloudPreferences,
)
from menuai.core import menuai
from menuai.setup import async_setup_component
from menuai.util.dt import utcnow

from . import mock_cloud, mock_cloud_prefs


@pytest.fixture(autouse=True)
async def load_menuai(menuai: menuai) -> None:
    """Load the menuai integration.

    This is needed for the cloud integration to work.
    """
    assert await async_setup_component(menuai, "menuai", {})


@pytest.fixture(name="cloud")
async def cloud_fixture() -> AsyncGenerator[MagicMock]:
    """Mock the cloud object.

    See the real menuai_nabucasa.Cloud class for how to configure the mock.
    """
    with patch(
        "menuai.components.cloud.Cloud", autospec=True
    ) as mock_cloud_class:
        mock_cloud = mock_cloud_class.return_value

        # Attributes set in the constructor without parameters.
        # We spec the mocks with the real classes
        # and set constructor attributes or mock properties as needed.
        mock_cloud.google_report_state = MagicMock(spec=GoogleReportState)
        mock_cloud.cloudhooks = MagicMock(spec=Cloudhooks)
        mock_cloud.remote = MagicMock(
            spec=RemoteUI,
            certificate=None,
            certificate_status=None,
            instance_domain=None,
            is_connected=False,
        )
        mock_cloud.auth = MagicMock(spec=CognitoAuth)
        mock_cloud.iot = MagicMock(
            spec=CloudIoT, last_disconnect_reason=None, state=STATE_CONNECTED
        )
        mock_cloud.voice = MagicMock(spec=Voice)
        mock_cloud.files = MagicMock(spec=Files)
        mock_cloud.started = None
        mock_cloud.ice_servers = MagicMock(
            spec=IceServers,
            async_register_ice_servers_listener=AsyncMock(
                return_value=lambda: "mock-unregister"
            ),
        )

        def set_up_mock_cloud(
            cloud_client: CloudClient, mode: str, **kwargs: Any
        ) -> DEFAULT:
            """Set up mock cloud with a mock constructor."""

            # Attributes set in the constructor with parameters.
            cloud_client.cloud = mock_cloud
            mock_cloud.client = cloud_client
            default_values = DEFAULT_VALUES[mode]
            servers = {
                f"{name}_server": server
                for name, server in DEFAULT_SERVERS[mode].items()
            }
            mock_cloud.configure_mock(**default_values, **servers)
            mock_cloud.configure_mock(**kwargs)
            mock_cloud.mode = mode

            # Properties that we mock as attributes from the constructor.
            mock_cloud.websession = cloud_client.websession

            return DEFAULT

        mock_cloud_class.side_effect = set_up_mock_cloud

        # Attributes that we mock with default values.

        mock_cloud.id_token = None
        mock_cloud.access_token = None
        mock_cloud.refresh_token = None

        # Properties that we keep as properties.

        def mock_is_logged_in() -> bool:
            """Mock is logged in."""
            return mock_cloud.id_token is not None

        is_logged_in = PropertyMock(side_effect=mock_is_logged_in)
        type(mock_cloud).is_logged_in = is_logged_in

        def mock_claims() -> dict[str, Any]:
            """Mock claims."""
            return Cloud._decode_claims(mock_cloud.id_token)

        claims = PropertyMock(side_effect=mock_claims)
        type(mock_cloud).claims = claims

        def mock_is_connected() -> bool:
            """Return True if we are connected."""
            return mock_cloud.iot.state == STATE_CONNECTED

        is_connected = PropertyMock(side_effect=mock_is_connected)
        type(mock_cloud).is_connected = is_connected
        type(mock_cloud.iot).connected = is_connected

        def mock_username() -> bool:
            """Return the subscription username."""
            return "abcdefghjkl"

        username = PropertyMock(side_effect=mock_username)
        type(mock_cloud).username = username

        # Properties that we mock as attributes.
        mock_cloud.expiration_date = utcnow()
        mock_cloud.subscription_expired = False

        # Methods that we mock with a custom side effect.

        async def mock_login(
            email: str,
            password: str,
            *,
            check_connection: bool = False,
        ) -> None:
            """Mock login.

            When called, it should call the on_start callback.
            """
            mock_cloud.id_token = jwt.encode(
                {
                    "email": "hello@home-assistant.io",
                    "custom:sub-exp": "2018-01-03",
                    "cognito:username": "abcdefghjkl",
                },
                "test",
            )
            mock_cloud.access_token = "test_access_token"
            mock_cloud.refresh_token = "test_refresh_token"
            on_start_callback = mock_cloud.register_on_start.call_args[0][0]
            await on_start_callback()

        mock_cloud.login.side_effect = mock_login

        async def mock_logout() -> None:
            """Mock logout."""
            mock_cloud.id_token = None
            mock_cloud.access_token = None
            mock_cloud.refresh_token = None
            await mock_cloud.stop()
            await mock_cloud.client.logout_cleanups()

        mock_cloud.logout.side_effect = mock_logout

        yield mock_cloud


@pytest.fixture(name="set_cloud_prefs")
def set_cloud_prefs_fixture(
    cloud: MagicMock,
) -> Callable[[dict[str, Any]], Coroutine[Any, Any, None]]:
    """Fixture for cloud component."""

    async def set_cloud_prefs(prefs_settings: dict[str, Any]) -> None:
        """Set cloud prefs."""
        prefs_to_set = cloud.client.prefs.as_dict()
        prefs_to_set.pop(PREF_ALEXA_DEFAULT_EXPOSE)
        prefs_to_set.pop(PREF_GOOGLE_DEFAULT_EXPOSE)
        prefs_to_set.update(prefs_settings)
        await cloud.client.prefs.async_update(**prefs_to_set)

    return set_cloud_prefs


@pytest.fixture(autouse=True)
def mock_tts_cache_dir_autouse(mock_tts_cache_dir: Path) -> None:
    """Mock the TTS cache dir with empty dir."""


@pytest.fixture(autouse=True)
def tts_mutagen_mock_fixture_autouse(tts_mutagen_mock: MagicMock) -> None:
    """Mock writing tags."""


@pytest.fixture(autouse=True)
def mock_user_data() -> Generator[MagicMock]:
    """Mock os module."""
    with patch("menuai_nabucasa.Cloud._write_user_info") as writer:
        yield writer


@pytest.fixture
async def mock_cloud_fixture(menuai: menuai) -> CloudPreferences:
    """Fixture for cloud component."""
    await mock_cloud(menuai)
    return mock_cloud_prefs(menuai, {})


@pytest.fixture
async def cloud_prefs(menuai: menuai) -> CloudPreferences:
    """Fixture for cloud preferences."""
    cloud_prefs = CloudPreferences(menuai)
    await cloud_prefs.async_initialize()
    return cloud_prefs


@pytest.fixture
async def mock_cloud_setup(menuai: menuai) -> None:
    """Set up the cloud."""
    await mock_cloud(menuai)


@pytest.fixture
def mock_cloud_login(menuai: menuai, mock_cloud_setup: None) -> Generator[None]:
    """Mock cloud is logged in."""
    menuai.data[DATA_CLOUD].id_token = jwt.encode(
        {
            "email": "hello@home-assistant.io",
            "custom:sub-exp": "2300-01-03",
            "cognito:username": "abcdefghjkl",
        },
        "test",
    )
    with patch.object(menuai.data[DATA_CLOUD].auth, "async_check_token"):
        yield


@pytest.fixture(name="mock_auth")
def mock_auth_fixture() -> Generator[None]:
    """Mock check token."""
    with (
        patch("menuai_nabucasa.auth.CognitoAuth.async_check_token"),
        patch("menuai_nabucasa.auth.CognitoAuth.async_renew_access_token"),
    ):
        yield


@pytest.fixture
def mock_expired_cloud_login(menuai: menuai, mock_cloud_setup: None) -> None:
    """Mock cloud is logged in."""
    menuai.data[DATA_CLOUD].id_token = jwt.encode(
        {
            "email": "hello@home-assistant.io",
            "custom:sub-exp": "2018-01-01",
            "cognito:username": "abcdefghjkl",
        },
        "test",
    )
