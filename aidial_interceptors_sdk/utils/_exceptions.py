import dataclasses
from typing import Any

from aidial_sdk.exceptions import HTTPException as DialException
from fastapi.responses import JSONResponse as FastAPIResponse
from httpx import Headers
from openai import APIConnectionError, APIStatusError, APITimeoutError


@dataclasses.dataclass
class ResponseWrapper:
    status_code: int
    content: Any
    headers: Headers | None = None

    def to_fastapi_response(self) -> FastAPIResponse:
        return FastAPIResponse(
            content=self.content,
            status_code=self.status_code,
            headers=self.headers,
        )


def to_dial_exception(exc: Exception) -> DialException | ResponseWrapper:
    if isinstance(exc, APIStatusError):
        r = exc.response
        headers = r.headers

        # The original content length may have changed
        # due to the response modification in the adapter.
        if "Content-Length" in headers:
            del headers["Content-Length"]

        # httpx library (used by openai) automatically sets
        # "Accept-Encoding:gzip,deflate" header in requests to the upstream.
        # Therefore, we may receive from the upstream gzip-encoded
        # response along with "Content-Encoding:gzip" header.
        # We either need to encode the response, or
        # remove the "Content-Encoding" header.
        if "Content-Encoding" in headers:
            del headers["Content-Encoding"]

        try:
            content = r.json()
        except Exception:
            content = r.text

        return ResponseWrapper(
            status_code=r.status_code,
            headers=headers,
            content=content,
        )

    if isinstance(exc, APITimeoutError):
        return DialException("Request timed out", 504, "timeout")

    if isinstance(exc, APIConnectionError):
        return DialException(
            "Error communicating with OpenAI", 502, "connection"
        )

    if isinstance(exc, DialException):
        return exc

    return DialException(
        status_code=500,
        type="internal_server_error",
        message=str(exc),
    )


def to_json_content(exc: DialException | ResponseWrapper) -> Any:
    if isinstance(exc, DialException):
        return exc.json_error()
    else:
        return exc.content
