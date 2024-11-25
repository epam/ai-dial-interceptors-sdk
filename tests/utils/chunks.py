import json
from typing import Any, Mapping

from tests.utils.json import Check, has_type

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


def create_chunk(
    *, stream: bool, delta: dict = {}, finish_reason: str | None = None
):
    return create_chunk_checker(stream=stream, id="id", created=0)(
        delta, finish_reason
    )
