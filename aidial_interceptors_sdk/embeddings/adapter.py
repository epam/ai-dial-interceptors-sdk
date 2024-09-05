from typing import Type

from fastapi import Request
from openai.types import CreateEmbeddingResponse

from aidial_interceptors_sdk.dial_client import DialClient
from aidial_interceptors_sdk.embeddings.base import EmbeddingsInterceptor
from aidial_interceptors_sdk.utils._debug import debug_logging
from aidial_interceptors_sdk.utils._exceptions import dial_exception_decorator
from aidial_interceptors_sdk.utils._reflection import call_with_extra_body


def interceptor_to_embeddings_handler(cls: Type[EmbeddingsInterceptor]):
    @dial_exception_decorator
    async def _handler(request: Request) -> dict:

        dial_client = await DialClient.create(
            api_key=request.headers.get("api-key", None),
            api_version=request.query_params.get("api-version"),
        )

        interceptor = cls(dial_client=dial_client, **request.path_params)

        body = await request.json()
        body = await debug_logging("request")(interceptor.modify_request)(body)

        response: CreateEmbeddingResponse = await call_with_extra_body(
            dial_client.client.embeddings.create, body
        )

        resp = response.to_dict()
        resp = await debug_logging("response")(interceptor.modify_response)(
            resp
        )
        return resp

    return _handler
