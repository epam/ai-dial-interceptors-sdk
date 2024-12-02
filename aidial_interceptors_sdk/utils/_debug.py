import functools
import json
import logging
from typing import Awaitable, Callable, TypeVar

_log = logging.getLogger(__name__)


_A = TypeVar("_A")
_B = TypeVar("_B")


def debug_logging(
    title: str,
) -> Callable[
    [Callable[[_A], Awaitable[_B]]],
    Callable[[_A], Awaitable[_B]],
]:
    def decorator(
        func: Callable[[_A], Awaitable[_B]]
    ) -> Callable[[_A], Awaitable[_B]]:
        if not _log.isEnabledFor(logging.DEBUG):
            return func

        @functools.wraps(func)
        async def wrapper(a: _A) -> _B:
            _log.debug(f"{title} old: {json.dumps(a)}")
            b = await func(a)
            _log.debug(f"{title} new: {json.dumps(b)}")
            return b

        return wrapper

    return decorator
