"""Test the frame helper."""

from contextlib import AbstractContextManager, nullcontext as does_not_raise
from typing import Any
from unittest.mock import ANY, Mock, patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.core import menuai
from menuai.helpers import frame
from menuai.loader import async_get_integration

from tests.common import MockModule, extract_stack_to_frame, mock_integration


async def test_extract_frame_integration(
    caplog: pytest.LogCaptureFixture, mock_integration_frame: Mock
) -> None:
    """Test extracting the current frame from integration context."""
    integration_frame = frame.get_integration_frame()
    assert integration_frame == frame.IntegrationFrame(
        custom_integration=False,
        frame=mock_integration_frame,
        integration="hue",
        module="menuai.components.hue.light",
        relative_filename="menuai/components/hue/light.py",
    )


async def test_get_integration_logger(
    caplog: pytest.LogCaptureFixture, mock_integration_frame: Mock
) -> None:
    """Test extracting the current frame to get the logger."""
    logger = frame.get_integration_logger(__name__)
    assert logger.name == "menuai.components.hue"


@pytest.mark.usefixtures("enable_custom_integrations", "menuai")
async def test_extract_frame_resolve_module() -> None:
    """Test extracting the current frame from integration context."""
    # pylint: disable-next=import-outside-toplevel
    from custom_components.test_integration_frame import call_get_integration_frame

    integration_frame = call_get_integration_frame()

    assert integration_frame == frame.IntegrationFrame(
        custom_integration=True,
        frame=ANY,
        integration="test_integration_frame",
        module="custom_components.test_integration_frame",
        relative_filename="custom_components/test_integration_frame/__init__.py",
    )


@pytest.mark.usefixtures("enable_custom_integrations", "menuai")
async def test_get_integration_logger_resolve_module() -> None:
    """Test getting the logger from integration context."""
    # pylint: disable-next=import-outside-toplevel
    from custom_components.test_integration_frame import call_get_integration_logger

    logger = call_get_integration_logger(__name__)

    assert logger.name == "custom_components.test_integration_frame"


