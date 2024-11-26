import json
import logging
from typing import Awaitable, Callable, TypeVar

_log = logging.getLogger(__name__)


def _debug():
    return _log.isEnabledFor(logging.DEBUG)


_A = TypeVar("_A")
_B = TypeVar("_B")


def debug_logging(
    title: str,
) -> Callable[
    [Callable[[_A], Awaitable[_B]]],
    Callable[[_A], Awaitable[_B]],
]:
    def decorator(
        fn: Callable[[_A], Awaitable[_B]]
    ) -> Callable[[_A], Awaitable[_B]]:
        if not _debug():
            return fn

        async def _fn(a: _A) -> _B:
            _log.debug(f"{title} old: {json.dumps(a)}")
            b = await fn(a)
            _log.debug(f"{title} new: {json.dumps(b)}")
            return b

        return _fn

    return decorator
