import itertools
from typing import Iterable

import pytest
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

from aidial_interceptors_sdk.chat_completion.base import (
    ChatCompletionNoOpInterceptor,
)
from tests.utils.applications import RequestValidationApplication
from tests.utils.chunks import create_chunk_checker
from tests.utils.dial_app import create_openai_client
from tests.utils.json import has_type, match_objects, memorize


@pytest.mark.parametrize("stream", [False, True])
def test_extra_fields(stream: bool):
    def validate_request(body: dict):
        assert body.get("extra_top_field") == "extra_top_value"
        message = body["messages"][0]
        assert message.get("extra_message_field") == "extra_message_value"

    openai_client = create_openai_client(
        [
            ("validator", RequestValidationApplication(validate_request)),
            ("noop", ChatCompletionNoOpInterceptor),
        ],
        ["noop", "validator"],
    )

    response: ChatCompletion | Iterable[ChatCompletionChunk] = (
        openai_client.chat.completions.create(
            model=None,  # type: ignore
            stream=stream,
            messages=[
                {
                    "role": "user",
                    "content": "hello",
                    "extra_message_field": "extra_message_value",  # type: ignore
                }
            ],
            extra_body={"extra_top_field": "extra_top_value"},
        )
    )

    checker = create_chunk_checker(
        stream=stream,
        id=memorize(has_type(str)),
        created=memorize(has_type(int)),
    )

    if isinstance(response, ChatCompletion):
        match_objects(
            response.to_dict(),
            checker(
                delta={"role": "assistant", "content": "hello"},
                finish_reason="stop",
            ),
        )

    else:
        expected_chunks = [
            checker({"role": "assistant"}),
            checker({"content": "hello"}),
            checker({}, finish_reason="stop"),
        ]

        for actual, expected in itertools.zip_longest(
            response, expected_chunks
        ):
            match_objects(actual.to_dict(), expected)
