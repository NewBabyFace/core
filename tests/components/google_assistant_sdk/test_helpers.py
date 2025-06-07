"""Test the Google Assistant SDK helpers."""

from menuai.components.google_assistant_sdk.const import SUPPORTED_LANGUAGE_CODES
from menuai.components.google_assistant_sdk.helpers import (
    DEFAULT_LANGUAGE_CODES,
    best_matching_language_code,
    default_language_code,
)
from menuai.core import menuai


def test_default_language_codes(menuai: menuai) -> None:
    """Test all supported languages have a default language_code."""
    for language_code in SUPPORTED_LANGUAGE_CODES:
        lang = language_code.split("-", maxsplit=1)[0]
        assert DEFAULT_LANGUAGE_CODES.get(lang)


def test_default_language_code(menuai: menuai) -> None:
    """Test default_language_code."""
    assert default_language_code(menuai) == "en-US"

    menuai.config.language = "en"
    menuai.config.country = "US"
    assert default_language_code(menuai) == "en-US"

    menuai.config.language = "en"
    menuai.config.country = "GB"
    assert default_language_code(menuai) == "en-GB"

    menuai.config.language = "en"
    menuai.config.country = "ES"
    assert default_language_code(menuai) == "en-US"

    menuai.config.language = "es"
    menuai.config.country = "ES"
    assert default_language_code(menuai) == "es-ES"

    menuai.config.language = "es"
    menuai.config.country = "MX"
    assert default_language_code(menuai) == "es-MX"

    menuai.config.language = "es"
    menuai.config.country = None
    assert default_language_code(menuai) == "es-ES"

    menuai.config.language = "el"
    menuai.config.country = "GR"
    assert default_language_code(menuai) == "en-US"


def test_best_matching_language_code(menuai: menuai) -> None:
    """Test best_matching_language_code."""
    menuai.config.language = "es"
    menuai.config.country = "MX"

    # Assist Language is supported
    assert best_matching_language_code(menuai, "de-DE", "en-AU") == "de-DE"
    assert best_matching_language_code(menuai, "de-DE") == "de-DE"

    # Assist Language is not supported, but agent language has the same "lang" part, and is supported
    assert best_matching_language_code(menuai, "en", "en-AU") == "en-AU"
    assert best_matching_language_code(menuai, "en-XYZ", "en-AU") == "en-AU"
    # Assist Language is not supported, but agent language has the same "lang" part, but is not supported
    assert best_matching_language_code(menuai, "en", "en-XYZ") == "en-US"
    assert best_matching_language_code(menuai, "en-XYZ", "en-ABC") == "en-US"

    # Assist Language is not supported, agent is not matching or available, falling back to the default of assist lang
    assert best_matching_language_code(menuai, "de", "en-AU") == "de-DE"
    assert best_matching_language_code(menuai, "de-XYZ", "en-AU") == "de-DE"
    assert best_matching_language_code(menuai, "de") == "de-DE"
    assert best_matching_language_code(menuai, "de-XYZ") == "de-DE"

    # Assist language is not existing at all, agent is supported
    assert best_matching_language_code(menuai, "abc-XYZ", "en-AU") == "en-AU"

    # Assist language is not existing at all, agent is not supported, falling back to the agent default
    assert best_matching_language_code(menuai, "abc-XYZ", "de-XYZ") == "de-DE"

    # Assist language is not existing at all, agent is not existing or available, falling back to system default
    assert best_matching_language_code(menuai, "abc-XYZ", "def-XYZ") == "es-MX"
    assert best_matching_language_code(menuai, "abc-XYZ") == "es-MX"

    # Assist language is not existing at all, agent is not existing or available, system default is not supported
    menuai.config.language = "el"
    menuai.config.country = "GR"
    assert best_matching_language_code(menuai, "abc-XYZ", "def-XYZ") == "en-US"
    assert best_matching_language_code(menuai, "abc-XYZ") == "en-US"
