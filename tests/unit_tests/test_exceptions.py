import http
import itertools

import httpx
import pytest
from openai import APIStatusError

from aidial_interceptors_sdk.chat_completion.base import (
    ChatCompletionNoOpInterceptor,
)
from aidial_interceptors_sdk.utils._exceptions import (
    _parse_dial_exception,
    to_dial_exception,
)
from tests.utils.applications import create_broken_application
from tests.utils.chunks import create_chunk_checker, create_sse_stream_checker
from tests.utils.dial_app import create_httpx_client
from tests.utils.json import has_type, match_objects

_too_many_requests_error = _parse_dial_exception(
    status_code=http.HTTPStatus.TOO_MANY_REQUESTS,
    content={"error": {"message": "Too many requests"}},
    headers={"retry-after": "42"},
)


def test_to_dial_exception_drops_hop_by_hop_headers():
    request = httpx.Request("POST", "http://upstream/chat/completions")
    body = {
        "error": {
            "message": "maximum context length",
            "code": "400",
        }
    }
    response = httpx.Response(
        400,
        headers={
            "Retry-After": "0",
            "X-Request-ID": "abc",
        },
        json=body,
        request=request,
    )
    response.headers["Content-Length"] = "99"
    response.headers["Content-Encoding"] = "gzip"
    response.headers["Transfer-Encoding"] = "chunked"
    response.headers["Connection"] = "keep-alive"
    response.headers["Server"] = "vllm"
    response.headers["Proxy-Authenticate"] = "Basic"

    dial = to_dial_exception(
        APIStatusError("Bad request", response=response, body=body)
    )

    assert dial.status_code == 400
    assert "maximum context length" in dial.message
    names = {key.lower(): value for key, value in (dial.headers or {}).items()}
    assert "transfer-encoding" not in names
    assert "content-length" not in names
    assert "content-encoding" not in names
    assert "connection" not in names
    assert "server" not in names
    assert "proxy-authenticate" not in names
    assert names["retry-after"] == "0"
    assert names["x-request-id"] == "abc"


@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize("is_first_chunk_error", [False, True])
@pytest.mark.parametrize("repeats", [0, 1, 2, 3])
async def test_interceptor_errors(
    stream: bool, is_first_chunk_error: bool, repeats: int
):
    httpx_client = create_httpx_client(
        [
            (
                "upstream",
                (
                    "chat/completions",
                    create_broken_application(
                        _too_many_requests_error, is_first_chunk_error
                    ),
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
        assert response.json() == {
            "error": {"message": "Too many requests", "code": "429"}
        }

        assert match_objects(
            {k.decode(): v.decode() for k, v in response.headers.raw},
            {
                "retry-after": "42",
                "content-length": has_type(str),
                "content-type": "application/json",
            },
        )

    elif is_first_chunk_error and repeats > 0:
        # DIAL SDK promotes an error from the first chunk to a full response:
        # https://github.com/epam/ai-dial-sdk/blob/7632cdac59b2e21131f92c45713a67aab5ccabf7/aidial_sdk/utils/streaming.py#L86-L87

        assert response.status_code == 429
        assert response.json() == {
            "error": {"message": "Too many requests", "code": "429"}
        }

    else:
        assert response.status_code == 200

        actual = [line async for line in response.aiter_lines()]

        chunk_checkers = []

        if not is_first_chunk_error:
            chunk_checkers.append(create_chunk_checker(stream=stream)())

        chunk_checkers.extend(
            [
                {"error": {"message": "Too many requests", "code": "429"}},
                "[DONE]",
            ]
        )

        assert match_objects(actual, create_sse_stream_checker(*chunk_checkers))
