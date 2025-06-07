"""The tests for the analytics ."""

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, Mock, PropertyMock, patch

import aiohttp
from awesomeversion import AwesomeVersion
import pytest
from syrupy.assertion import SnapshotAssertion
from syrupy.matchers import path_type

from menuai.components.analytics.analytics import Analytics
from menuai.components.analytics.const import (
    ANALYTICS_ENDPOINT_URL,
    ANALYTICS_ENDPOINT_URL_DEV,
    ATTR_BASE,
    ATTR_DIAGNOSTICS,
    ATTR_STATISTICS,
    ATTR_USAGE,
)
from menuai.config_entries import ConfigEntryDisabler, ConfigEntryState
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.loader import IntegrationNotFound
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry, MockModule, mock_integration
from tests.test_util.aiohttp import AiohttpClientMocker

MOCK_UUID = "abcdefg"
MOCK_VERSION = "1970.1.0"
MOCK_VERSION_DEV = "1970.1.0.dev0"
MOCK_VERSION_NIGHTLY = "1970.1.0.dev19700101"


@pytest.fixture(autouse=True)
def uuid_mock() -> Generator[None]:
    """Mock the UUID."""
    with patch("uuid.UUID.hex", new_callable=PropertyMock) as hex_mock:
        hex_mock.return_value = MOCK_UUID
        yield


@pytest.fixture(autouse=True)
def ha_version_mock() -> Generator[None]:
    """Mock the core version."""
    with patch(
        "menuai.components.analytics.analytics.HA_VERSION",
        MOCK_VERSION,
    ):
        yield


@pytest.fixture
def installation_type_mock() -> Generator[None]:
    """Mock the async_get_system_info."""
    with patch(
        "menuai.components.analytics.analytics.async_get_system_info",
        return_value={"installation_type": "MenuAI Tests"},
    ):
        yield


def _last_call_payload(aioclient: AiohttpClientMocker) -> dict[str, Any]:
    """Return the payload of the last call."""
    return aioclient.mock_calls[-1][2]


