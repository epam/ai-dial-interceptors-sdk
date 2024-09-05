import logging
from functools import wraps

import openai
from aidial_sdk.exceptions import HTTPException as DialException

_log = logging.getLogger(__name__)


def _to_dial_exception(e: Exception) -> Exception:
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


def dial_exception_decorator(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            _log.exception(
                f"caught exception: {type(e).__module__}.{type(e).__name__}"
            )
            raise _to_dial_exception(e) from e

    return wrapper
