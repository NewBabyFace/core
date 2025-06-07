"""Test creating repairs from alerts."""

from __future__ import annotations

from datetime import timedelta
import json
from unittest.mock import ANY, patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_unordered import unordered

from menuai.components.menuai_alerts.const import (
    COMPONENT_LOADED_COOLDOWN,
    DOMAIN,
    UPDATE_INTERVAL,
)
from menuai.components.repairs import DOMAIN as REPAIRS_DOMAIN
from menuai.const import EVENT_COMPONENT_LOADED
from menuai.core import menuai
from menuai.setup import ATTR_COMPONENT, async_setup_component
from menuai.util import dt as dt_util

from tests.common import async_fire_time_changed, async_load_fixture
from tests.test_util.aiohttp import AiohttpClientMocker
from tests.typing import WebSocketGenerator


def stub_alert(aioclient_mock: AiohttpClientMocker, alert_id) -> None:
    """Stub an alert."""
    aioclient_mock.get(
        f"https://alerts.home-assistant.io/alerts/{alert_id}.json",
        json={"title": f"Title for {alert_id}", "content": f"Content for {alert_id}"},
    )


@pytest.fixture(autouse=True)
async def setup_repairs(menuai: menuai) -> None:
    """Set up the repairs integration."""
    assert await async_setup_component(menuai, REPAIRS_DOMAIN, {REPAIRS_DOMAIN: {}})


@pytest.mark.parametrize(
    ("ha_version", "supervisor_info", "expected_alerts"),
    [
        (
            "2022.7.0",
            {"version": "2022.11.0"},
            [
                ("aladdin_connect", "aladdin_connect"),
                ("dark_sky", "darksky"),
                ("menuaiio", "menuaiio"),
                ("hikvision", "hikvision"),
                ("hikvision", "hikvisioncam"),
                ("hive_us", "hive"),
                ("homematicip_cloud", "homematicip_cloud"),
                ("logi_circle", "logi_circle"),
                ("neato", "neato"),
                ("nest", "nest"),
                ("senseme", "senseme"),
                ("sochain", "sochain"),
            ],
        ),
        (
            "2022.8.0",
            {"version": "2022.11.1"},
            [
                ("dark_sky", "darksky"),
                ("hikvision", "hikvision"),
                ("hikvision", "hikvisioncam"),
                ("hive_us", "hive"),
                ("homematicip_cloud", "homematicip_cloud"),
                ("logi_circle", "logi_circle"),
                ("neato", "neato"),
                ("nest", "nest"),
                ("senseme", "senseme"),
                ("sochain", "sochain"),
            ],
        ),
        (
            "2021.10.0",
            None,
            [
                ("aladdin_connect", "aladdin_connect"),
                ("dark_sky", "darksky"),
                ("hikvision", "hikvision"),
                ("hikvision", "hikvisioncam"),
                ("homematicip_cloud", "homematicip_cloud"),
                ("logi_circle", "logi_circle"),
                ("neato", "neato"),
                ("nest", "nest"),
                ("senseme", "senseme"),
                ("sochain", "sochain"),
            ],
        ),
    ],
)
async def test_alerts(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    aioclient_mock: AiohttpClientMocker,
    ha_version: str,
    supervisor_info: dict[str, str] | None,
    expected_alerts: list[tuple[str, str]],
) -> None:
    """Test creating issues based on alerts."""

    aioclient_mock.clear_requests()
    aioclient_mock.get(
        "https://alerts.home-assistant.io/alerts.json",
        text=await async_load_fixture(menuai, "alerts_1.json", DOMAIN),
    )
    for alert in expected_alerts:
        stub_alert(aioclient_mock, alert[0])

    activated_components = (
        "aladdin_connect",
        "darksky",
        "hikvision",
        "hikvisioncam",
        "hive",
        "homematicip_cloud",
        "logi_circle",
        "neato",
        "nest",
        "senseme",
        "sochain",
    )
    for domain in activated_components:
        menuai.config.components.add(domain)

    if supervisor_info is not None:
        menuai.config.components.add("menuaiio")

    with (
        patch(
            "menuai.components.menuai_alerts.coordinator.__version__",
            ha_version,
        ),
        patch(
            "menuai.components.menuai_alerts.coordinator.is_menuaiio",
            return_value=supervisor_info is not None,
        ),
        patch(
            "menuai.components.menuai_alerts.coordinator.get_supervisor_info",
            return_value=supervisor_info,
        ),
    ):
        assert await async_setup_component(menuai, DOMAIN, {})

    client = await menuai_ws_client(menuai)

    await client.send_json({"id": 1, "type": "repairs/list_issues"})
    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"] == {
        "issues": [
            {
                "breaks_in_ha_version": None,
                "created": ANY,
                "dismissed_version": None,
                "domain": DOMAIN,
                "ignored": False,
                "is_fixable": False,
                "issue_id": f"{alert_id}.markdown_{integration}",
                "issue_domain": integration,
                "learn_more_url": None,
                "severity": "warning",
                "translation_key": "alert",
                "translation_placeholders": {
                    "title": f"Title for {alert_id}",
                    "description": f"Content for {alert_id}",
                },
            }
            for alert_id, integration in expected_alerts
        ]
    }


