import json
from collections.abc import Iterable, Mapping
from typing import Any

from aidial_sdk.utils.merge_chunks import (
    cleanup_indices,
    merge_chat_completion_chunks,
)
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

from tests.utils.json import Check, has_type, match_objects

_DATA_PREFIX = "data: "


def format_chunk(data: str | Mapping[str, Any]) -> str:
    if isinstance(data, str):
        return _DATA_PREFIX + data.strip() + "\n\n"
    else:
        return _DATA_PREFIX + json.dumps(data, separators=(",", ":")) + "\n\n"


def create_chunk_checker(
    *,
    stream: bool,
    id: Check | str = has_type(str),
    created: Check | int = has_type(int),
):
    def _checker(delta: dict = {}, finish_reason: str | None = None):
        object = "chat.completion.chunk" if stream else "chat.completion"
        message_key = "delta" if stream else "message"

        return {
            "id": id,
            "choices": [
                {
                    "finish_reason": finish_reason,
                    "index": 0,
                    message_key: delta,
                }
            ],
            "created": created,
            "object": object,
            "usage": None,
        }

    return _checker


def _data_prefix_checker(expected):
    def _check(path: str, string: Any):
        assert isinstance(string, str)
        assert string.startswith("data: "), (
            f"Invalid data entry in SSE stream: {string!r}"
        )
        string = string.removeprefix("data: ")

        if string == "[DONE]":
            actual = string
        else:
            try:
                actual = json.loads(string)
            except Exception:
                assert False, (
                    f"The data entry in SSE stream isn't a valid JSON: {string!r}"
                )

        match_objects(actual, expected, path)

    return _check


def create_sse_stream_checker(*chunk_checkers: Any):
    ret = []
    for checker in chunk_checkers:
        ret.append(_data_prefix_checker(checker))
        ret.append("")
    return ret


def create_chunk(
    *, stream: bool, delta: dict = {}, finish_reason: str | None = None
):
    return create_chunk_checker(stream=stream, id="id", created=0)(
        delta, finish_reason
    )


def _merge_chat_stream(stream: Iterable[ChatCompletionChunk]) -> ChatCompletion:
    chunks: list[dict] = []
    for chunk in stream:
        chunks.append(chunk.model_dump())

    response_dict = merge_chat_completion_chunks(*chunks)

    for choice in response_dict["choices"]:
        choice["message"] = cleanup_indices(choice["delta"])
        del choice["delta"]

    response_dict["object"] = "chat.completion"

    return ChatCompletion.parse_obj(response_dict)


def merge_chat_response(
    response: ChatCompletion | Iterable[ChatCompletionChunk],
) -> ChatCompletion:
    if isinstance(response, ChatCompletion):
        return response
    else:
        return _merge_chat_stream(response)
