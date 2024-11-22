import asyncio
from typing import List, Tuple, Type, assert_never

import httpx
import openai
from aidial_sdk import DIALApp
from aidial_sdk.chat_completion import ChatCompletion
from aidial_sdk.embeddings import Embeddings
from fastapi.testclient import TestClient

from aidial_interceptors_sdk.chat_completion.adapter import (
    interceptor_to_chat_completion,
)
from aidial_interceptors_sdk.chat_completion.base import (
    ChatCompletionInterceptor,
)
from aidial_interceptors_sdk.dial_client import _UPSTREAMS_HEADER
from aidial_interceptors_sdk.embeddings.adapter import interceptor_to_embeddings
from aidial_interceptors_sdk.embeddings.base import EmbeddingsInterceptor
from aidial_interceptors_sdk.examples.app_factory import create_app
from aidial_interceptors_sdk.examples.registry import Interceptors
from aidial_interceptors_sdk.utils._http_client import HTTPClientFactory

AppEndpoint = (
    Type[ChatCompletionInterceptor]
    | Type[EmbeddingsInterceptor]
    | ChatCompletion
    | Embeddings
)

AppEndpoints = List[Tuple[str, AppEndpoint]]


def add_endpoints(
    app: DIALApp,
    *,
    dial_url: str,
    client_factory: HTTPClientFactory,
    endpoints: AppEndpoints,
) -> None:
    for name, endpoint in endpoints:
        if isinstance(endpoint, ChatCompletion):
            app.add_chat_completion(name, endpoint)
        elif isinstance(endpoint, Embeddings):
            app.add_embeddings(name, endpoint)
        elif issubclass(endpoint, EmbeddingsInterceptor):
            app.add_embeddings(
                name,
                interceptor_to_embeddings(endpoint, dial_url, client_factory),
            )
        elif issubclass(endpoint, ChatCompletionInterceptor):
            app.add_chat_completion(
                name,
                interceptor_to_chat_completion(
                    endpoint, dial_url, client_factory
                ),
            )
        else:
            assert_never(endpoint)


def create_recursive_app(endpoints: AppEndpoints) -> DIALApp:
    dial_url = "http://test-app.com"
    client_future: asyncio.Future[httpx.AsyncClient] = asyncio.Future()

    app = create_app(
        dial_url=dial_url,
        client_factory=lambda: client_future,
        interceptors=Interceptors(),
    )

    add_endpoints(
        app,
        dial_url=dial_url,
        client_factory=lambda: client_future,
        endpoints=endpoints,
    )

    client_future.set_result(httpx.AsyncClient(app=app, base_url=dial_url))

    return app


def create_openai_client(
    endpoints: AppEndpoints, upstreams: List[str]
) -> openai.AzureOpenAI:
    dial_app = create_recursive_app(endpoints)
    http_client = TestClient(dial_app)

    deployment, *upstreams = upstreams

    return openai.AzureOpenAI(
        azure_endpoint=str(http_client.base_url),
        azure_deployment=deployment,
        http_client=http_client,
        api_key="-",
        api_version="2024-10-21",
        max_retries=0,
        default_headers={_UPSTREAMS_HEADER: ",".join(upstreams)},
    )
