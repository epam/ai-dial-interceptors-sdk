import http
from typing import Iterator, cast

import httpx
import openai
import pytest
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

from aidial_interceptors_sdk.chat_completion.base import (
    ChatCompletionNoOpInterceptor,
)
from aidial_interceptors_sdk.utils._exceptions import ResponseWrapper
from tests.utils.applications import create_broken_application
from tests.utils.chunks import create_chunk_checker
from tests.utils.dial_app import create_openai_client
from tests.utils.json import match_objects

to_many_requests_error = ResponseWrapper(
    status_code=http.HTTPStatus.TOO_MANY_REQUESTS,
    content={"error": {"message": "Too many requests"}},
    headers=httpx.Headers(headers={"Retry-After": "42"}),
)


@pytest.mark.parametrize("stream", [False, True])
def test_interceptor_errors(stream: bool):
    openai_client = create_openai_client(
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

    try:
        response = cast(
            ChatCompletion | Iterator[ChatCompletionChunk],
            (
                openai_client.chat.completions.create(
                    model=None,  # type: ignore
                    stream=stream,
                    messages=[{"role": "user", "content": "hello"}],
                )
            ),
        )
    except openai.APIStatusError as e:
        assert e.status_code == 500
        assert e.body == {
            "message": "Error during processing the request",
            "type": "runtime_error",
            "code": "500",
        }
        return

    if isinstance(response, ChatCompletion):
        assert (
            False
        ), "The request should have failed with openai.APIStatusError error"
    else:
        # First SEE chunk
        actual = next(response).to_dict()
        expected = create_chunk_checker(stream=True)()
        match_objects(actual, expected)

        # Second SEE chunk with an error
        try:
            next(response)
        except openai.APIError as e:
            assert e.body == {
                "message": "Too many requests",
                "type": "internal_server_error",
                "code": "500",
            }
