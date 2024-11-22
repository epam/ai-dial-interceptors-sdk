from aidial_sdk.chat_completion import ChatCompletion, Request, Response

from aidial_interceptors_sdk.chat_completion.base import (
    ChatCompletionNoOpInterceptor,
)
from tests.examples.utils import create_openai_client


class EchoApplication(ChatCompletion):
    async def chat_completion(
        self, request: Request, response: Response
    ) -> None:
        last_message = request.messages[-1]

        with response.create_single_choice() as choice:
            choice.append_content(last_message.text())


def test_noop():
    openai_client = create_openai_client(
        [
            ("final", EchoApplication()),
            ("no-op", ChatCompletionNoOpInterceptor),
        ],
        ["no-op", "no-op", "final"],
    )

    response = openai_client.chat.completions.create(
        model=None,  # type: ignore
        messages=[
            {
                "role": "user",
                "content": "2+3=?",
            }
        ],
    )

    print(response)
    assert True
