"""Provide helper functions for the TTS."""

from __future__ import annotations

from typing import TYPE_CHECKING

from menuai.core import menuai

from .const import DATA_COMPONENT, DATA_TTS_MANAGER

if TYPE_CHECKING:
    from . import TextToSpeechEntity
    from .legacy import Provider


def get_engine_instance(
    menuai: menuai, engine: str
) -> TextToSpeechEntity | Provider | None:
    """Get engine instance."""
    if entity := menuai.data[DATA_COMPONENT].get_entity(engine):
        return entity

    return menuai.data[DATA_TTS_MANAGER].providers.get(engine)
