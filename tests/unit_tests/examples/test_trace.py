import itertools
from typing import Iterable

import pytest
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

from tests.utils.applications import EchoApplication
from tests.utils.chunks import create_chunk_checker
from tests.utils.dial_app import create_openai_client
from tests.utils.interceptors import TracingInterceptor
from tests.utils.json import has_type, match_objects, memorize


@pytest.mark.parametrize("stream", [False, True])
def test_trace_interceptor(stream: bool):
    openai_client = create_openai_client(
        [
            ("echo", EchoApplication()),
            ("trace:{name:str}", TracingInterceptor),
        ],
        ["trace:1", "trace:2", "echo"],
    )

    response: ChatCompletion | Iterable[ChatCompletionChunk] = (
        openai_client.chat.completions.create(
            model=None,  # type: ignore
            stream=stream,
            messages=[{"role": "user", "content": "hello"}],
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
                    "content": "1.enter\n2.enter\nhello\n2.exit\n1.exit",
                },
                finish_reason="stop",
            ),
        )

    else:
        expected_chunks = [
            checker({"content": "1.enter\n"}),
            checker({"content": "2.enter\n"}),
            checker({"role": "assistant"}),
            checker({"content": "hello"}),
            checker({}, finish_reason="stop"),
            checker({"content": "\n2.exit"}),
            checker({"content": "\n1.exit"}),
        ]

        for actual, expected in itertools.zip_longest(
            response, expected_chunks
        ):
            match_objects(actual.to_dict(), expected)
