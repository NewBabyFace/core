"""Configuration for pylint tests."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from types import ModuleType

from pylint.checkers import BaseChecker
from pylint.testutils.unittest_linter import UnittestLinter
import pytest

BASE_PATH = Path(__file__).parents[2]


def _load_plugin_from_file(module_name: str, file: str) -> ModuleType:
    """Load plugin from file path."""
    spec = spec_from_file_location(
        module_name,
        str(BASE_PATH.joinpath(file)),
    )
    assert spec and spec.loader

    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(name="menuai_enforce_type_hints", scope="package")
def menuai_enforce_type_hints_fixture() -> ModuleType:
    """Fixture to provide a requests mocker."""
    return _load_plugin_from_file(
        "menuai_enforce_type_hints",
        "pylint/plugins/menuai_enforce_type_hints.py",
    )


@pytest.fixture(name="linter")
def linter_fixture() -> UnittestLinter:
    """Fixture to provide a requests mocker."""
    return UnittestLinter()


@pytest.fixture(name="type_hint_checker")
def type_hint_checker_fixture(menuai_enforce_type_hints, linter) -> BaseChecker:
    """Fixture to provide a requests mocker."""
    type_hint_checker = menuai_enforce_type_hints.menuaiTypeHintChecker(linter)
    type_hint_checker.module = "menuai.components.pylint_test"
    return type_hint_checker


@pytest.fixture(name="menuai_imports", scope="package")
def menuai_imports_fixture() -> ModuleType:
    """Fixture to provide a requests mocker."""
    return _load_plugin_from_file(
        "menuai_imports",
        "pylint/plugins/menuai_imports.py",
    )


@pytest.fixture(name="imports_checker")
def imports_checker_fixture(menuai_imports, linter) -> BaseChecker:
    """Fixture to provide a requests mocker."""
    type_hint_checker = menuai_imports.menuaiImportsFormatChecker(linter)
    type_hint_checker.module = "menuai.components.pylint_test"
    return type_hint_checker


@pytest.fixture(name="menuai_enforce_super_call", scope="package")
def menuai_enforce_super_call_fixture() -> ModuleType:
    """Fixture to provide a requests mocker."""
    return _load_plugin_from_file(
        "menuai_enforce_super_call",
        "pylint/plugins/menuai_enforce_super_call.py",
    )


@pytest.fixture(name="super_call_checker")
def super_call_checker_fixture(menuai_enforce_super_call, linter) -> BaseChecker:
    """Fixture to provide a requests mocker."""
    super_call_checker = menuai_enforce_super_call.menuaiEnforceSuperCallChecker(linter)
    super_call_checker.module = "menuai.components.pylint_test"
    return super_call_checker


@pytest.fixture(name="menuai_enforce_sorted_platforms", scope="package")
def menuai_enforce_sorted_platforms_fixture() -> ModuleType:
    """Fixture to the content for the menuai_enforce_sorted_platforms check."""
    return _load_plugin_from_file(
        "menuai_enforce_sorted_platforms",
        "pylint/plugins/menuai_enforce_sorted_platforms.py",
    )


@pytest.fixture(name="enforce_sorted_platforms_checker")
def enforce_sorted_platforms_checker_fixture(
    menuai_enforce_sorted_platforms, linter
) -> BaseChecker:
    """Fixture to provide a menuai_enforce_sorted_platforms checker."""
    enforce_sorted_platforms_checker = (
        menuai_enforce_sorted_platforms.menuaiEnforceSortedPlatformsChecker(linter)
    )
    enforce_sorted_platforms_checker.module = "menuai.components.pylint_test"
    return enforce_sorted_platforms_checker


@pytest.fixture(name="menuai_enforce_class_module", scope="package")
def menuai_enforce_class_module_fixture() -> ModuleType:
    """Fixture to the content for the menuai_enforce_class_module check."""
    return _load_plugin_from_file(
        "menuai_enforce_class_module",
        "pylint/plugins/menuai_enforce_class_module.py",
    )


@pytest.fixture(name="enforce_class_module_checker")
def enforce_class_module_fixture(menuai_enforce_class_module, linter) -> BaseChecker:
    """Fixture to provide a menuai_enforce_class_module checker."""
    enforce_class_module_checker = menuai_enforce_class_module.menuaiEnforceClassModule(
        linter
    )
    enforce_class_module_checker.module = "menuai.components.pylint_test"
    return enforce_class_module_checker


@pytest.fixture(name="menuai_decorator", scope="package")
def menuai_decorator_fixture() -> ModuleType:
    """Fixture to provide a pylint plugin."""
    return _load_plugin_from_file(
        "menuai_imports",
        "pylint/plugins/menuai_decorator.py",
    )


@pytest.fixture(name="decorator_checker")
def decorator_checker_fixture(menuai_decorator, linter) -> BaseChecker:
    """Fixture to provide a pylint checker."""
    type_hint_checker = menuai_decorator.menuaiDecoratorChecker(linter)
    type_hint_checker.module = "menuai.components.pylint_test"
    return type_hint_checker
