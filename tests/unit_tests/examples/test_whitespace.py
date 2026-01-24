import itertools
from typing import Iterable

import pytest
from aidial_sdk.chat_completion import Choice, Request, Response
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

from aidial_interceptors_sdk.examples.chat_completion import (
    WhitespaceAccumulatorInterceptor,
)
from tests.utils.applications import WhitespaceEchoApplication
from tests.utils.chunks import create_chunk_checker
from tests.utils.dial_app import create_openai_client
from tests.utils.json import has_type, match_objects, memorize


def wrap(
    content: str | None = None, finish: bool = False, extra: bool = False
) -> dict:
    output: dict = {}
    if content is not None:
        output["content"] = content
    if finish:
        output["finish_reason"] = True
    if extra:
        output["as_attachment"] = True
    return output


def extra(content: str | None = None, finish: bool = False) -> dict:
    return wrap(content=content, finish=finish, extra=True)


def has_content(chunk: dict) -> bool:
    return chunk.get("content") is not None


def has_extra(chunk: dict) -> bool:
    return chunk.get("as_attachment") is True


def has_finish(chunk: dict) -> bool:
    return chunk.get("finish_reason") is True


def extract_content(chunk: dict) -> str | None:
    return chunk.get("content")


def check_nonstream(interceptor_output: list[dict]) -> dict:
    buffer: list[str] = []
    extra_buffer: list[str] = []
    for output in interceptor_output:
        content = extract_content(output)
        if not content:
            continue
        if has_extra(output):
            extra_buffer.append(content)
        else:
            buffer.append(content)

    content = "".join(buffer)
    result: dict = {
        "role": "assistant",
        "content": content,
    }
    if extra_buffer:
        result["custom_content"] = {
            "attachments": [{"data": data} for data in extra_buffer]
        }
    return result


def check_stream(checker, interceptor_output: list[dict]) -> list:
    checkers: list = []
    cur_extra_idx = 0
    first = True
    for output in interceptor_output:
        data: dict = {}
        finish_reason: str | None = None
        content = extract_content(output)
        if has_finish(output):
            finish_reason = "stop"
        if has_extra(output):
            data["custom_content"] = {
                "attachments": [{"index": cur_extra_idx, "data": content}]
            }
            cur_extra_idx += 1
        elif content is not None:
            data["content"] = content
        if first:
            data["role"] = "assistant"
            first = False
        checkers.append(checker(data, finish_reason=finish_reason))

    return checkers


tests = [
    (
        [wrap("")],
        [wrap(""), wrap(finish=True)],
    ),
    (
        [wrap(" ")],
        [wrap(" "), wrap(finish=True)],
    ),
    (
        [wrap(" "), wrap(" ")],
        [wrap("  "), wrap(finish=True)],
    ),
    (
        [wrap(" "), wrap(" "), wrap("a")],
        [wrap("  a"), wrap(finish=True)],
    ),
    (
        [wrap("a"), wrap(" "), wrap(" ")],
        [wrap("a"), wrap("  "), wrap(finish=True)],
    ),
    (
        [wrap("a"), wrap(" "), wrap(" "), wrap("b"), extra("t")],
        [wrap("a"), wrap("  b"), extra("t"), wrap(finish=True)],
    ),
    (
        [wrap("a"), wrap(" "), wrap(" "), wrap("b"), wrap(" ")],
        [wrap("a"), wrap("  b"), wrap(" "), wrap(finish=True)],
    ),
    (
        [extra(" "), wrap(" "), extra(" ")],
        [wrap(""), extra(" "), wrap(" "), extra(" "), wrap(finish=True)],
    ),
    (
        [extra(" "), wrap(" "), wrap(" ")],
        [wrap(""), extra(" "), wrap("  "), wrap(finish=True)],
    ),
]


@pytest.mark.parametrize("stream", [True])
@pytest.mark.parametrize("model_output, interceptor_output", tests)
def test_whitespace_accumulator_interceptor(
    stream: bool, model_output: list[dict], interceptor_output: list[dict]
):
    def callback(request: Request, response: Response, choice: Choice):
        for chunk in model_output:
            content = extract_content(chunk)
            if not content:
                continue
            if has_extra(chunk):
                choice.add_attachment(data=content)
            else:
                choice.append_content(content)

    openai_client = create_openai_client(
        [
            ("echo", WhitespaceEchoApplication(callback)),
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
                    "content": "dummy",
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
                check_nonstream(interceptor_output),
                finish_reason="stop",
            ),
        )

    else:
        expected_chunks = check_stream(checker, interceptor_output)

        for actual, expected in itertools.zip_longest(
            response, expected_chunks
        ):
            print(f"\nexpected {expected}")
            print(f"actual   {actual.to_dict()}")
            match_objects(actual.to_dict(), expected)
