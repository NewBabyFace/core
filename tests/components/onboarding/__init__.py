"""Tests for the onboarding component."""

from menuai.components import onboarding


def mock_storage(menuai_storage, data):
    """Mock the onboarding storage."""
    menuai_storage[onboarding.STORAGE_KEY] = {
        "version": onboarding.STORAGE_VERSION,
        "data": data,
    }
