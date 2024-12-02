import functools
import logging
from typing import Dict

from aidial_sdk.exceptions import HTTPException as DialException
from openai import APIConnectionError, APIError, APIStatusError, APITimeoutError

_log = logging.getLogger(__name__)


def _parse_dial_exception(
    status_code: int,
    content: dict | str,
    headers: Dict[str, str] | None = None,
):
    if (
        isinstance(content, dict)
        and (error := content.get("error"))
        and isinstance(error, dict)
    ):
        message = error.get("message") or "Unknown error"
        code = error.get("code")
        type = error.get("type")
        param = error.get("param")
        display_message = error.get("display_message")
    else:
        message = str(content)
        code = type = param = display_message = None

    return DialException(
        status_code=status_code,
        message=message,
        type=type,
        param=param,
        code=code,
        display_message=display_message,
        headers=headers,
    )


def to_dial_exception(exc: Exception) -> DialException:
    if isinstance(exc, APIStatusError):
        # Non-streaming errors reported by `openai` library via this exception

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

        plain_headers = {k.decode(): v.decode() for k, v in headers.raw}

        try:
            content = r.json()
        except Exception:
            content = r.text

        return _parse_dial_exception(
            status_code=r.status_code,
            headers=plain_headers,
            content=content,
        )

    if isinstance(exc, APIError):
        # Streaming errors reported by `openai` library via this exception
        status_code: int = 500
        if exc.code:
            try:
                status_code = int(exc.code)
            except Exception:
                pass

        return _parse_dial_exception(
            status_code=status_code,
            headers={},
            content={"error": exc.body or {}},
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


def dial_exception_decorator(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            _log.exception(
                f"caught exception: {type(e).__module__}.{type(e).__name__}"
            )
            raise to_dial_exception(e) from e

    return wrapper
