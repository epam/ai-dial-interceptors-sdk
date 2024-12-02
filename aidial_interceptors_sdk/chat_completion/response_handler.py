from typing import Dict, List

from aidial_sdk.chat_completion import Response
from aidial_sdk.chat_completion.chunks import BaseChunk
from aidial_sdk.pydantic_v1 import PrivateAttr

from aidial_interceptors_sdk.chat_completion.annotated_value import (
    AnnotatedChunk,
)
from aidial_interceptors_sdk.chat_completion.element_path import (
    ChoiceContext,
    ElementPath,
)
from aidial_interceptors_sdk.chat_completion.helpers import (
    traverse_dict_value,
    traverse_list,
)
from aidial_interceptors_sdk.chat_completion.index_mapper import IndexMapper
from aidial_interceptors_sdk.chat_completion.response_message_handler import (
    ResponseMessageHandler,
)
from aidial_interceptors_sdk.utils._dial_sdk import send_chunk_to_response
from aidial_interceptors_sdk.utils.not_given import NotGiven


class ResponseHandler(ResponseMessageHandler):
    """
    Callbacks for handling chat completion responses.

    1. the callbacks may mutate the response in place,
    2. the callbacks are applied in bottom-up order (the order of callbacks in the class definition reflects the order of application),
    3. a callback for a list element return a list of objects, which allows for adding or removing elements. Such callbacks have the type signature: `T -> List[T]`,
    4. a callback for a dictionary value returns an optional dictionary, which allows for adding or removing keys. Such callbacks have the type signature: `(T | NotGiven | None) -> (T | NotGiven | None)`.
    5. `on_response*` methods are expected to be overridden by subclasses.
    6. `traverse_response*` methods are not expected to be overridden by subclasses.

    The callbacks are intended to be used for:
    1. collecting information about the response,
    2. inplace modifying the response.

    Avoid it creating new entities in the response, creation of deeply nested
    entities is hard if possible.

    E.g. adding a new stage in a response which doesn't have custom content is impossible,
    because one would have to create "custom_content" field _before_
    creating the "stages" field. Bottom-up application order of callbacks
    doesn't allow for that.
    """

    response: Response

    # NOTE: `_stage_indices = {}` isn't going to work, since
    # the underscored field `_stage_indices` will be shared across
    # all instances of the class.
    _stage_indices: Dict[int, IndexMapper[int]] = PrivateAttr({})

    def _get_stage_index_mapper(self, choice_idx: int) -> IndexMapper[int]:
        if choice_idx not in self._stage_indices:
            self._stage_indices[choice_idx] = IndexMapper()
        return self._stage_indices[choice_idx]

    def reserve_stage_index(self, choice_idx: int) -> int:
        return self._get_stage_index_mapper(choice_idx).reserve()

    def send_chunk(self, chunk: BaseChunk | dict):
        return send_chunk_to_response(self.response, chunk)

    async def on_response_message(
        self, path: ElementPath, message: dict | NotGiven | None
    ) -> dict | NotGiven | None:
        return message

    async def on_response_finish_reason(
        self, path: ElementPath, finish_reason: str | NotGiven | None
    ) -> str | NotGiven | None:
        return finish_reason

    async def on_response_choice(
        self, path: ElementPath, choice: dict
    ) -> List[dict] | dict:
        return choice

    async def on_response_choices(
        self, choices: List[dict] | NotGiven | None
    ) -> List[dict] | NotGiven | None:
        return choices

    # TODO: add path to the signature and to the rest of similar methods
    async def on_response_usage(
        self, usage: dict | NotGiven | None
    ) -> dict | NotGiven | None:
        return usage

    async def on_stream_chunk(self, chunk: dict) -> None:
        self.send_chunk(chunk)

    async def traverse_response_chunk(self, ann_chunk: AnnotatedChunk) -> None:
        r = ann_chunk.chunk

        async def traverse_message(
            path: ElementPath, message: dict | NotGiven | None
        ) -> dict | NotGiven | None:
            if message is not None and not isinstance(message, NotGiven):
                message = await self.traverse_response_message(path, message)
            return await self.on_response_message(path, message)

        async def traverse_choice(
            path: ElementPath, choice: dict
        ) -> List[dict] | dict:
            choice = await traverse_dict_value(
                path, choice, "finish_reason", self.on_response_finish_reason
            )
            choice = await traverse_dict_value(
                path, choice, "delta", traverse_message
            )
            return await self.on_response_choice(path, choice)

        async def traverse_choices(
            path: ElementPath, choices: List[dict] | NotGiven | None
        ) -> List[dict] | NotGiven | None:
            def with_choice_ctx(choice_idx: int) -> ElementPath:
                return path.with_choice_ctx(
                    ChoiceContext(
                        index=choice_idx,
                        stage_index_mapper=self._get_stage_index_mapper(
                            choice_idx
                        ),
                    )
                )

            choices = await traverse_list(
                with_choice_ctx, choices, traverse_choice
            )
            return await self.on_response_choices(choices)

        async def traverse_response_usage(
            path: ElementPath, usage: dict | NotGiven | None
        ) -> dict | NotGiven | None:
            return await self.on_response_usage(usage)

        path = ElementPath(response_ctx=ann_chunk.annotation)
        r = await traverse_dict_value(path, r, "usage", traverse_response_usage)
        r = await traverse_dict_value(path, r, "choices", traverse_choices)

        await self.on_stream_chunk(r)
