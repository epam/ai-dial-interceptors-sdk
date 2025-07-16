import json
from typing import Any, Mapping

from .json import Check, has_type, match_objects

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
        assert string.startswith(
            "data: "
        ), f"Invalid data entry in SSE stream: {string!r}"
        string = string.removeprefix("data: ")

        if string == "[DONE]":
            actual = string
        else:
            try:
                actual = json.loads(string)
            except Exception:
                assert (
                    False
                ), f"The data entry in SSE stream isn't a valid JSON: {string!r}"

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
