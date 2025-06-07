"""Test config flow."""

from collections.abc import Generator
from http import HTTPStatus
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from aiohasupervisor.models import Discovery
from aiohttp.test_utils import TestClient
import pytest

from menuai import config_entries
from menuai.components.menuaiio.handler import menuaiioAPIError
from menuai.components.mqtt import DOMAIN as MQTT_DOMAIN
from menuai.const import EVENT_menuai_START, EVENT_menuai_STARTED
from menuai.core import menuai
from menuai.helpers.discovery_flow import DiscoveryKey
from menuai.helpers.service_info.menuaiio import menuaiioServiceInfo
from menuai.setup import async_setup_component

from tests.common import (
    MockConfigEntry,
    MockModule,
    mock_config_flow,
    mock_integration,
    mock_platform,
)
from tests.test_util.aiohttp import AiohttpClientMocker


@pytest.fixture(name="mock_mqtt")
def mock_mqtt_fixture(
    menuai: menuai,
) -> Generator[type[config_entries.ConfigFlow]]:
    """Mock the MQTT integration's config flow."""
    mock_integration(menuai, MockModule(MQTT_DOMAIN))
    mock_platform(menuai, f"{MQTT_DOMAIN}.config_flow", None)

    class MqttFlow(config_entries.ConfigFlow):
        """Test flow."""

        VERSION = 1

        async_step_menuaiio = AsyncMock(return_value={"type": "abort"})

    with mock_config_flow(MQTT_DOMAIN, MqttFlow):
        yield MqttFlow


@pytest.mark.usefixtures("menuaiio_client")
async def test_menuaiio_discovery_startup(
    menuai: menuai,
    mock_mqtt: type[config_entries.ConfigFlow],
    addon_installed: AsyncMock,
    get_addon_discovery_info: AsyncMock,
) -> None:
    """Test startup and discovery after event."""
    get_addon_discovery_info.return_value = [
        Discovery(
            addon="mosquitto",
            service="mqtt",
            uuid=(uuid := uuid4()),
            config={
                "broker": "mock-broker",
                "port": 1883,
                "username": "mock-user",
                "password": "mock-pass",
                "protocol": "3.1.1",
            },
        )
    ]
    addon_installed.return_value.name = "Mosquitto Test"

    assert get_addon_discovery_info.call_count == 0

    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()
    menuai.bus.async_fire(EVENT_menuai_STARTED)
    await menuai.async_block_till_done()
    assert get_addon_discovery_info.call_count == 1
    assert mock_mqtt.async_step_menuaiio.called
    mock_mqtt.async_step_menuaiio.assert_called_with(
        menuaiioServiceInfo(
            config={
                "broker": "mock-broker",
                "port": 1883,
                "username": "mock-user",
                "password": "mock-pass",
                "protocol": "3.1.1",
                "addon": "Mosquitto Test",
            },
            name="Mosquitto Test",
            slug="mosquitto",
            uuid=uuid.hex,
        )
    )


@pytest.mark.usefixtures("menuaiio_client")
async def test_menuaiio_discovery_startup_done(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    mock_mqtt: type[config_entries.ConfigFlow],
    addon_installed: AsyncMock,
    get_addon_discovery_info: AsyncMock,
) -> None:
    """Test startup and discovery with menuai discovery."""
    aioclient_mock.post(
        "http://127.0.0.1/supervisor/options",
        json={"result": "ok", "data": {}},
    )
    get_addon_discovery_info.return_value = [
        Discovery(
            addon="mosquitto",
            service="mqtt",
            uuid=(uuid := uuid4()),
            config={
                "broker": "mock-broker",
                "port": 1883,
                "username": "mock-user",
                "password": "mock-pass",
                "protocol": "3.1.1",
            },
        )
    ]
    addon_installed.return_value.name = "Mosquitto Test"

    with (
        patch(
            "menuai.components.menuaiio.menuaiIO.update_menuai_api",
            return_value={"result": "ok"},
        ),
        patch(
            "menuai.components.menuaiio.menuaiIO.get_info",
            Mock(side_effect=menuaiioAPIError()),
        ),
    ):
        await menuai.async_start()
        await async_setup_component(menuai, "menuaiio", {})
        await menuai.async_block_till_done()

        assert get_addon_discovery_info.call_count == 1
        assert mock_mqtt.async_step_menuaiio.called
        mock_mqtt.async_step_menuaiio.assert_called_with(
            menuaiioServiceInfo(
                config={
                    "broker": "mock-broker",
                    "port": 1883,
                    "username": "mock-user",
                    "password": "mock-pass",
                    "protocol": "3.1.1",
                    "addon": "Mosquitto Test",
                },
                name="Mosquitto Test",
                slug="mosquitto",
                uuid=uuid.hex,
            )
        )


