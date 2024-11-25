import http

import httpx
import pytest

from aidial_interceptors_sdk.chat_completion.base import (
    ChatCompletionNoOpInterceptor,
)
from aidial_interceptors_sdk.utils._exceptions import ResponseWrapper
from tests.utils.applications import create_broken_application
from tests.utils.chunks import create_chunk_checker, create_sse_stream_checker
from tests.utils.dial_app import create_httpx_client
from tests.utils.json import has_type, match_objects, memorize

to_many_requests_error = ResponseWrapper(
    status_code=http.HTTPStatus.TOO_MANY_REQUESTS,
    content={"error": {"message": "Too many requests"}},
    headers=httpx.Headers(headers={"Retry-After": "42"}),
)


@pytest.mark.parametrize("stream", [False, True])
async def test_interceptor_errors(stream: bool):
    httpx_client = create_httpx_client(
        [
            (
                "upstream",
                (
                    "chat/completions",
                    create_broken_application(to_many_requests_error),
                ),
            ),
            ("no-op", ChatCompletionNoOpInterceptor),
        ],
        ["no-op", "no-op", "upstream"],
    )

    response = await httpx_client.post(
        "chat/completions",
        json={
            "stream": stream,
            "messages": [{"role": "user", "content": "hello"}],
        },
    )

    if not stream:
        assert response.status_code == 500
        assert response.json() == {
            "error": {
                "message": "Error during processing the request",
                "type": "runtime_error",
                "code": "500",
            }
        }
    else:
        assert response.status_code == 200

        actual = [line async for line in response.aiter_lines()]

        id_checker = memorize(has_type(str))
        created_checker = memorize(has_type(int))
        chunk_checker = create_chunk_checker(
            stream=stream,
            id=id_checker,
            created=created_checker,
        )

        expected = create_sse_stream_checker(
            chunk_checker(),
            {
                "id": id_checker,
                "created": created_checker,
                "object": "chat.completion.chunk",
                "error": {
                    "message": "Too many requests",
                    "type": "internal_server_error",
                    "code": "500",
                },
            },
            "[DONE]",
        )

        match_objects(actual, expected)
