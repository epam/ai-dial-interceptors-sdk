from typing import Any, AsyncIterator, Callable, Coroutine

from aidial_interceptors_sdk.chat_completion.annotated_chunk import (
    AnnotatedChunk,
)
from aidial_interceptors_sdk.chat_completion.request_handler import (
    RequestHandler,
)
from aidial_interceptors_sdk.chat_completion.response_handler import (
    ResponseHandler,
)
from aidial_interceptors_sdk.dial_client import DialClient


class ChatCompletionInterceptor(RequestHandler, ResponseHandler):
    dial_client: DialClient

    async def call_upstreams(
        self,
        request: dict,
        call_upstream: Callable[
            [dict, Any | None], Coroutine[Any, Any, AsyncIterator[dict]]
        ],
    ) -> AsyncIterator[AnnotatedChunk]:
        async def iterator():
            call_context = None
            async for chunk in await call_upstream(request, call_context):
                yield AnnotatedChunk(chunk=chunk, annotation=call_context)

        return iterator()

    async def on_stream_start(self) -> None:
        # TODO: it's probably worth to put all the chunks
        # generated by this method into a separate list.
        # And then merge them all with the first incoming chunk.
        # Otherwise, we may end up with choice being open *before*
        # its "assistant" role is reported.
        pass

    async def on_stream_error(self, error: AnnotatedChunk) -> None:
        self.send_chunk(error.chunk)

    async def on_stream_end(self) -> None:
        # TODO: it's probably worth to withhold the last chunk generated by
        # on_stream_chunk and merge it with all the chunks reported by on_stream_end.
        pass


class ChatCompletionNoOpInterceptor(ChatCompletionInterceptor):
    pass
