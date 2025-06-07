"""Const for conversation integration."""

from __future__ import annotations

from enum import IntFlag
from typing import TYPE_CHECKING

from menuai.util.menuai_dict import menuaiKey

if TYPE_CHECKING:
    from menuai.helpers.entity_component import EntityComponent

    from .default_agent import DefaultAgent
    from .entity import ConversationEntity

DOMAIN = "conversation"
DEFAULT_EXPOSED_ATTRIBUTES = {"device_class"}
HOME_ASSISTANT_AGENT = "conversation.home_assistant"
OLD_HOME_ASSISTANT_AGENT = "menuai"

ATTR_TEXT = "text"
ATTR_LANGUAGE = "language"
ATTR_AGENT_ID = "agent_id"
ATTR_CONVERSATION_ID = "conversation_id"

SERVICE_PROCESS = "process"
SERVICE_RELOAD = "reload"

DATA_COMPONENT: menuaiKey[EntityComponent[ConversationEntity]] = menuaiKey(DOMAIN)
DATA_DEFAULT_ENTITY: menuaiKey[DefaultAgent] = menuaiKey(f"{DOMAIN}_default_entity")


class ConversationEntityFeature(IntFlag):
    """Supported features of the conversation entity."""

    CONTROL = 1