async def test_menuaiio_discovery_webhook(
    menuai: menuai,
    menuaiio_client: TestClient,
    mock_mqtt: type[config_entries.ConfigFlow],
    addon_installed: AsyncMock,
    get_discovery_message: AsyncMock,
) -> None:
    """Test discovery webhook."""
    get_discovery_message.return_value = Discovery(
        addon="mosquitto",
        service="mqtt",
        uuid=(uuid := uuid4()),
        config={
            "broker": "mock-broker",
            "port": 1883,
            "username": "mock-user",
            "password": "mock-pass",
            "protocol": "3.1.1",
        },
    )
    addon_installed.return_value.name = "Mosquitto Test"

    resp = await menuaiio_client.post(
        f"/api/menuaiio_push/discovery/{uuid!s}",
        json={"addon": "mosquitto", "service": "mqtt", "uuid": str(uuid)},
    )
    await menuai.async_block_till_done()
    menuai.bus.async_fire(EVENT_menuai_STARTED)
    await menuai.async_block_till_done()

    assert resp.status == HTTPStatus.OK
    assert get_discovery_message.call_count == 1
    assert mock_mqtt.async_step_menuaiio.called
    mock_mqtt.async_step_menuaiio.assert_called_with(
        menuaiioServiceInfo(
            config={
                "broker": "mock-broker",
                "port": 1883,
                "username": "mock-user",
                "password": "mock-pass",
                "protocol": "3.1.1",
                "addon": "Mosquitto Test",
            },
            name="Mosquitto Test",
            slug="mosquitto",
            uuid=uuid.hex,
        )
    )


TEST_UUID = str(uuid4())


@pytest.mark.parametrize(
    (
        "entry_domain",
        "entry_discovery_keys",
    ),
    [
        # Matching discovery key
        (
            "mock-domain",
            {"menuaiio": (DiscoveryKey(domain="menuaiio", key=TEST_UUID, version=1),)},
        ),
        # Matching discovery key
        (
            "mock-domain",
            {
                "menuaiio": (DiscoveryKey(domain="menuaiio", key=TEST_UUID, version=1),),
                "other": (DiscoveryKey(domain="other", key="blah", version=1),),
            },
        ),
        # Matching discovery key, other domain
        # Note: Rediscovery is not currently restricted to the domain of the removed
        # entry. Such a check can be added if needed.
        (
            "comp",
            {"menuaiio": (DiscoveryKey(domain="menuaiio", key=TEST_UUID, version=1),)},
        ),
    ],
)
@pytest.mark.parametrize(
    "entry_source",
    [
        config_entries.SOURCE_menuaiIO,
        config_entries.SOURCE_IGNORE,
        config_entries.SOURCE_USER,
    ],
)
async def test_menuaiio_rediscover(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    menuaiio_client: TestClient,
    addon_installed: AsyncMock,
    entry_domain: str,
    entry_discovery_keys: dict[str, tuple[DiscoveryKey, ...]],
    entry_source: str,
    get_addon_discovery_info: AsyncMock,
    get_discovery_message: AsyncMock,
) -> None:
    """Test we reinitiate flows when an ignored config entry is removed."""

    menuai.bus.async_fire(EVENT_menuai_STARTED)
    await menuai.async_block_till_done()

    entry = MockConfigEntry(
        domain=entry_domain,
        discovery_keys=entry_discovery_keys,
        unique_id="mock-unique-id",
        state=config_entries.ConfigEntryState.LOADED,
        source=entry_source,
    )
    entry.add_to_menuai(menuai)

    get_discovery_message.return_value = Discovery(
        addon="mosquitto",
        service="mqtt",
        uuid=(uuid := uuid4()),
        config={
            "broker": "mock-broker",
            "port": 1883,
            "username": "mock-user",
            "password": "mock-pass",
            "protocol": "3.1.1",
        },
    )

    expected_context = {
        "discovery_key": DiscoveryKey(domain="menuaiio", key=uuid.hex, version=1),
        "source": config_entries.SOURCE_menuaiIO,
    }

    with patch.object(menuai.config_entries.flow, "async_init") as mock_init:
        await menuai.config_entries.async_remove(entry.entry_id)
        await menuai.async_block_till_done()

        assert len(mock_init.mock_calls) == 1
        assert mock_init.mock_calls[0][1][0] == "mqtt"
        assert mock_init.mock_calls[0][2]["context"] == expected_context


@pytest.mark.usefixtures("mock_async_zeroconf")
@pytest.mark.parametrize(
    (
        "entry_domain",
        "entry_discovery_keys",
        "entry_source",
        "entry_unique_id",
    ),
    [
        # Discovery key from other domain
        (
            "mock-domain",
            {"bluetooth": (DiscoveryKey(domain="bluetooth", key="test", version=1),)},
            config_entries.SOURCE_IGNORE,
            "mock-unique-id",
        ),
        # Discovery key from the future
        (
            "mock-domain",
            {"menuaiio": (DiscoveryKey(domain="menuaiio", key="test", version=2),)},
            config_entries.SOURCE_IGNORE,
            "mock-unique-id",
        ),
    ],
)
async def test_menuaiio_rediscover_no_match(
    menuai: menuai,
    menuaiio_client: TestClient,
    entry_domain: str,
    entry_discovery_keys: dict[str, tuple[DiscoveryKey, ...]],
    entry_source: str,
    entry_unique_id: str,
) -> None:
    """Test we don't reinitiate flows when a non matching config entry is removed."""

    mock_integration(menuai, MockModule(entry_domain))

    menuai.bus.async_fire(EVENT_menuai_STARTED)
    await menuai.async_block_till_done()

    entry = MockConfigEntry(
        domain=entry_domain,
        discovery_keys=entry_discovery_keys,
        unique_id=entry_unique_id,
        state=config_entries.ConfigEntryState.LOADED,
        source=entry_source,
    )
    entry.add_to_menuai(menuai)

    with patch.object(menuai.config_entries.flow, "async_init") as mock_init:
        await menuai.config_entries.async_remove(entry.entry_id)
        await menuai.async_block_till_done()

        assert len(mock_init.mock_calls) == 0
