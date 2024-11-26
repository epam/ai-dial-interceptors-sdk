import http
import itertools

import pytest

from aidial_interceptors_sdk.chat_completion.base import (
    ChatCompletionNoOpInterceptor,
)
from aidial_interceptors_sdk.utils._exceptions import _parse_dial_exception
from tests.utils.applications import create_broken_application
from tests.utils.chunks import create_chunk_checker, create_sse_stream_checker
from tests.utils.dial_app import create_httpx_client
from tests.utils.json import has_type, match_objects, memorize

to_many_requests_error = _parse_dial_exception(
    status_code=http.HTTPStatus.TOO_MANY_REQUESTS,
    content={"error": {"message": "Too many requests"}},
    headers={"retry-after": "42"},
)


@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize("repeats", [1, 2, 3])
async def test_interceptor_errors(stream: bool, repeats: int):
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
        [
            *itertools.repeat("no-op", repeats),
            "upstream",
        ],
    )

    response = await httpx_client.post(
        "chat/completions",
        json={
            "stream": stream,
            "messages": [{"role": "user", "content": "hello"}],
        },
    )

    if not stream:
        assert response.status_code == 429
        actual_headers = {
            k.decode(): v.decode() for k, v in response.headers.raw
        }
        assert match_objects(
            actual_headers,
            {
                "retry-after": "42",
                "content-length": has_type(str),
                "content-type": "application/json",
            },
        )
        assert response.json() == {
            "error": {"message": "Too many requests", "code": "429"}
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
                # FIXME: error chunks shouldn't have id/created/object fields
                # https://github.com/epam/ai-dial-sdk/blob/development/aidial_sdk/chat_completion/chunks.py#L31-L35
                # Alternatively, the errors in the stream should be
                # translated to DIALExceptions in the Interceptors SDK
                "id": id_checker,
                "created": created_checker,
                "object": "chat.completion.chunk",
                "error": {"message": "Too many requests", "code": "429"},
            },
            "[DONE]",
        )

        match_objects(actual, expected)


@pytest.mark.parametrize("stream", [False, True])
async def test_direct_errors(stream: bool):
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
        ["upstream"],
    )

    response = await httpx_client.post(
        "chat/completions",
        json={
            "stream": stream,
            "messages": [{"role": "user", "content": "hello"}],
        },
    )

    if not stream:
        assert response.status_code == 429
        actual_headers = {
            k.decode(): v.decode() for k, v in response.headers.raw
        }
        assert match_objects(
            actual_headers,
            {
                "content-length": has_type(str),
                "content-type": "application/json",
                "retry-after": "42",
            },
        )
        assert response.json() == {
            "error": {"message": "Too many requests", "code": "429"}
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
            {"error": {"message": "Too many requests", "code": "429"}},
            "[DONE]",
        )

        match_objects(actual, expected)
