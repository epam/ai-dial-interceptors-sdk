import logging
from functools import wraps

import openai
from aidial_sdk.exceptions import HTTPException as DialException
from aidial_sdk.exceptions import internal_server_error
from fastapi.responses import Response

_log = logging.getLogger(__name__)


class EarlyStreamExit(Exception):
    """
    Thrown when one needs to end the stream prematurely.
    """


def to_dial_exception(e: Exception) -> Exception:
    """
    Converting certain interceptor-specific exceptions into DialException.

    The rest of the exceptions will be handled by the DIAL SDK.
    """

    if isinstance(e, openai.APIStatusError):
        r = e.response
        # FIXME: the headers aren't propagated,
        # so we may miss something useful like Retry-After.
        return DialException(r.text, r.status_code)

    if isinstance(e, openai.APITimeoutError):
        return DialException("Request timed out", 504, "timeout")

    if isinstance(e, openai.APIConnectionError):
        return DialException(
            "Error communicating with OpenAI", 502, "connection"
        )

    return e


def to_error_response(e: Exception) -> Response:
    if isinstance(e, DialException):
        return e.to_fastapi_response()
    else:
        return internal_server_error(str(e)).to_fastapi_response()


def dial_exception_decorator_response(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            _log.exception(
                f"caught exception: {type(e).__module__}.{type(e).__name__}"
            )

            dial_exception = to_dial_exception(e)
            error_response = to_error_response(dial_exception)
            _log.debug(f"error response: {error_response}")
            return error_response

    return wrapper


def dial_exception_decorator(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            _log.exception(
                f"caught exception: {type(e).__module__}.{type(e).__name__}"
            )
            raise to_dial_exception(e) from e

    return wrapper
