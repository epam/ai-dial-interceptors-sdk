import logging
from typing import Any, AsyncIterator, Callable, List, Optional, TypeVar

import aiostream
import openai
from aidial_sdk.exceptions import HTTPException as DialException

_log = logging.getLogger(__name__)

_T = TypeVar("_T")
_V = TypeVar("_V")


async def handle_streaming_errors(
    stream: AsyncIterator[dict],
) -> AsyncIterator[dict]:

    try:
        async for chunk in stream:
            yield chunk
    except openai.APIError as e:
        _log.error(f"error during steaming: {e.body}")

        display_message = None
        if e.body is not None and isinstance(e.body, dict):
            display_message = e.body.get("display_message", None)

        yield DialException(
            message=e.message,
            type=e.type,
            param=e.param,
            code=e.code,
            display_message=display_message,
        ).json_error()


# TODO: add to SDK as a inverse of cleanup_indices
def _add_indices(chunk: Any) -> Any:
    if isinstance(chunk, list):
        ret = []
        for idx, elem in enumerate(chunk, start=1):
            if isinstance(elem, dict) and "index" not in elem:
                elem = {**elem, "index": idx}
            ret.append(_add_indices(elem))
        return ret

    if isinstance(chunk, dict):
        return {key: _add_indices(value) for key, value in chunk.items()}

    return chunk


# TODO: add to SDK as an inverse of merge_chunks
def block_response_to_streaming_chunk(response: dict) -> dict:
    for choice in response["choices"]:
        choice["delta"] = choice["message"]
        del choice["message"]
        _add_indices(choice["delta"])
    return response


async def map_stream(
    func: Callable[[_T], Optional[_V]], iterator: AsyncIterator[_T]
) -> AsyncIterator[_V]:
    async for item in iterator:
        new_item = func(item)
        if new_item is not None:
            yield new_item


async def singleton_stream(item: _T) -> AsyncIterator[_T]:
    yield item


async def join_iterators(iters: List[AsyncIterator[_T]]) -> AsyncIterator[_T]:
    combine = aiostream.stream.merge(*iters)
    # FIXME: UserWarning: Streamer is iterated outside of its context
    async for item in combine:
        yield item
