"""Tests for the Ollama integration."""

from menuai.components import ollama
from menuai.helpers import llm

TEST_USER_DATA = {
    ollama.CONF_URL: "http://localhost:11434",
    ollama.CONF_MODEL: "test model",
}

TEST_OPTIONS = {
    ollama.CONF_PROMPT: llm.DEFAULT_INSTRUCTIONS_PROMPT,
    ollama.CONF_MAX_HISTORY: 2,
}
