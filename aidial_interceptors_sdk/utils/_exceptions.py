import contextlib
import functools
import logging

from aidial_sdk.exceptions import HTTPException as DialException
from openai import APIConnectionError, APIError, APIStatusError, APITimeoutError

_log = logging.getLogger(__name__)

# Do not copy hop-by-hop / framing headers onto the FastAPI JSON error.
# JSONResponse sets a new Content-Length; emitting that together with a
# copied Transfer-Encoding violates RFC 9112 §6.2:
#   "A sender MUST NOT send a Content-Length header field in any
#    message that contains a Transfer-Encoding header field."
# Connection / Keep-Alive / TE / Trailer / Upgrade / Transfer-Encoding
# are hop-by-hop. RFC 9110 §7.6.1:
#   "intermediaries SHOULD remove or replace fields that are known to
#    require removal before forwarding ... This includes but is not
#    limited to: ... Keep-Alive ... TE ... Transfer-Encoding ...
#    Upgrade"
# Content-Length / Content-Encoding are end-to-end but stale here
# (new JSON body, not the upstream encoding); listed so they cannot
# leak back via headers.raw after the dels below.
_HOP_BY_HOP_HEADERS = frozenset(
    {
        "content-length",
        "content-encoding",
        "transfer-encoding",
        "connection",
        "keep-alive",
        "te",
        "trailer",
        "upgrade",
    }
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

        plain_headers = {
            key.decode(): value.decode()
            for key, value in headers.raw
            if key.decode().lower() not in _HOP_BY_HOP_HEADERS
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
