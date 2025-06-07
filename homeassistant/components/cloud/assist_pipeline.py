"""Handle Cloud assist pipelines."""

import asyncio
from typing import Any

from menuai.components.assist_pipeline import (
    async_create_default_pipeline,
    async_get_pipelines,
    async_setup_pipeline_store,
    async_update_pipeline,
)
from menuai.components.conversation import HOME_ASSISTANT_AGENT
from menuai.components.stt import DOMAIN as STT_DOMAIN
from menuai.components.tts import DOMAIN as TTS_DOMAIN
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .const import (
    DATA_PLATFORMS_SETUP,
    DOMAIN,
    STT_ENTITY_UNIQUE_ID,
    TTS_ENTITY_UNIQUE_ID,
)


async def async_create_cloud_pipeline(menuai: menuai) -> str | None:
    """Create a cloud assist pipeline."""
    # Wait for stt and tts platforms to set up and entities to be added
    # before creating the pipeline.
    platforms_setup = menuai.data[DATA_PLATFORMS_SETUP]
    await asyncio.gather(*(event.wait() for event in platforms_setup.values()))
    # Make sure the pipeline store is loaded, needed because assist_pipeline
    # is an after dependency of cloud
    await async_setup_pipeline_store(menuai)

    entity_registry = er.async_get(menuai)
    new_stt_engine_id = entity_registry.async_get_entity_id(
        STT_DOMAIN, DOMAIN, STT_ENTITY_UNIQUE_ID
    )
    new_tts_engine_id = entity_registry.async_get_entity_id(
        TTS_DOMAIN, DOMAIN, TTS_ENTITY_UNIQUE_ID
    )
    if new_stt_engine_id is None or new_tts_engine_id is None:
        # If there's no cloud stt or tts entity, we can't create a cloud pipeline.
        return None

    def cloud_assist_pipeline(menuai: menuai) -> str | None:
        """Return the ID of a cloud-enabled assist pipeline or None.

        Check if a cloud pipeline already exists with either
        legacy or current cloud engine ids.
        """
        for pipeline in async_get_pipelines(menuai):
            if (
                pipeline.conversation_engine == HOME_ASSISTANT_AGENT
                and pipeline.stt_engine in (DOMAIN, new_stt_engine_id)
                and pipeline.tts_engine in (DOMAIN, new_tts_engine_id)
            ):
                return pipeline.id
        return None

    if (cloud_assist_pipeline(menuai)) is not None or (
        cloud_pipeline := await async_create_default_pipeline(
            menuai,
            stt_engine_id=new_stt_engine_id,
            tts_engine_id=new_tts_engine_id,
            pipeline_name="MenuAI Cloud",
        )
    ) is None:
        return None

    return cloud_pipeline.id


async def async_migrate_cloud_pipeline_engine(
    menuai: menuai, platform: Platform, engine_id: str
) -> None:
    """Migrate the pipeline engines in the cloud assist pipeline."""
    # Migrate existing pipelines with cloud stt or tts to use new cloud engine id.
    # Added in 2024.02.0. Can be removed in 2025.02.0.

    # We need to make sure that both stt and tts are loaded before this migration.
    # Assist pipeline will call default engine when setting up the store.
    # Wait for the stt or tts platform loaded event here.
    if platform == Platform.STT:
        wait_for_platform = Platform.TTS
        pipeline_attribute = "stt_engine"
    elif platform == Platform.TTS:
        wait_for_platform = Platform.STT
        pipeline_attribute = "tts_engine"
    else:
        raise ValueError(f"Invalid platform {platform}")

    platforms_setup = menuai.data[DATA_PLATFORMS_SETUP]
    await platforms_setup[wait_for_platform].wait()

    # Make sure the pipeline store is loaded, needed because assist_pipeline
    # is an after dependency of cloud
    await async_setup_pipeline_store(menuai)

    kwargs: dict[str, Any] = {pipeline_attribute: engine_id}
    pipelines = async_get_pipelines(menuai)
    for pipeline in pipelines:
        if getattr(pipeline, pipeline_attribute) == DOMAIN:
            await async_update_pipeline(menuai, pipeline, **kwargs)
