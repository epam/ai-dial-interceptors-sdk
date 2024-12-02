import logging
from typing import Any, AsyncIterator, Callable, Optional, TypeVar

from aidial_sdk.exceptions import HTTPException as DialException

from aidial_interceptors_sdk.chat_completion.annotated_value import (
    AnnotatedChunk,
    AnnotatedException,
    AnnotatedValue,
    Annotation,
)
from aidial_interceptors_sdk.utils._exceptions import to_dial_exception

_log = logging.getLogger(__name__)

_T = TypeVar("_T")
_V = TypeVar("_V")


async def materialize_streaming_errors(
    stream: AsyncIterator[dict],
) -> AsyncIterator[dict | DialException]:

    try:
        async for chunk in stream:
            yield chunk
    except Exception as e:
        _log.exception(
            f"caught exception while streaming: {type(e).__module__}.{type(e).__name__}"
        )

        yield to_dial_exception(e)


def annotate_stream(
    annotation: Annotation, stream: AsyncIterator[dict | DialException]
) -> AsyncIterator[AnnotatedValue]:
    def _annotate(value: dict | DialException) -> AnnotatedValue:
        if isinstance(value, dict):
            return AnnotatedChunk(chunk=value, annotation=annotation)
        else:
            return AnnotatedException(error=value, annotation=annotation)

    return map_stream(_annotate, stream)


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
