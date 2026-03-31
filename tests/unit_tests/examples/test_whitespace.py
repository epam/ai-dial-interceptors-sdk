import itertools
from collections.abc import Iterable

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
    content: str | None = None,
    extra: str | None = None,
    role: str | None = None,
    finish: str | None = None,
) -> dict:
    output: dict = {}
    if content is not None:
        output["content"] = content
    if extra is not None:
        output["extra_content"] = extra
    if role is not None:
        output["role"] = role
    if finish is not None:
        output["finish_reason"] = finish
    return output


def extra(
    content: str | None = None,
    role: str | None = None,
    finish: str | None = None,
) -> dict:
    return wrap(extra=content, role=role, finish=finish)


def start() -> dict:
    return wrap(role="assistant")


def end() -> dict:
    return wrap(finish="stop")


def get_content(chunk: dict) -> str | None:
    return chunk.get("content")


def get_extra_content(chunk: dict) -> str | None:
    return chunk.get("extra_content")


def get_role(chunk: dict) -> str | None:
    return chunk.get("role")


def get_finish_reason(chunk: dict) -> str | None:
    return chunk.get("finish_reason")


def check_nonstream(interceptor_output: list[dict]) -> dict:
    buffer: list[str] = []
    extra_buffer: list[str] = []
    for output in interceptor_output:
        if content := get_content(output):
            buffer.append(content)
        if extra_content := get_extra_content(output):
            extra_buffer.append(extra_content)

    content = "".join(buffer)
    result: dict = {
        "role": "assistant",
    }
    if buffer:
        result["content"] = content
    if extra_buffer:
        result["custom_content"] = {
            "attachments": [{"data": data} for data in extra_buffer]
        }
    return result


def check_stream(checker, interceptor_output: list[dict]) -> list:
    checkers: list = []
    cur_extra_idx = 0
    for output in interceptor_output:
        data: dict = {}

        if content := get_content(output):
            data["content"] = content
        if extra_content := get_extra_content(output):
            data["custom_content"] = {
                "attachments": [{"index": cur_extra_idx, "data": extra_content}]
            }
            cur_extra_idx += 1
        if role := get_role(output):
            data["role"] = role
        finish_reason = get_finish_reason(output)

        checkers.append(checker(data, finish_reason=finish_reason))

    return checkers


tests = [
    (
        [wrap("")],
        [start(), end()],
    ),
    (
        [wrap(" ")],
        [start(), wrap(" "), end()],
    ),
    (
        [wrap(" "), wrap(" ")],
        [start(), wrap("  "), end()],
    ),
    (
        [wrap(" "), wrap(" "), wrap("a")],
        [start(), wrap("  a"), end()],
    ),
    (
        [wrap("a"), wrap(" "), wrap(" ")],
        [start(), wrap("a"), wrap("  "), end()],
    ),
    (
        [wrap("a"), wrap(" "), wrap(" "), wrap("b"), extra("t")],
        [start(), wrap("a"), wrap("  b"), extra("t"), end()],
    ),
    (
        [wrap("a"), wrap(" "), wrap(" "), wrap("b"), wrap(" ")],
        [start(), wrap("a"), wrap("  b"), wrap(" "), end()],
    ),
    (
        [extra(" "), wrap(" "), extra(" ")],
        [start(), extra(" "), wrap(" "), extra(" "), end()],
    ),
    (
        [extra(" "), wrap(" "), wrap(" "), extra(" ")],
        [start(), extra(" "), wrap("  "), extra(" "), end()],
    ),
    (
        [wrap(" "), wrap("\t"), wrap(" ", extra="\n"), wrap(" "), wrap(" ")],
        [start(), wrap(" \t "), extra("\n"), wrap("  "), end()],
    ),
]


@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize("model_output, interceptor_output", tests)
def test_whitespace_accumulator_interceptor(
    stream: bool, model_output: list[dict], interceptor_output: list[dict]
):
    def callback(request: Request, response: Response, choice: Choice):
        for chunk in model_output:
            if content := get_content(chunk):
                choice.append_content(content)
            if extra_content := get_extra_content(chunk):
                choice.add_attachment(data=extra_content)

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
            match_objects(actual.to_dict(), expected)
