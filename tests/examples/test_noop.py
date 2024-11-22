import asyncio

import httpx
import openai
from aidial_sdk.chat_completion import ChatCompletion, Request, Response
from fastapi.testclient import TestClient

from aidial_interceptors_sdk.examples.app_factory import create_app


class EchoApplication(ChatCompletion):
    async def chat_completion(
        self, request: Request, response: Response
    ) -> None:
        last_message = request.messages[-1]

        with response.create_single_choice() as choice:
            choice.append_content(last_message.text())


def create_http_client() -> TestClient:
    base_url = "http://test-app.com"
    client_future: asyncio.Future[httpx.AsyncClient] = asyncio.Future()

    app = create_app(dial_url=base_url, client_factory=lambda: client_future)
    app.add_chat_completion("interceptor", EchoApplication())

    client_future.set_result(httpx.AsyncClient(app=app, base_url=base_url))

    return TestClient(app)


def test_noop():

    http_client = create_http_client()

    openai_client = openai.AzureOpenAI(
        azure_endpoint=str(http_client.base_url),
        http_client=http_client,
        api_key="-",
        api_version="2024-10-21",
        max_retries=0,
    )

    response = openai_client.chat.completions.create(
        model="no-op",
        messages=[
            {
                "role": "user",
                "content": "2+3=?",
            }
        ],
    )

    print(response)
    assert True