@pytest.mark.parametrize(
    (
        "ha_version",
        "supervisor_info",
        "initial_components",
        "late_components",
        "initial_alerts",
        "late_alerts",
    ),
    [
        (
            "2022.7.0",
            {"version": "2022.11.0"},
            ["aladdin_connect", "darksky"],
            [
                "menuaiio",
                "hikvision",
                "hikvisioncam",
                "hive",
                "homematicip_cloud",
                "logi_circle",
                "neato",
                "nest",
                "senseme",
                "sochain",
            ],
            [
                ("aladdin_connect", "aladdin_connect"),
                ("dark_sky", "darksky"),
            ],
            [
                ("aladdin_connect", "aladdin_connect"),
                ("dark_sky", "darksky"),
                ("menuaiio", "menuaiio"),
                ("hikvision", "hikvision"),
                ("hikvision", "hikvisioncam"),
                ("hive_us", "hive"),
                ("homematicip_cloud", "homematicip_cloud"),
                ("logi_circle", "logi_circle"),
                ("neato", "neato"),
                ("nest", "nest"),
                ("senseme", "senseme"),
                ("sochain", "sochain"),
            ],
        ),
        (
            "2022.8.0",
            {"version": "2022.11.1"},
            ["aladdin_connect", "darksky"],
            [
                "menuaiio",
                "hikvision",
                "hikvisioncam",
                "hive",
                "homematicip_cloud",
                "logi_circle",
                "neato",
                "nest",
                "senseme",
                "sochain",
            ],
            [
                ("dark_sky", "darksky"),
            ],
            [
                ("dark_sky", "darksky"),
                ("hikvision", "hikvision"),
                ("hikvision", "hikvisioncam"),
                ("hive_us", "hive"),
                ("homematicip_cloud", "homematicip_cloud"),
                ("logi_circle", "logi_circle"),
                ("neato", "neato"),
                ("nest", "nest"),
                ("senseme", "senseme"),
                ("sochain", "sochain"),
            ],
        ),
        (
            "2021.10.0",
            None,
            ["aladdin_connect", "darksky"],
            [
                "hikvision",
                "hikvisioncam",
                "hive",
                "homematicip_cloud",
                "logi_circle",
                "neato",
                "nest",
                "senseme",
                "sochain",
            ],
            [
                ("aladdin_connect", "aladdin_connect"),
                ("dark_sky", "darksky"),
            ],
            [
                ("aladdin_connect", "aladdin_connect"),
                ("dark_sky", "darksky"),
                ("hikvision", "hikvision"),
                ("hikvision", "hikvisioncam"),
                ("homematicip_cloud", "homematicip_cloud"),
                ("logi_circle", "logi_circle"),
                ("neato", "neato"),
                ("nest", "nest"),
                ("senseme", "senseme"),
                ("sochain", "sochain"),
            ],
        ),
    ],
)
async def test_alerts_refreshed_on_component_load(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    aioclient_mock: AiohttpClientMocker,
    ha_version: str,
    supervisor_info: dict[str, str] | None,
    initial_components: list[str],
    late_components: list[str],
    initial_alerts: list[tuple[str, str]],
    late_alerts: list[tuple[str, str]],
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test alerts are refreshed when components are loaded."""

    aioclient_mock.clear_requests()
    aioclient_mock.get(
        "https://alerts.home-assistant.io/alerts.json",
        text=await async_load_fixture(menuai, "alerts_1.json", DOMAIN),
    )
    for alert in initial_alerts:
        stub_alert(aioclient_mock, alert[0])
    for alert in late_alerts:
        stub_alert(aioclient_mock, alert[0])

    for domain in initial_components:
        menuai.config.components.add(domain)

    with (
        patch(
            "menuai.components.menuai_alerts.coordinator.__version__",
            ha_version,
        ),
        patch(
            "menuai.components.menuai_alerts.coordinator.is_menuaiio",
            return_value=supervisor_info is not None,
        ),
        patch(
            "menuai.components.menuai_alerts.coordinator.get_supervisor_info",
            return_value=supervisor_info,
        ),
    ):
        assert await async_setup_component(menuai, DOMAIN, {})

        client = await menuai_ws_client(menuai)

        await client.send_json({"id": 1, "type": "repairs/list_issues"})
        msg = await client.receive_json()
        assert msg["success"]
        assert msg["result"] == {
            "issues": [
                {
                    "breaks_in_ha_version": None,
                    "created": ANY,
                    "dismissed_version": None,
                    "domain": DOMAIN,
                    "ignored": False,
                    "is_fixable": False,
                    "issue_id": f"{alert}.markdown_{integration}",
                    "issue_domain": integration,
                    "learn_more_url": None,
                    "severity": "warning",
                    "translation_key": "alert",
                    "translation_placeholders": {
                        "title": f"Title for {alert}",
                        "description": f"Content for {alert}",
                    },
                }
                for alert, integration in initial_alerts
            ]
        }

    with (
        patch(
            "menuai.components.menuai_alerts.coordinator.__version__",
            ha_version,
        ),
        patch(
            "menuai.components.menuai_alerts.coordinator.is_menuaiio",
            return_value=supervisor_info is not None,
        ),
        patch(
            "menuai.components.menuai_alerts.coordinator.get_supervisor_info",
            return_value=supervisor_info,
        ),
    ):
        # Fake component_loaded events and wait for debounce
        for domain in late_components:
            menuai.config.components.add(domain)
            menuai.bus.async_fire(EVENT_COMPONENT_LOADED, {ATTR_COMPONENT: domain})
        freezer.tick(COMPONENT_LOADED_COOLDOWN + 1)
        await menuai.async_block_till_done()

        client = await menuai_ws_client(menuai)

        await client.send_json({"id": 2, "type": "repairs/list_issues"})
        msg = await client.receive_json()
        assert msg["success"]
        assert msg["result"] == {
            "issues": [
                {
                    "breaks_in_ha_version": None,
                    "created": ANY,
                    "dismissed_version": None,
                    "domain": DOMAIN,
                    "ignored": False,
                    "is_fixable": False,
                    "issue_id": f"{alert}.markdown_{integration}",
                    "issue_domain": integration,
                    "learn_more_url": None,
                    "severity": "warning",
                    "translation_key": "alert",
                    "translation_placeholders": {
                        "title": f"Title for {alert}",
                        "description": f"Content for {alert}",
                    },
                }
                for alert, integration in late_alerts
            ]
        }


@pytest.mark.parametrize(
    ("ha_version", "fixture", "expected_alerts"),
    [
        (
            "2022.7.0",
            "alerts_no_integrations.json",
            [
                ("dark_sky", "darksky"),
            ],
        ),
        (
            "2022.7.0",
            "alerts_no_package.json",
            [
                ("dark_sky", "darksky"),
                ("hikvision", "hikvision"),
            ],
        ),
    ],
)
async def test_bad_alerts(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    aioclient_mock: AiohttpClientMocker,
    ha_version: str,
    fixture: str,
    expected_alerts: list[tuple[str, str]],
) -> None:
    """Test creating issues based on alerts."""
    fixture_content = await async_load_fixture(menuai, fixture, DOMAIN)
    aioclient_mock.clear_requests()
    aioclient_mock.get(
        "https://alerts.home-assistant.io/alerts.json",
        text=fixture_content,
    )
    for alert in json.loads(fixture_content):
        stub_alert(aioclient_mock, alert["id"])

    activated_components = (
        "darksky",
        "hikvision",
        "hikvisioncam",
    )
    for domain in activated_components:
        menuai.config.components.add(domain)

    with patch(
        "menuai.components.menuai_alerts.coordinator.__version__",
        ha_version,
    ):
        assert await async_setup_component(menuai, DOMAIN, {})

    client = await menuai_ws_client(menuai)

    await client.send_json({"id": 1, "type": "repairs/list_issues"})
    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"] == {
        "issues": [
            {
                "breaks_in_ha_version": None,
                "created": ANY,
                "dismissed_version": None,
                "domain": DOMAIN,
                "ignored": False,
                "is_fixable": False,
                "issue_id": f"{alert_id}.markdown_{integration}",
                "issue_domain": integration,
                "learn_more_url": None,
                "severity": "warning",
                "translation_key": "alert",
                "translation_placeholders": {
                    "title": f"Title for {alert_id}",
                    "description": f"Content for {alert_id}",
                },
            }
            for alert_id, integration in expected_alerts
        ]
    }


async def test_no_alerts(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test creating issues based on alerts."""

    aioclient_mock.clear_requests()
    aioclient_mock.get(
        "https://alerts.home-assistant.io/alerts.json",
        text="",
    )

    assert await async_setup_component(menuai, DOMAIN, {})

    client = await menuai_ws_client(menuai)

    await client.send_json({"id": 1, "type": "repairs/list_issues"})
    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"] == {"issues": []}


@pytest.mark.parametrize(
    ("ha_version", "fixture_1", "expected_alerts_1", "fixture_2", "expected_alerts_2"),
    [
        (
            "2022.7.0",
            "alerts_1.json",
            [
                ("aladdin_connect", "aladdin_connect"),
                ("dark_sky", "darksky"),
                ("hikvision", "hikvision"),
                ("hikvision", "hikvisioncam"),
                ("hive_us", "hive"),
                ("homematicip_cloud", "homematicip_cloud"),
                ("logi_circle", "logi_circle"),
                ("neato", "neato"),
                ("nest", "nest"),
                ("senseme", "senseme"),
                ("sochain", "sochain"),
            ],
            "alerts_2.json",
            [
                ("dark_sky", "darksky"),
                ("hikvision", "hikvision"),
                ("hikvision", "hikvisioncam"),
                ("hive_us", "hive"),
                ("homematicip_cloud", "homematicip_cloud"),
                ("logi_circle", "logi_circle"),
                ("neato", "neato"),
                ("nest", "nest"),
                ("senseme", "senseme"),
                ("sochain", "sochain"),
            ],
        ),
        (
            "2022.7.0",
            "alerts_2.json",
            [
                ("dark_sky", "darksky"),
                ("hikvision", "hikvision"),
                ("hikvision", "hikvisioncam"),
                ("hive_us", "hive"),
                ("homematicip_cloud", "homematicip_cloud"),
                ("logi_circle", "logi_circle"),
                ("neato", "neato"),
                ("nest", "nest"),
                ("senseme", "senseme"),
                ("sochain", "sochain"),
            ],
            "alerts_1.json",
            [
                ("aladdin_connect", "aladdin_connect"),
                ("dark_sky", "darksky"),
                ("hikvision", "hikvision"),
                ("hikvision", "hikvisioncam"),
                ("hive_us", "hive"),
                ("homematicip_cloud", "homematicip_cloud"),
                ("logi_circle", "logi_circle"),
                ("neato", "neato"),
                ("nest", "nest"),
                ("senseme", "senseme"),
                ("sochain", "sochain"),
            ],
        ),
    ],
)
async def test_alerts_change(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    aioclient_mock: AiohttpClientMocker,
    ha_version: str,
    fixture_1: str,
    expected_alerts_1: list[tuple[str, str]],
    fixture_2: str,
    expected_alerts_2: list[tuple[str, str]],
) -> None:
    """Test creating issues based on alerts."""
    fixture_1_content = await async_load_fixture(menuai, fixture_1, DOMAIN)
    aioclient_mock.clear_requests()
    aioclient_mock.get(
        "https://alerts.home-assistant.io/alerts.json",
        text=fixture_1_content,
    )
    for alert in json.loads(fixture_1_content):
        stub_alert(aioclient_mock, alert["id"])

    activated_components = (
        "aladdin_connect",
        "darksky",
        "hikvision",
        "hikvisioncam",
        "hive",
        "homematicip_cloud",
        "logi_circle",
        "neato",
        "nest",
        "senseme",
        "sochain",
    )
    for domain in activated_components:
        menuai.config.components.add(domain)

    with patch(
        "menuai.components.menuai_alerts.coordinator.__version__",
        ha_version,
    ):
        assert await async_setup_component(menuai, DOMAIN, {})

    now = dt_util.utcnow()

    client = await menuai_ws_client(menuai)

    await client.send_json({"id": 1, "type": "repairs/list_issues"})
    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"]["issues"] == unordered(
        [
            {
                "breaks_in_ha_version": None,
                "created": ANY,
                "dismissed_version": None,
                "domain": DOMAIN,
                "ignored": False,
                "is_fixable": False,
                "issue_id": f"{alert_id}.markdown_{integration}",
                "issue_domain": integration,
                "learn_more_url": None,
                "severity": "warning",
                "translation_key": "alert",
                "translation_placeholders": {
                    "title": f"Title for {alert_id}",
                    "description": f"Content for {alert_id}",
                },
            }
            for alert_id, integration in expected_alerts_1
        ]
    )

    fixture_2_content = await async_load_fixture(menuai, fixture_2, DOMAIN)
    aioclient_mock.clear_requests()
    aioclient_mock.get(
        "https://alerts.home-assistant.io/alerts.json",
        text=fixture_2_content,
    )
    for alert in json.loads(fixture_2_content):
        stub_alert(aioclient_mock, alert["id"])

    future = now + UPDATE_INTERVAL + timedelta(seconds=1)
    async_fire_time_changed(menuai, future)
    await menuai.async_block_till_done()

    await client.send_json({"id": 2, "type": "repairs/list_issues"})
    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"]["issues"] == unordered(
        [
            {
                "breaks_in_ha_version": None,
                "created": ANY,
                "dismissed_version": None,
                "domain": DOMAIN,
                "ignored": False,
                "is_fixable": False,
                "issue_id": f"{alert_id}.markdown_{integration}",
                "issue_domain": integration,
                "learn_more_url": None,
                "severity": "warning",
                "translation_key": "alert",
                "translation_placeholders": {
                    "title": f"Title for {alert_id}",
                    "description": f"Content for {alert_id}",
                },
            }
            for alert_id, integration in expected_alerts_2
        ]
    )
