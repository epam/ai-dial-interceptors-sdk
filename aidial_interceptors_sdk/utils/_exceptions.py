import contextlib
import functools
import logging

from aidial_sdk.exceptions import HTTPException as DialException
from openai import APIConnectionError, APIError, APIStatusError, APITimeoutError

_log = logging.getLogger(__name__)

_HOP_BY_HOP_HEADERS = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    }
)

# Uvicorn adds its own "Server: uvicorn" response header.
# Multiple "Server" headers are prohibited by RFC 9110 §5.3,
# a strict HTTP parser may reject such an HTTP response.
# Content-Length / Content-Encoding are stale after the JSON body is rebuilt.
_PROXY_MANAGED_RESPONSE_HEADERS = frozenset(
    {
        "server",
        "content-length",
        "content-encoding",
    }
)

_STRIPPED_RESPONSE_HEADERS = (
    _HOP_BY_HOP_HEADERS | _PROXY_MANAGED_RESPONSE_HEADERS
)


def _parse_dial_exception(
    status_code: int,
    content: dict | str,
    headers: dict[str, str] | None = None,
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

        plain_headers = {
            key.decode(): value.decode()
            for key, value in headers.raw
            if key.decode().lower() not in _STRIPPED_RESPONSE_HEADERS
        }

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
            with contextlib.suppress(Exception):
                status_code = int(exc.code)

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
            dial_exception = to_dial_exception(e)
            _log.exception(
                f"Caught exception: {type(e).__module__}.{type(e).__name__}. "
                f"Converted to the DIAL exception: {dial_exception!r}"
            )
            raise dial_exception from e

    return wrapper
