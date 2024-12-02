from typing import Type

from aidial_sdk.embeddings import Embeddings
from aidial_sdk.embeddings.request import Request
from aidial_sdk.embeddings.response import Response
from openai.types import CreateEmbeddingResponse

from aidial_interceptors_sdk.dial_client import DialClient
from aidial_interceptors_sdk.embeddings.base import EmbeddingsInterceptor
from aidial_interceptors_sdk.utils._debug import debug_logging
from aidial_interceptors_sdk.utils._exceptions import dial_exception_decorator
from aidial_interceptors_sdk.utils._http_client import HTTPClientFactory
from aidial_interceptors_sdk.utils._reflection import call_with_extra_body


def interceptor_to_embeddings(
    cls: Type[EmbeddingsInterceptor],
    dial_url: str,
    client_factory: HTTPClientFactory,
) -> Embeddings:

    class Impl(Embeddings):
        @dial_exception_decorator
        async def embeddings(self, request: Request) -> Response:
            dial_client = await DialClient.create(
                dial_url=dial_url,
                api_key=request.api_key,
                api_version=request.api_version,
                authorization=request.jwt,
                headers=request.headers,
                client_factory=client_factory,
            )

            interceptor = cls(
                dial_client=dial_client,
                **request.original_request.path_params,
            )

            body = await request.original_request.json()
            body = await debug_logging("request")(interceptor.modify_request)(
                body
            )

            response: CreateEmbeddingResponse = await call_with_extra_body(
                dial_client.client.embeddings.create, body
            )

            response_dict = await debug_logging("response")(
                interceptor.modify_response
            )(response.to_dict())

            return Response.parse_obj(response_dict)

    return Impl()
