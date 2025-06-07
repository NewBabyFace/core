"""Tests for the Schlage integration."""

from menuai.components.schlage.coordinator import SchlageDataUpdateCoordinator

from tests.common import MockConfigEntry

type MockSchlageConfigEntry = MockConfigEntry[SchlageDataUpdateCoordinator]
