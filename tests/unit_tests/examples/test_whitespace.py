import itertools
from typing import Iterable

import pytest
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

from aidial_interceptors_sdk.examples.chat_completion import (
    WhitespaceAccumulatorInterceptor,
)
from tests.utils.applications import WhitespaceEchoApplication
from tests.utils.chunks import create_chunk_checker
from tests.utils.dial_app import create_openai_client
from tests.utils.json import has_type, match_objects, memorize


@pytest.mark.parametrize("stream", [False, True])
def test_whitespace_accumulator_interceptor(stream: bool):
    openai_client = create_openai_client(
        [
            ("echo", WhitespaceEchoApplication()),
            ("whitespace-accumulator", WhitespaceAccumulatorInterceptor),
        ],
        ["whitespace-accumulator", "echo"],
    )

    response: ChatCompletion | Iterable[ChatCompletionChunk] = (
        openai_client.chat.completions.create(
            model=None,  # type: ignore
            stream=stream,
            messages=[
                {
                    "role": "assistant",
                    "content": "hello",
                },
            ],
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
                {
                    "role": "assistant",
                    "content": "          hello          ",
                },
                finish_reason="stop",
            ),
        )

    else:
        expected_chunks = [
            checker({"role": "assistant"}),
            checker({"content": "          hello"}),
            checker({}, finish_reason="stop"),
            checker({"content": "          "}),
        ]

        for actual, expected in itertools.zip_longest(
            response, expected_chunks
        ):
            match_objects(actual.to_dict(), expected)
