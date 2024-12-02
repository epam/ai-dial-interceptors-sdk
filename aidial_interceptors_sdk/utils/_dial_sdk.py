"""
All kinds of logic which is a good candidate
to be moved eventually to the SDK itself.
"""

from aidial_sdk.chat_completion import Response
from aidial_sdk.chat_completion.chunks import ArbitraryChunk, BaseChunk


def send_chunk_to_response(response: Response, chunk: BaseChunk | dict):
    if isinstance(chunk, dict):
        for choice in chunk.get("choices") or []:
            if (index := choice.get("index")) is not None:
                response._last_choice_index = max(
                    response._last_choice_index, index + 1
                )
        response._queue.put_nowait(ArbitraryChunk(chunk=chunk))
    else:
        response._queue.put_nowait(chunk)
