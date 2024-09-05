import json
import logging
from typing import Any, AsyncIterator, Type, cast

from aidial_sdk.chat_completion import ChatCompletion as DialChatCompletion
from aidial_sdk.chat_completion import Request as DialRequest
from aidial_sdk.chat_completion import Response as DialResponse
from openai import AsyncStream
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

from aidial_interceptors_sdk.chat_completion.base import (
    ChatCompletionInterceptor,
)
from aidial_interceptors_sdk.dial_client import DialClient
from aidial_interceptors_sdk.error import EarlyStreamExit
from aidial_interceptors_sdk.utils._debug import debug_logging
from aidial_interceptors_sdk.utils._exceptions import dial_exception_decorator
from aidial_interceptors_sdk.utils._reflection import call_with_extra_body
from aidial_interceptors_sdk.utils.streaming import (
    block_response_to_streaming_chunk,
    handle_streaming_errors,
    map_stream,
    singleton_stream,
)

_log = logging.getLogger(__name__)
_debug = _log.isEnabledFor(logging.DEBUG)


def interceptor_to_chat_completion(
    cls: Type[ChatCompletionInterceptor],
) -> DialChatCompletion:
    class Impl(DialChatCompletion):
        @dial_exception_decorator
        async def chat_completion(
            self, request: DialRequest, response: DialResponse
        ) -> None:

            dial_client = await DialClient.create(
                api_key=request.api_key,
                api_version=request.api_version,
            )

            interceptor = cls(
                dial_client=dial_client,
                response=response,
                **request.original_request.path_params,
            )

            request_body = await request.original_request.json()
            request_body = await debug_logging("request")(
                interceptor.traverse_request
            )(request_body)

            async def call_upstream(
                request: dict, call_context: Any | None
            ) -> AsyncIterator[dict]:
                upstream_response = cast(
                    AsyncStream[ChatCompletionChunk] | ChatCompletion,
                    await call_with_extra_body(
                        dial_client.client.chat.completions.create, request
                    ),
                )

                if isinstance(upstream_response, ChatCompletion):
                    resp = upstream_response.to_dict()
                    if _debug:
                        _log.debug(
                            f"upstream response[{call_context}]: {json.dumps(resp)}"
                        )

                    chunk = block_response_to_streaming_chunk(resp)
                    stream = singleton_stream(chunk)
                else:

                    def on_upstream_chunk(chunk: ChatCompletionChunk) -> dict:
                        d = chunk.to_dict()
                        if _debug:
                            _log.debug(
                                f"upstream chunk[{call_context}]: {json.dumps(d)}"
                            )
                        return d

                    stream = map_stream(on_upstream_chunk, upstream_response)

                return handle_streaming_errors(stream)

            try:
                await interceptor.on_stream_start()

                async for chunk in await interceptor.call_upstreams(
                    request_body, call_upstream
                ):
                    if "error" in chunk.chunk:
                        await interceptor.on_stream_error(chunk)
                    else:
                        await interceptor.traverse_response_chunk(chunk)

                await interceptor.on_stream_end()
            except EarlyStreamExit:
                pass

    return Impl()
