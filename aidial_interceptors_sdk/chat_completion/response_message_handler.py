"""
CODE-GENERATED from aidial_interceptors_sdk/chat_completion/request_message_handler.py module.
DO NOT MODIFY THIS FILE.

Callbacks to handle messages in the chat completion response.
"""

from abc import ABC
from typing import List

from aidial_sdk.pydantic_v1 import BaseModel

from aidial_interceptors_sdk.chat_completion.element_path import ElementPath
from aidial_interceptors_sdk.chat_completion.helpers import (
    traverse_dict_value,
    traverse_list,
)
from aidial_interceptors_sdk.utils.not_given import NotGiven


class ResponseMessageHandler(ABC, BaseModel):
    class Config:
        arbitrary_types_allowed = True

    async def on_response_stage(
        self, path: ElementPath, stage: dict
    ) -> List[dict] | dict:
        return stage

    async def on_response_stages(
        self, path: ElementPath, stages: List[dict] | NotGiven | None
    ) -> List[dict] | NotGiven | None:
        return stages

    async def on_response_attachment(
        self, path: ElementPath, attachment: dict
    ) -> List[dict] | dict:
        """
        Applied to individual attachments: every message and stage attachment
        """

        return attachment

    async def on_response_attachments(
        self, path: ElementPath, attachments: List[dict] | NotGiven | None
    ) -> List[dict] | NotGiven | None:
        """
        Applied to list of attachments: message attachments and stage attachments
        """
        return attachments

    async def on_response_state(
        self, path: ElementPath, state: dict | NotGiven | None
    ) -> dict | NotGiven | None:
        return state

    async def on_response_custom_content(
        self, path: ElementPath, custom_content: dict | NotGiven | None
    ) -> dict | NotGiven | None:
        return custom_content

    async def traverse_response_message(
        self, path: ElementPath, message: dict
    ) -> dict:

        async def apply_on_attachments(
            path: ElementPath, attachments: List[dict] | NotGiven | None
        ) -> List[dict] | NotGiven | None:
            attachments = await traverse_list(
                path.with_attachment_idx,
                attachments,
                self.on_response_attachment,
            )
            return await self.on_response_attachments(path, attachments)

        async def apply_on_stage(
            path: ElementPath, stage: dict
        ) -> List[dict] | dict:
            stage = await traverse_dict_value(
                path, stage, "attachments", apply_on_attachments
            )

            if path.stage_idx is not None and path.choice_ctx is not None:
                mapper = path.choice_ctx.stage_index_mapper
                stage["index"] = mapper(path.stage_idx)

            return await self.on_response_stage(path, stage)

        async def apply_on_stages(
            path: ElementPath, stages: List[dict] | NotGiven | None
        ) -> List[dict] | NotGiven | None:
            stages = await traverse_list(
                path.with_stage_idx, stages, apply_on_stage
            )
            return await self.on_response_stages(path, stages)

        async def apply_on_custom_content(
            path: ElementPath, cc: dict | NotGiven | None
        ) -> dict | NotGiven | None:
            cc = await traverse_dict_value(
                path, cc, "state", self.on_response_state
            )
            cc = await traverse_dict_value(
                path, cc, "attachments", apply_on_attachments
            )
            cc = await traverse_dict_value(path, cc, "stages", apply_on_stages)
            return await self.on_response_custom_content(path, cc)

        return await traverse_dict_value(
            path, message, "custom_content", apply_on_custom_content
        )