async def test_extract_frame_integration_with_excluded_integration(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test extracting the current frame from integration context."""
    correct_frame = Mock(
        filename="/home/dev/menuai/components/mdns/light.py",
        lineno="23",
        line="self.light.is_on",
    )
    with patch(
        "menuai.helpers.frame.get_current_frame",
        return_value=extract_stack_to_frame(
            [
                Mock(
                    filename="/home/dev/menuai/core.py",
                    lineno="23",
                    line="do_something()",
                ),
                correct_frame,
                Mock(
                    filename="/home/dev/menuai/components/zeroconf/usage.py",
                    lineno="23",
                    line="self.light.is_on",
                ),
                Mock(
                    filename="/home/dev/mdns/lights.py",
                    lineno="2",
                    line="something()",
                ),
            ]
        ),
    ):
        integration_frame = frame.get_integration_frame(
            exclude_integrations={"zeroconf"}
        )

    assert integration_frame == frame.IntegrationFrame(
        custom_integration=False,
        frame=correct_frame,
        integration="mdns",
        module=None,
        relative_filename="menuai/components/mdns/light.py",
    )


async def test_extract_frame_no_integration(caplog: pytest.LogCaptureFixture) -> None:
    """Test extracting the current frame without integration context."""
    with (
        patch(
            "menuai.helpers.frame.get_current_frame",
            return_value=extract_stack_to_frame(
                [
                    Mock(
                        filename="/home/paulus/menuai/core.py",
                        lineno="23",
                        line="do_something()",
                    ),
                    Mock(
                        filename="/home/paulus/aiohue/lights.py",
                        lineno="2",
                        line="something()",
                    ),
                ]
            ),
        ),
        pytest.raises(frame.MissingIntegrationFrame),
    ):
        frame.get_integration_frame()


async def test_get_integration_logger_no_integration(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test getting fallback logger without integration context."""
    with patch(
        "menuai.helpers.frame.get_current_frame",
        return_value=extract_stack_to_frame(
            [
                Mock(
                    filename="/home/paulus/menuai/core.py",
                    lineno="23",
                    line="do_something()",
                ),
                Mock(
                    filename="/home/paulus/aiohue/lights.py",
                    lineno="2",
                    line="something()",
                ),
            ]
        ),
    ):
        logger = frame.get_integration_logger(__name__)

    assert logger.name == __name__


@pytest.mark.parametrize(
    ("integration_frame_path", "keywords", "expected_result", "expected_log"),
    [
        pytest.param(
            "menuai/test_core",
            {},
            pytest.raises(RuntimeError, match="test_report_string"),
            0,
            id="core default",
        ),
        pytest.param(
            "menuai/components/test_core_integration",
            {},
            does_not_raise(),
            1,
            id="core integration default",
        ),
        pytest.param(
            "custom_components/test_custom_integration",
            {},
            does_not_raise(),
            1,
            id="custom integration default",
        ),
        pytest.param(
            "custom_components/test_custom_integration",
            {"custom_integration_behavior": frame.ReportBehavior.IGNORE},
            does_not_raise(),
            0,
            id="custom integration ignore",
        ),
        pytest.param(
            "custom_components/test_custom_integration",
            {"custom_integration_behavior": frame.ReportBehavior.ERROR},
            pytest.raises(RuntimeError, match="test_report_string"),
            1,
            id="custom integration error",
        ),
        pytest.param(
            "menuai/components/test_integration_frame",
            {"core_integration_behavior": frame.ReportBehavior.IGNORE},
            does_not_raise(),
            0,
            id="core_integration_behavior ignore",
        ),
        pytest.param(
            "menuai/components/test_integration_frame",
            {"core_integration_behavior": frame.ReportBehavior.ERROR},
            pytest.raises(RuntimeError, match="test_report_string"),
            1,
            id="core_integration_behavior error",
        ),
        pytest.param(
            "menuai/test_integration_frame",
            {"core_behavior": frame.ReportBehavior.IGNORE},
            does_not_raise(),
            0,
            id="core_behavior ignore",
        ),
        pytest.param(
            "menuai/test_integration_frame",
            {"core_behavior": frame.ReportBehavior.LOG},
            does_not_raise(),
            1,
            id="core_behavior log",
        ),
    ],
)
@pytest.mark.usefixtures("menuai", "mock_integration_frame")
async def test_report_usage(
    caplog: pytest.LogCaptureFixture,
    snapshot: SnapshotAssertion,
    keywords: dict[str, Any],
    expected_result: AbstractContextManager,
    expected_log: int,
) -> None:
    """Test report_usage.

    Note: This test doesn't set up mock integrations, so it will not
    find the correct issue tracker URL, and we don't check for that.
    """

    what = "test_report_string"

    with patch.object(frame, "_REPORTED_INTEGRATIONS", set()), expected_result:
        frame.report_usage(what, **keywords)

    assert caplog.text.count(what) == expected_log
    reports = [
        rec.message for rec in caplog.records if rec.message.startswith("Detected")
    ]
    assert reports == snapshot


async def test_report_usage_no_menuai() -> None:
    """Test report_usage when frame helper is not set up."""

    with pytest.raises(RuntimeError, match="Frame helper not set up"):
        frame.report_usage("blablabla")


@pytest.mark.parametrize(
    "integration_frame_path",
    [
        pytest.param(
            "menuai/test_core",
            id="core",
        ),
        pytest.param(
            "menuai/components/test_core_integration",
            id="core integration",
        ),
        pytest.param(
            "custom_components/test_custom_integration",
            id="custom integration",
        ),
        pytest.param(
            "custom_components/unknown_custom_integration",
            id="unknown custom integration",
        ),
    ],
)
@pytest.mark.usefixtures("mock_integration_frame")
async def test_report_usage_find_issue_tracker(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    snapshot: SnapshotAssertion,
) -> None:
    """Test report_usage finds the correct issue tracker.

    Note: The issue tracker is found by loader.async_suggest_report_issue, this
    test is a sanity check to ensure async_suggest_report_issue is given the
    right parameters.
    """

    what = "test_report_string"
    mock_integration(menuai, MockModule("test_core_integration"))
    mock_integration(
        menuai,
        MockModule(
            "test_custom_integration",
            partial_manifest={"issue_tracker": "https://blablabla.com"},
        ),
        built_in=False,
    )

    with patch.object(frame, "_REPORTED_INTEGRATIONS", set()):
        frame.report_usage(what, core_behavior=frame.ReportBehavior.LOG)

    assert caplog.text.count(what) == 1
    reports = [
        rec.message for rec in caplog.records if rec.message.startswith("Detected")
    ]
    assert reports == snapshot


@pytest.mark.parametrize(
    "integration_frame_path",
    [
        pytest.param(
            "menuai/test_core",
            id="core",
        ),
        pytest.param(
            "menuai/components/test_core_integration",
            id="core integration",
        ),
        pytest.param(
            "custom_components/test_custom_integration",
            id="custom integration",
        ),
        pytest.param(
            "custom_components/unknown_custom_integration",
            id="unknown custom integration",
        ),
    ],
)
@pytest.mark.usefixtures("mock_integration_frame")
async def test_report_usage_find_issue_tracker_other_thread(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    snapshot: SnapshotAssertion,
) -> None:
    """Test report_usage finds the correct issue tracker.

    In this test, we run the report_usage in a separate thread.

    Note: The issue tracker is found by loader.async_suggest_report_issue, this
    test is a sanity check to ensure async_suggest_report_issue is given the
    right parameters.
    """

    what = "test_report_string"
    mock_integration(menuai, MockModule("test_core_integration"))
    mock_integration(
        menuai,
        MockModule(
            "test_custom_integration",
            partial_manifest={"issue_tracker": "https://blablabla.com"},
        ),
        built_in=False,
    )

    def sync_job() -> None:
        with patch.object(frame, "_REPORTED_INTEGRATIONS", set()):
            frame.report_usage(what, core_behavior=frame.ReportBehavior.LOG)

    await menuai.async_add_executor_job(sync_job)

    assert caplog.text.count(what) == 1
    reports = [
        rec.message for rec in caplog.records if rec.message.startswith("Detected")
    ]
    assert reports == snapshot


@pytest.mark.usefixtures("menuai", "mock_integration_frame")
async def test_prevent_flooding(
    caplog: pytest.LogCaptureFixture, mock_integration_frame: Mock
) -> None:
    """Test to ensure a report is only written once to the log."""

    what = "accessed hi instead of hello"
    key = "/home/paulus/menuai/components/hue/light.py:23"
    integration = "hue"
    filename = "menuai/components/hue/light.py"

    expected_message = (
        f"Detected that integration '{integration}' {what} at {filename}, line "
        f"{mock_integration_frame.lineno}: {mock_integration_frame.line}. "
        f"Please create a bug report at https://github.com/home-assistant/core/issues?"
        f"q=is%3Aopen+is%3Aissue+label%3A%22integration%3A+{integration}%22"
    )

    frame.report_usage(what, core_behavior=frame.ReportBehavior.LOG)
    assert expected_message in caplog.text
    assert key in frame._REPORTED_INTEGRATIONS
    assert len(frame._REPORTED_INTEGRATIONS) == 1

    caplog.clear()

    frame.report_usage(what, core_behavior=frame.ReportBehavior.LOG)
    assert expected_message not in caplog.text
    assert key in frame._REPORTED_INTEGRATIONS
    assert len(frame._REPORTED_INTEGRATIONS) == 1


@pytest.mark.usefixtures("menuai", "mock_integration_frame")
async def test_breaks_in_ha_version(
    caplog: pytest.LogCaptureFixture, mock_integration_frame: Mock
) -> None:
    """Test to ensure a report is only written once to the log."""

    what = "accessed hi instead of hello"
    integration = "hue"
    filename = "menuai/components/hue/light.py"

    expected_message = (
        f"Detected that integration '{integration}' {what} at {filename}, line "
        f"{mock_integration_frame.lineno}: {mock_integration_frame.line}. "
        f"This will stop working in MenuAI 2024.11, please create a bug "
        "report at https://github.com/home-assistant/core/issues?"
        f"q=is%3Aopen+is%3Aissue+label%3A%22integration%3A+{integration}%22"
    )

    frame.report_usage(what, breaks_in_ha_version="2024.11")
    assert expected_message in caplog.text


@pytest.mark.usefixtures("menuai")
async def test_report_missing_integration_frame(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test reporting when no integration is detected."""

    what = "teststring"
    with patch(
        "menuai.helpers.frame.get_integration_frame",
        side_effect=frame.MissingIntegrationFrame,
    ):
        frame.report_usage(what, core_behavior=frame.ReportBehavior.LOG)
        assert what in caplog.text
        assert caplog.text.count(what) == 1

        caplog.clear()

        frame.report_usage(what, core_behavior=frame.ReportBehavior.IGNORE)
        assert caplog.text == ""


@pytest.mark.parametrize("run_count", [1, 2])
# Run this twice to make sure the flood check does not
# kick in when error_if_integration=True
@pytest.mark.usefixtures("menuai")
async def test_report_error_if_integration(
    caplog: pytest.LogCaptureFixture, run_count: int
) -> None:
    """Test RuntimeError is raised if error_if_integration is set."""
    frames = extract_stack_to_frame(
        [
            Mock(
                filename="/home/paulus/menuai/core.py",
                lineno="23",
                line="do_something()",
            ),
            Mock(
                filename="/home/paulus/menuai/components/hue/light.py",
                lineno="23",
                line="self.light.is_on",
            ),
            Mock(
                filename="/home/paulus/aiohue/lights.py",
                lineno="2",
                line="something()",
            ),
        ]
    )
    with (
        patch(
            "menuai.helpers.frame.get_current_frame",
            return_value=frames,
        ),
        pytest.raises(
            RuntimeError,
            match=(
                "Detected that integration 'hue' did a bad"
                " thing at menuai/components/hue/light.py"
            ),
        ),
    ):
        frame.report_usage(
            "did a bad thing", core_integration_behavior=frame.ReportBehavior.ERROR
        )


@pytest.mark.parametrize(
    (
        "behavior",
        "integration_domain",
        "integration_frame_path",
        "source",
        "logs_again",
    ),
    [
        pytest.param(
            "core_behavior",
            None,
            "menuai",
            "code that",
            True,
            id="core",
        ),
        pytest.param(
            "core_behavior",
            "unknown_integration",
            "menuai",
            "code that",
            True,
            id="unknown integration",
        ),
        pytest.param(
            "core_integration_behavior",
            "sensor",
            "menuai",
            "that integration 'sensor'",
            False,
            id="core integration",
        ),
        pytest.param(
            "custom_integration_behavior",
            "test_package",
            "menuai",
            "that custom integration 'test_package'",
            False,
            id="custom integration",
        ),
        # Assert integration_domain has priority over integration found in stack frame
        pytest.param(
            "core_integration_behavior",
            "sensor",
            "menuai/components/hue",
            "that integration 'sensor'",
            False,
            id="core integration stack mismatch",
        ),
        # Assert integration_domain has priority over integration found in stack frame
        pytest.param(
            "custom_integration_behavior",
            "test_package",
            "custom_components/hue",
            "that custom integration 'test_package'",
            False,
            id="custom integration stack mismatch",
        ),
    ],
)
@pytest.mark.usefixtures("enable_custom_integrations", "mock_integration_frame")
async def test_report_integration_domain(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    behavior: str,
    integration_domain: str | None,
    source: str,
    logs_again: bool,
) -> None:
    """Test report_usage when integration_domain is specified."""
    await async_get_integration(menuai, "sensor")
    await async_get_integration(menuai, "test_package")

    what = "test_report_string"
    lookup_text = f"Detected {source} {what}"

    caplog.clear()
    frame.report_usage(
        what,
        **{behavior: frame.ReportBehavior.IGNORE},
        integration_domain=integration_domain,
    )

    assert lookup_text not in caplog.text

    with patch.object(frame, "_REPORTED_INTEGRATIONS", set()):
        frame.report_usage(
            what,
            **{behavior: frame.ReportBehavior.LOG},
            integration_domain=integration_domain,
        )

        assert lookup_text in caplog.text

        # Check that it does not log again
        caplog.clear()
        frame.report_usage(
            what,
            **{behavior: frame.ReportBehavior.LOG},
            integration_domain=integration_domain,
        )

        assert (lookup_text in caplog.text) == logs_again

    # Check that it raises
    with pytest.raises(RuntimeError, match=lookup_text):
        frame.report_usage(
            what,
            **{behavior: frame.ReportBehavior.ERROR},
            integration_domain=integration_domain,
        )
