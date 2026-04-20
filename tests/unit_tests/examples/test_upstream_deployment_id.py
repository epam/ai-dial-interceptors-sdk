from collections.abc import Iterable

import pytest
from aidial_sdk.chat_completion import ChatCompletion as DIALChatCompletion
from aidial_sdk.chat_completion import Request, Response
from aidial_sdk.chat_completion.chunks import ContentChunk
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from typing_extensions import override

from aidial_interceptors_sdk.chat_completion.base import (
    ChatCompletionInterceptor,
)
from tests.utils.chunks import merge_chat_response
from tests.utils.dial_app import create_openai_client


class _Interceptor(ChatCompletionInterceptor):
    @override
    async def on_stream_end(self) -> None:
        self.send_chunk(
            ContentChunk(
                f"upstream_deployment_id={self.upstream_deployment_id}", 0
            )
        )


class _Model(DIALChatCompletion):
    async def chat_completion(
        self, request: Request, response: Response
    ) -> None:
        response.set_model(request.deployment_id)
        with response.create_single_choice() as choice:
            choice.append_content(request.messages[-1].text())


@pytest.mark.parametrize("stream", [False, True])
def test_upstream_deployment_id(stream: bool):
    openai_client = create_openai_client(
        [
            ("echo-interceptor", _Interceptor),
            ("upstream-id", _Model()),
        ],
    )

    response: ChatCompletion | Iterable[ChatCompletionChunk] = (
        openai_client.chat.completions.create(
            model="test-model-name",
            stream=stream,
            messages=[{"role": "user", "content": ""}],
        )
    )
    resp = merge_chat_response(response)

    expected_content = "upstream_deployment_id=upstream-id"
    assert resp.choices[0].message.content == expected_content
