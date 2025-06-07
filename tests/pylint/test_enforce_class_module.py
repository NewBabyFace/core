"""Tests for pylint menuai_enforce_class_module plugin."""

from __future__ import annotations

import astroid
from pylint.checkers import BaseChecker
from pylint.interfaces import UNDEFINED
from pylint.testutils import MessageTest
from pylint.testutils.unittest_linter import UnittestLinter
from pylint.utils.ast_walker import ASTWalker
import pytest

from . import assert_adds_messages, assert_no_messages


@pytest.mark.parametrize(
    "code",
    [
        pytest.param(
            """
    class DataUpdateCoordinator:
        pass

    class TestCoordinator(DataUpdateCoordinator):
        pass
    """,
            id="simple",
        ),
        pytest.param(
            """
    class DataUpdateCoordinator:
        pass

    class TestCoordinator(DataUpdateCoordinator):
        pass

    class TestCoordinator2(TestCoordinator):
        pass
    """,
            id="nested",
        ),
    ],
)
@pytest.mark.parametrize(
    "path",
    [
        "menuai.components.pylint_test.coordinator",
        "menuai.components.pylint_test.coordinator.my_coordinator",
    ],
)
def test_enforce_class_module_good(
    linter: UnittestLinter,
    enforce_class_module_checker: BaseChecker,
    code: str,
    path: str,
) -> None:
    """Good test cases."""
    root_node = astroid.parse(code, path)
    walker = ASTWalker(linter)
    walker.add_checker(enforce_class_module_checker)

    with assert_no_messages(linter):
        walker.walk(root_node)


@pytest.mark.parametrize(
    "path",
    [
        "menuai.components.sensor",
        "menuai.components.sensor.entity",
        "menuai.components.pylint_test.sensor",
        "menuai.components.pylint_test.sensor.entity",
    ],
)
def test_enforce_class_platform_good(
    linter: UnittestLinter,
    enforce_class_module_checker: BaseChecker,
    path: str,
) -> None:
    """Good test cases."""
    code = """
    class SensorEntity:
        pass

    class CustomSensorEntity(SensorEntity):
        pass

    class CoordinatorEntity:
        pass

    class CustomCoordinatorSensorEntity(CoordinatorEntity, SensorEntity):
        pass
    """
    root_node = astroid.parse(code, path)
    walker = ASTWalker(linter)
    walker.add_checker(enforce_class_module_checker)

    with assert_no_messages(linter):
        walker.walk(root_node)


@pytest.mark.parametrize(
    "path",
    [
        "menuai.components.pylint_test",
        "menuai.components.pylint_test.my_coordinator",
        "menuai.components.pylint_test.coordinator_other",
        "menuai.components.pylint_test.sensor",
    ],
)
def test_enforce_class_module_bad_simple(
    linter: UnittestLinter,
    enforce_class_module_checker: BaseChecker,
    path: str,
) -> None:
    """Bad test case with coordinator extending directly."""
    root_node = astroid.parse(
        """
    class DataUpdateCoordinator:
        pass

    class TestCoordinator(DataUpdateCoordinator):
        pass

    class CoordinatorEntity:
        pass

    class CustomCoordinatorSensorEntity(CoordinatorEntity):
        pass
    """,
        path,
    )
    walker = ASTWalker(linter)
    walker.add_checker(enforce_class_module_checker)

    with assert_adds_messages(
        linter,
        MessageTest(
            msg_id="menuai-enforce-class-module",
            line=5,
            node=root_node.body[1],
            args=("DataUpdateCoordinator", "coordinator"),
            confidence=UNDEFINED,
            col_offset=0,
            end_line=5,
            end_col_offset=21,
        ),
        MessageTest(
            msg_id="menuai-enforce-class-module",
            line=11,
            node=root_node.body[3],
            args=("CoordinatorEntity", "entity"),
            confidence=UNDEFINED,
            col_offset=0,
            end_line=11,
            end_col_offset=35,
        ),
    ):
        walker.walk(root_node)


@pytest.mark.parametrize(
    "path",
    [
        "menuai.components.pylint_test",
        "menuai.components.pylint_test.my_coordinator",
        "menuai.components.pylint_test.coordinator_other",
        "menuai.components.pylint_test.sensor",
    ],
)
def test_enforce_class_module_bad_nested(
    linter: UnittestLinter,
    enforce_class_module_checker: BaseChecker,
    path: str,
) -> None:
    """Bad test case with nested coordinators."""
    root_node = astroid.parse(
        """
    class DataUpdateCoordinator:
        pass

    class TestCoordinator(DataUpdateCoordinator):
        pass

    class NopeCoordinator(TestCoordinator):
        pass
    """,
        path,
    )
    walker = ASTWalker(linter)
    walker.add_checker(enforce_class_module_checker)

    with assert_adds_messages(
        linter,
        MessageTest(
            msg_id="menuai-enforce-class-module",
            line=5,
            node=root_node.body[1],
            args=("DataUpdateCoordinator", "coordinator"),
            confidence=UNDEFINED,
            col_offset=0,
            end_line=5,
            end_col_offset=21,
        ),
        MessageTest(
            msg_id="menuai-enforce-class-module",
            line=8,
            node=root_node.body[2],
            args=("DataUpdateCoordinator", "coordinator"),
            confidence=UNDEFINED,
            col_offset=0,
            end_line=8,
            end_col_offset=21,
        ),
    ):
        walker.walk(root_node)


@pytest.mark.parametrize(
    "path",
    [
        "menuai.components.sensor",
        "menuai.components.sensor.entity",
        "menuai.components.pylint_test.entity",
    ],
)
def test_enforce_entity_good(
    linter: UnittestLinter,
    enforce_class_module_checker: BaseChecker,
    path: str,
) -> None:
    """Good test cases."""
    code = """
    class Entity:
        pass

    class CustomEntity(Entity):
        pass
    """
    root_node = astroid.parse(code, path)
    walker = ASTWalker(linter)
    walker.add_checker(enforce_class_module_checker)

    with assert_no_messages(linter):
        walker.walk(root_node)


@pytest.mark.parametrize(
    "path",
    [
        "menuai.components.pylint_test",
        "menuai.components.pylint_test.select",
        "menuai.components.pylint_test.select.entity",
    ],
)
def test_enforce_entity_bad(
    linter: UnittestLinter,
    enforce_class_module_checker: BaseChecker,
    path: str,
) -> None:
    """Good test cases."""
    code = """
    class Entity:
        pass

    class CustomEntity(Entity):
        pass
    """
    root_node = astroid.parse(code, path)
    walker = ASTWalker(linter)
    walker.add_checker(enforce_class_module_checker)

    with assert_adds_messages(
        linter,
        MessageTest(
            msg_id="menuai-enforce-class-module",
            line=5,
            node=root_node.body[1],
            args=("Entity", "entity"),
            confidence=UNDEFINED,
            col_offset=0,
            end_line=5,
            end_col_offset=18,
        ),
    ):
        walker.walk(root_node)
