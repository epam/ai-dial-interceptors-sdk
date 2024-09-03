import json
import logging
from typing import Callable, Coroutine, TypeVar

_log = logging.getLogger(__name__)
_debug = _log.isEnabledFor(logging.DEBUG)

A = TypeVar("A")
B = TypeVar("B")


def debug_logging(
    title: str,
) -> Callable[
    [Callable[[A], Coroutine[None, None, B]]],
    Callable[[A], Coroutine[None, None, B]],
]:
    def decorator(
        fn: Callable[[A], Coroutine[None, None, B]]
    ) -> Callable[[A], Coroutine[None, None, B]]:
        if not _debug:
            return fn

        async def _fn(a: A) -> B:
            _log.debug(f"{title} old: {json.dumps(a)}")
            b = await fn(a)
            _log.debug(f"{title} new: {json.dumps(b)}")
            return b

        return _fn

    return decorator