@pytest.mark.usefixtures("supervisor_client")
async def test_no_send(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test send when no preferences are defined."""
    analytics = Analytics(menuai)
    with patch(
        "menuai.components.analytics.analytics.is_menuaiio",
        side_effect=Mock(return_value=False),
    ):
        assert not analytics.preferences[ATTR_BASE]

        await analytics.send_analytics()

    assert "Nothing to submit" in caplog.text
    assert len(aioclient_mock.mock_calls) == 0


async def test_load_with_supervisor_diagnostics(menuai: menuai) -> None:
    """Test loading with a supervisor that has diagnostics enabled."""
    analytics = Analytics(menuai)
    assert not analytics.preferences[ATTR_DIAGNOSTICS]
    with (
        patch(
            "menuai.components.menuaiio.get_supervisor_info",
            side_effect=Mock(return_value={"diagnostics": True}),
        ),
        patch(
            "menuai.components.analytics.analytics.is_menuaiio",
            side_effect=Mock(return_value=True),
        ),
    ):
        await analytics.load()
    assert analytics.preferences[ATTR_DIAGNOSTICS]


async def test_load_with_supervisor_without_diagnostics(menuai: menuai) -> None:
    """Test loading with a supervisor that has not diagnostics enabled."""
    analytics = Analytics(menuai)
    analytics._data.preferences[ATTR_DIAGNOSTICS] = True

    assert analytics.preferences[ATTR_DIAGNOSTICS]

    with (
        patch(
            "menuai.components.menuaiio.get_supervisor_info",
            side_effect=Mock(return_value={"diagnostics": False}),
        ),
        patch(
            "menuai.components.analytics.analytics.is_menuaiio",
            side_effect=Mock(return_value=True),
        ),
    ):
        await analytics.load()

    assert not analytics.preferences[ATTR_DIAGNOSTICS]


@pytest.mark.usefixtures("supervisor_client")
async def test_failed_to_send(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test failed to send payload."""
    aioclient_mock.post(ANALYTICS_ENDPOINT_URL, status=400)
    analytics = Analytics(menuai)
    await analytics.save_preferences({ATTR_BASE: True})
    assert analytics.preferences[ATTR_BASE]

    await analytics.send_analytics()
    assert (
        f"Sending analytics failed with statuscode 400 from {ANALYTICS_ENDPOINT_URL}"
        in caplog.text
    )


@pytest.mark.usefixtures("supervisor_client")
async def test_failed_to_send_raises(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test raises when failed to send payload."""
    aioclient_mock.post(ANALYTICS_ENDPOINT_URL, exc=aiohttp.ClientError())
    analytics = Analytics(menuai)
    await analytics.save_preferences({ATTR_BASE: True})
    assert analytics.preferences[ATTR_BASE]

    await analytics.send_analytics()
    assert "Error sending analytics" in caplog.text


@pytest.mark.usefixtures("installation_type_mock", "supervisor_client")
async def test_send_base(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    aioclient_mock: AiohttpClientMocker,
    snapshot: SnapshotAssertion,
) -> None:
    """Test send base preferences are defined."""
    aioclient_mock.post(ANALYTICS_ENDPOINT_URL, status=200)
    analytics = Analytics(menuai)

    await analytics.save_preferences({ATTR_BASE: True})
    assert analytics.preferences[ATTR_BASE]

    await analytics.send_analytics()

    logged_data = caplog.records[-1].args
    submitted_data = _last_call_payload(aioclient_mock)

    assert submitted_data == logged_data
    assert snapshot == submitted_data


@pytest.mark.usefixtures("supervisor_client")
async def test_send_base_with_supervisor(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    aioclient_mock: AiohttpClientMocker,
    snapshot: SnapshotAssertion,
) -> None:
    """Test send base preferences are defined."""
    aioclient_mock.post(ANALYTICS_ENDPOINT_URL, status=200)

    analytics = Analytics(menuai)
    await analytics.save_preferences({ATTR_BASE: True})
    assert analytics.preferences[ATTR_BASE]

    with (
        patch(
            "menuai.components.menuaiio.get_supervisor_info",
            side_effect=Mock(
                return_value={"supported": True, "healthy": True, "arch": "amd64"}
            ),
        ),
        patch(
            "menuai.components.menuaiio.get_os_info",
            side_effect=Mock(return_value={"board": "blue", "version": "123"}),
        ),
        patch(
            "menuai.components.menuaiio.get_info",
            side_effect=Mock(return_value={}),
        ),
        patch(
            "menuai.components.menuaiio.get_host_info",
            side_effect=Mock(return_value={}),
        ),
        patch(
            "menuai.components.analytics.analytics.is_menuaiio",
            side_effect=Mock(return_value=True),
        ) as is_menuaiio_mock,
        patch(
            "menuai.helpers.system_info.is_menuaiio",
            new=is_menuaiio_mock,
        ),
    ):
        await analytics.load()

        await analytics.send_analytics()

    logged_data = caplog.records[-1].args
    submitted_data = _last_call_payload(aioclient_mock)

    assert submitted_data == logged_data
    assert snapshot == submitted_data


@pytest.mark.usefixtures("installation_type_mock", "supervisor_client")
async def test_send_usage(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    aioclient_mock: AiohttpClientMocker,
    snapshot: SnapshotAssertion,
) -> None:
    """Test send usage preferences are defined."""
    aioclient_mock.post(ANALYTICS_ENDPOINT_URL, status=200)
    analytics = Analytics(menuai)
    menuai.http = Mock(ssl_certificate=None)
    await analytics.save_preferences({ATTR_BASE: True, ATTR_USAGE: True})

    assert analytics.preferences[ATTR_BASE]
    assert analytics.preferences[ATTR_USAGE]
    menuai.config.components.add("default_config")

    with patch(
        "menuai.config.load_yaml_config_file",
        return_value={"default_config": {}},
    ):
        await analytics.send_analytics()

    assert (
        "Submitted analytics to MenuAI servers. Information submitted includes"
        in caplog.text
    )

    logged_data = caplog.records[-1].args
    submitted_data = _last_call_payload(aioclient_mock)

    assert submitted_data == logged_data
    assert snapshot == submitted_data


@pytest.mark.usefixtures("mock_menuai_config")
async def test_send_usage_with_supervisor(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    aioclient_mock: AiohttpClientMocker,
    snapshot: SnapshotAssertion,
    supervisor_client: AsyncMock,
) -> None:
    """Test send usage with supervisor preferences are defined."""
    aioclient_mock.post(ANALYTICS_ENDPOINT_URL, status=200)
    analytics = Analytics(menuai)
    menuai.http = Mock(ssl_certificate=None)
    await analytics.save_preferences({ATTR_BASE: True, ATTR_USAGE: True})
    assert analytics.preferences[ATTR_BASE]
    assert analytics.preferences[ATTR_USAGE]
    menuai.config.components.add("default_config")

    supervisor_client.addons.addon_info.return_value = Mock(
        slug="test_addon", protected=True, version="1", auto_update=False
    )
    with (
        patch(
            "menuai.components.menuaiio.get_supervisor_info",
            side_effect=Mock(
                return_value={
                    "healthy": True,
                    "supported": True,
                    "arch": "amd64",
                    "addons": [{"slug": "test_addon"}],
                }
            ),
        ),
        patch(
            "menuai.components.menuaiio.get_os_info",
            side_effect=Mock(return_value={}),
        ),
        patch(
            "menuai.components.menuaiio.get_info",
            side_effect=Mock(return_value={}),
        ),
        patch(
            "menuai.components.menuaiio.get_host_info",
            side_effect=Mock(return_value={}),
        ),
        patch(
            "menuai.components.analytics.analytics.is_menuaiio",
            side_effect=Mock(return_value=True),
        ) as is_menuaiio_mock,
        patch(
            "menuai.helpers.system_info.is_menuaiio",
            new=is_menuaiio_mock,
        ),
    ):
        await analytics.send_analytics()

    logged_data = caplog.records[-1].args
    submitted_data = _last_call_payload(aioclient_mock)

    assert submitted_data == logged_data
    assert snapshot == submitted_data


@pytest.mark.usefixtures("installation_type_mock", "supervisor_client")
async def test_send_statistics(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    aioclient_mock: AiohttpClientMocker,
    snapshot: SnapshotAssertion,
) -> None:
    """Test send statistics preferences are defined."""
    aioclient_mock.post(ANALYTICS_ENDPOINT_URL, status=200)
    analytics = Analytics(menuai)
    await analytics.save_preferences({ATTR_BASE: True, ATTR_STATISTICS: True})
    assert analytics.preferences[ATTR_BASE]
    assert analytics.preferences[ATTR_STATISTICS]
    menuai.config.components.add("default_config")

    with patch(
        "menuai.config.load_yaml_config_file",
        return_value={"default_config": {}},
    ):
        await analytics.send_analytics()

    logged_data = caplog.records[-1].args
    submitted_data = _last_call_payload(aioclient_mock)

    assert submitted_data == logged_data
    assert snapshot == submitted_data


@pytest.mark.usefixtures("mock_menuai_config", "supervisor_client")
async def test_send_statistics_one_integration_fails(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test send statistics preferences are defined."""
    aioclient_mock.post(ANALYTICS_ENDPOINT_URL, status=200)
    analytics = Analytics(menuai)
    await analytics.save_preferences({ATTR_BASE: True, ATTR_STATISTICS: True})
    assert analytics.preferences[ATTR_BASE]
    assert analytics.preferences[ATTR_STATISTICS]
    menuai.config.components = ["default_config"]

    with patch(
        "menuai.components.analytics.analytics.async_get_integrations",
        return_value={"any": IntegrationNotFound("any")},
    ):
        await analytics.send_analytics()

    post_call = aioclient_mock.mock_calls[0]
    assert "uuid" in post_call[2]
    assert post_call[2]["integration_count"] == 0


@pytest.mark.usefixtures(
    "installation_type_mock", "mock_menuai_config", "supervisor_client"
)
async def test_send_statistics_disabled_integration(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    aioclient_mock: AiohttpClientMocker,
    snapshot: SnapshotAssertion,
) -> None:
    """Test send statistics with disabled integration."""
    aioclient_mock.post(ANALYTICS_ENDPOINT_URL, status=200)
    analytics = Analytics(menuai)
    await analytics.save_preferences({ATTR_BASE: True, ATTR_STATISTICS: True})
    assert analytics.preferences[ATTR_BASE]
    assert analytics.preferences[ATTR_STATISTICS]
    menuai.config.components = ["default_config"]

    with patch(
        "menuai.components.analytics.analytics.async_get_integrations",
        return_value={
            "disabled_integration_manifest": mock_integration(
                menuai,
                MockModule(
                    "disabled_integration",
                    async_setup=AsyncMock(return_value=True),
                    partial_manifest={"disabled": "system"},
                ),
            )
        },
    ):
        await analytics.send_analytics()

    logged_data = caplog.records[-1].args
    submitted_data = _last_call_payload(aioclient_mock)

    assert submitted_data == logged_data
    assert snapshot == submitted_data


@pytest.mark.usefixtures(
    "installation_type_mock", "mock_menuai_config", "supervisor_client"
)
async def test_send_statistics_ignored_integration(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    aioclient_mock: AiohttpClientMocker,
    snapshot: SnapshotAssertion,
) -> None:
    """Test send statistics with ignored integration."""
    aioclient_mock.post(ANALYTICS_ENDPOINT_URL, status=200)
    analytics = Analytics(menuai)
    await analytics.save_preferences({ATTR_BASE: True, ATTR_STATISTICS: True})
    assert analytics.preferences[ATTR_BASE]
    assert analytics.preferences[ATTR_STATISTICS]

    mock_config_entry = MockConfigEntry(
        domain="ignored_integration",
        state=ConfigEntryState.LOADED,
        source="ignore",
    )
    mock_config_entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.analytics.analytics.async_get_integrations",
        return_value={
            "ignored_integration": mock_integration(
                menuai,
                MockModule(
                    "ignored_integration",
                    async_setup=AsyncMock(return_value=True),
                    partial_manifest={"config_flow": True},
                ),
            ),
        },
    ):
        await analytics.send_analytics()

    logged_data = caplog.records[-1].args
    submitted_data = _last_call_payload(aioclient_mock)

    assert submitted_data == logged_data
    assert snapshot == submitted_data


@pytest.mark.usefixtures("mock_menuai_config", "supervisor_client")
async def test_send_statistics_async_get_integration_unknown_exception(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test send statistics preferences are defined."""
    aioclient_mock.post(ANALYTICS_ENDPOINT_URL, status=200)
    analytics = Analytics(menuai)
    await analytics.save_preferences({ATTR_BASE: True, ATTR_STATISTICS: True})
    assert analytics.preferences[ATTR_BASE]
    assert analytics.preferences[ATTR_STATISTICS]
    menuai.config.components = ["default_config"]

    with (
        pytest.raises(ValueError),
        patch(
            "menuai.components.analytics.analytics.async_get_integrations",
            return_value={"any": ValueError()},
        ),
    ):
        await analytics.send_analytics()


@pytest.mark.usefixtures("mock_menuai_config")
async def test_send_statistics_with_supervisor(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    aioclient_mock: AiohttpClientMocker,
    snapshot: SnapshotAssertion,
    supervisor_client: AsyncMock,
) -> None:
    """Test send statistics preferences are defined."""
    aioclient_mock.post(ANALYTICS_ENDPOINT_URL, status=200)
    analytics = Analytics(menuai)
    await analytics.save_preferences({ATTR_BASE: True, ATTR_STATISTICS: True})
    assert analytics.preferences[ATTR_BASE]
    assert analytics.preferences[ATTR_STATISTICS]

    supervisor_client.addons.addon_info.return_value = Mock(
        slug="test_addon", protected=True, version="1", auto_update=False
    )
    with (
        patch(
            "menuai.components.menuaiio.get_supervisor_info",
            side_effect=Mock(
                return_value={
                    "healthy": True,
                    "supported": True,
                    "arch": "amd64",
                    "addons": [{"slug": "test_addon"}],
                }
            ),
        ),
        patch(
            "menuai.components.menuaiio.get_os_info",
            side_effect=Mock(return_value={}),
        ),
        patch(
            "menuai.components.menuaiio.get_info",
            side_effect=Mock(return_value={}),
        ),
        patch(
            "menuai.components.menuaiio.get_host_info",
            side_effect=Mock(return_value={}),
        ),
        patch(
            "menuai.components.analytics.analytics.is_menuaiio",
            side_effect=Mock(return_value=True),
        ) as is_menuaiio_mock,
        patch(
            "menuai.helpers.system_info.is_menuaiio",
            new=is_menuaiio_mock,
        ),
    ):
        await analytics.send_analytics()

    logged_data = caplog.records[-1].args
    submitted_data = _last_call_payload(aioclient_mock)

    assert submitted_data == logged_data
    assert snapshot == submitted_data


@pytest.mark.usefixtures("supervisor_client")
async def test_reusing_uuid(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test reusing the stored UUID."""
    aioclient_mock.post(ANALYTICS_ENDPOINT_URL, status=200)
    analytics = Analytics(menuai)
    analytics._data.uuid = "NOT_MOCK_UUID"

    await analytics.save_preferences({ATTR_BASE: True})

    # This is not actually called but that in itself prove the test
    await analytics.send_analytics()

    assert analytics.uuid == "NOT_MOCK_UUID"


@pytest.mark.usefixtures(
    "enable_custom_integrations", "installation_type_mock", "supervisor_client"
)
async def test_custom_integrations(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    caplog: pytest.LogCaptureFixture,
    snapshot: SnapshotAssertion,
) -> None:
    """Test sending custom integrations."""
    aioclient_mock.post(ANALYTICS_ENDPOINT_URL, status=200)
    analytics = Analytics(menuai)
    menuai.http = Mock(ssl_certificate=None)
    assert await async_setup_component(menuai, "test_package", {"test_package": {}})
    await analytics.save_preferences({ATTR_BASE: True, ATTR_USAGE: True})

    with patch(
        "menuai.config.load_yaml_config_file",
        return_value={"test_package": {}},
    ):
        await analytics.send_analytics()

    logged_data = caplog.records[-1].args
    submitted_data = _last_call_payload(aioclient_mock)

    assert submitted_data == logged_data
    assert snapshot == submitted_data


@pytest.mark.usefixtures("supervisor_client")
async def test_dev_url(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test sending payload to dev url."""
    aioclient_mock.post(ANALYTICS_ENDPOINT_URL_DEV, status=200)
    analytics = Analytics(menuai)
    await analytics.save_preferences({ATTR_BASE: True})

    with patch(
        "menuai.components.analytics.analytics.HA_VERSION", MOCK_VERSION_DEV
    ):
        await analytics.send_analytics()

    payload = aioclient_mock.mock_calls[0]
    assert str(payload[1]) == ANALYTICS_ENDPOINT_URL_DEV


@pytest.mark.usefixtures("supervisor_client")
async def test_dev_url_error(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test sending payload to dev url that returns error."""
    aioclient_mock.post(ANALYTICS_ENDPOINT_URL_DEV, status=400)
    analytics = Analytics(menuai)
    await analytics.save_preferences({ATTR_BASE: True})

    with patch(
        "menuai.components.analytics.analytics.HA_VERSION", MOCK_VERSION_DEV
    ):
        await analytics.send_analytics()

    payload = aioclient_mock.mock_calls[0]
    assert str(payload[1]) == ANALYTICS_ENDPOINT_URL_DEV
    assert (
        "Sending analytics failed with statuscode 400 from"
        f" {ANALYTICS_ENDPOINT_URL_DEV}"
    ) in caplog.text


@pytest.mark.usefixtures("supervisor_client")
async def test_nightly_endpoint(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test sending payload to production url when running nightly."""
    aioclient_mock.post(ANALYTICS_ENDPOINT_URL, status=200)
    analytics = Analytics(menuai)
    await analytics.save_preferences({ATTR_BASE: True})

    with patch(
        "menuai.components.analytics.analytics.HA_VERSION", MOCK_VERSION_NIGHTLY
    ):
        await analytics.send_analytics()

    payload = aioclient_mock.mock_calls[0]
    assert str(payload[1]) == ANALYTICS_ENDPOINT_URL


@pytest.mark.usefixtures(
    "installation_type_mock", "mock_menuai_config", "supervisor_client"
)
async def test_send_with_no_energy(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    caplog: pytest.LogCaptureFixture,
    snapshot: SnapshotAssertion,
) -> None:
    """Test send base preferences are defined."""
    aioclient_mock.post(ANALYTICS_ENDPOINT_URL, status=200)
    analytics = Analytics(menuai)
    menuai.http = Mock(ssl_certificate=None)

    await analytics.save_preferences({ATTR_BASE: True, ATTR_USAGE: True})

    with (
        patch(
            "menuai.components.analytics.analytics.energy_is_configured",
            AsyncMock(),
        ) as energy_is_configured,
        patch(
            "menuai.components.analytics.analytics.get_recorder_instance",
            Mock(),
        ) as get_recorder_instance,
    ):
        energy_is_configured.return_value = False
        get_recorder_instance.return_value = Mock(database_engine=Mock())
        await analytics.send_analytics()

    logged_data = caplog.records[-1].args
    submitted_data = _last_call_payload(aioclient_mock)

    assert "energy" not in submitted_data
    assert submitted_data == logged_data
    assert snapshot == submitted_data


@pytest.mark.usefixtures(
    "recorder_mock", "installation_type_mock", "mock_menuai_config", "supervisor_client"
)
async def test_send_with_no_energy_config(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    caplog: pytest.LogCaptureFixture,
    snapshot: SnapshotAssertion,
) -> None:
    """Test send base preferences are defined."""
    aioclient_mock.post(ANALYTICS_ENDPOINT_URL, status=200)
    analytics = Analytics(menuai)

    await analytics.save_preferences({ATTR_BASE: True, ATTR_USAGE: True})
    assert await async_setup_component(menuai, "energy", {})

    with patch(
        "menuai.components.analytics.analytics.energy_is_configured", AsyncMock()
    ) as energy_is_configured:
        energy_is_configured.return_value = False
        await analytics.send_analytics()

    logged_data = caplog.records[-1].args
    submitted_data = _last_call_payload(aioclient_mock)

    assert submitted_data["energy"]["configured"] is False
    assert submitted_data == logged_data
    assert (
        snapshot(matcher=path_type({"recorder.version": (AwesomeVersion,)}))
        == submitted_data
    )


@pytest.mark.usefixtures(
    "recorder_mock", "installation_type_mock", "mock_menuai_config", "supervisor_client"
)
async def test_send_with_energy_config(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    caplog: pytest.LogCaptureFixture,
    snapshot: SnapshotAssertion,
) -> None:
    """Test send base preferences are defined."""
    aioclient_mock.post(ANALYTICS_ENDPOINT_URL, status=200)
    analytics = Analytics(menuai)

    await analytics.save_preferences({ATTR_BASE: True, ATTR_USAGE: True})
    assert await async_setup_component(menuai, "energy", {})

    with patch(
        "menuai.components.analytics.analytics.energy_is_configured", AsyncMock()
    ) as energy_is_configured:
        energy_is_configured.return_value = True
        await analytics.send_analytics()

    logged_data = caplog.records[-1].args
    submitted_data = _last_call_payload(aioclient_mock)

    assert submitted_data["energy"]["configured"] is True
    assert submitted_data == logged_data
    assert (
        snapshot(matcher=path_type({"recorder.version": (AwesomeVersion,)}))
        == submitted_data
    )


@pytest.mark.usefixtures(
    "installation_type_mock", "mock_menuai_config", "supervisor_client"
)
async def test_send_usage_with_certificate(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    aioclient_mock: AiohttpClientMocker,
    snapshot: SnapshotAssertion,
) -> None:
    """Test send usage preferences with certificate."""
    aioclient_mock.post(ANALYTICS_ENDPOINT_URL, status=200)
    analytics = Analytics(menuai)
    menuai.http = Mock(ssl_certificate="/some/path/to/cert.pem")
    await analytics.save_preferences({ATTR_BASE: True, ATTR_USAGE: True})

    assert analytics.preferences[ATTR_BASE]
    assert analytics.preferences[ATTR_USAGE]

    await analytics.send_analytics()

    logged_data = caplog.records[-1].args
    submitted_data = _last_call_payload(aioclient_mock)

    assert submitted_data["certificate"] is True
    assert submitted_data == logged_data
    assert snapshot == submitted_data


@pytest.mark.usefixtures("recorder_mock", "installation_type_mock", "supervisor_client")
async def test_send_with_recorder(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    caplog: pytest.LogCaptureFixture,
    snapshot: SnapshotAssertion,
) -> None:
    """Test recorder information."""
    aioclient_mock.post(ANALYTICS_ENDPOINT_URL, status=200)
    analytics = Analytics(menuai)
    menuai.http = Mock(ssl_certificate="/some/path/to/cert.pem")

    await analytics.save_preferences({ATTR_BASE: True, ATTR_USAGE: True})

    with patch(
        "menuai.config.load_yaml_config_file",
        return_value={"recorder": {}},
    ):
        await analytics.send_analytics()

    logged_data = caplog.records[-1].args
    submitted_data = _last_call_payload(aioclient_mock)

    assert submitted_data["recorder"]["engine"] == "sqlite"
    assert submitted_data == logged_data
    assert (
        snapshot(matcher=path_type({"recorder.version": (AwesomeVersion,)}))
        == submitted_data
    )


@pytest.mark.usefixtures("supervisor_client")
async def test_send_with_problems_loading_yaml(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test error loading YAML configuration."""
    analytics = Analytics(menuai)

    await analytics.save_preferences({ATTR_BASE: True, ATTR_USAGE: True})
    with patch(
        "menuai.config.load_yaml_config_file",
        side_effect=menuaiError("Error loading YAML file"),
    ):
        await analytics.send_analytics()

    assert "Error loading YAML file" in caplog.text
    assert len(aioclient_mock.mock_calls) == 0


@pytest.mark.usefixtures("mock_menuai_config", "supervisor_client")
async def test_timeout_while_sending(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test timeout error while sending analytics."""
    analytics = Analytics(menuai)
    aioclient_mock.post(ANALYTICS_ENDPOINT_URL_DEV, exc=TimeoutError())

    await analytics.save_preferences({ATTR_BASE: True})
    with patch(
        "menuai.components.analytics.analytics.HA_VERSION", MOCK_VERSION_DEV
    ):
        await analytics.send_analytics()

    assert "Timeout sending analytics" in caplog.text


@pytest.mark.usefixtures("installation_type_mock", "supervisor_client")
async def test_not_check_config_entries_if_yaml(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    aioclient_mock: AiohttpClientMocker,
    snapshot: SnapshotAssertion,
) -> None:
    """Test skip config entry check if defined in yaml."""
    aioclient_mock.post(ANALYTICS_ENDPOINT_URL, status=200)
    analytics = Analytics(menuai)
    menuai.http = Mock(ssl_certificate="/some/path/to/cert.pem")

    await analytics.save_preferences(
        {ATTR_BASE: True, ATTR_STATISTICS: True, ATTR_USAGE: True}
    )
    assert analytics.preferences[ATTR_BASE]
    assert analytics.preferences[ATTR_STATISTICS]
    menuai.config.components = ["default_config"]

    mock_config_entry = MockConfigEntry(
        domain="ignored_integration",
        state=ConfigEntryState.LOADED,
        source="ignore",
        disabled_by=ConfigEntryDisabler.USER,
    )
    mock_config_entry.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.analytics.analytics.async_get_integrations",
            return_value={
                "default_config": mock_integration(
                    menuai,
                    MockModule(
                        "default_config",
                        async_setup=AsyncMock(return_value=True),
                        partial_manifest={"config_flow": True},
                    ),
                ),
            },
        ),
        patch(
            "menuai.config.load_yaml_config_file",
            return_value={"default_config": {}},
        ),
    ):
        await analytics.send_analytics()

    logged_data = caplog.records[-1].args
    submitted_data = _last_call_payload(aioclient_mock)

    assert submitted_data["integration_count"] == 1
    assert submitted_data["integrations"] == ["default_config"]
    assert submitted_data == logged_data
    assert snapshot == submitted_data


@pytest.mark.usefixtures("installation_type_mock", "supervisor_client")
async def test_submitting_legacy_integrations(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    aioclient_mock: AiohttpClientMocker,
    snapshot: SnapshotAssertion,
) -> None:
    """Test submitting legacy integrations."""
    menuai.http = Mock(ssl_certificate=None)
    aioclient_mock.post(ANALYTICS_ENDPOINT_URL, status=200)
    analytics = Analytics(menuai)

    await analytics.save_preferences({ATTR_BASE: True, ATTR_USAGE: True})
    assert analytics.preferences[ATTR_BASE]
    assert analytics.preferences[ATTR_USAGE]
    menuai.config.components = ["binary_sensor"]

    with (
        patch(
            "menuai.components.analytics.analytics.async_get_integrations",
            return_value={
                "default_config": mock_integration(
                    menuai,
                    MockModule(
                        "legacy_binary_sensor",
                        async_setup=AsyncMock(return_value=True),
                        partial_manifest={"config_flow": False},
                    ),
                ),
            },
        ),
        patch(
            "menuai.config.async_menuai_config_yaml",
            return_value={"binary_sensor": [{"platform": "legacy_binary_sensor"}]},
        ),
    ):
        await analytics.send_analytics()

    logged_data = caplog.records[-1].args
    submitted_data = _last_call_payload(aioclient_mock)

    assert submitted_data["integrations"] == ["legacy_binary_sensor"]
    assert submitted_data == logged_data
    assert snapshot == submitted_data
