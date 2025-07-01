import logging
from typing import Callable

_log = logging.getLogger(__name__)


def fail_safe(func: Callable[..., str]) -> Callable[..., str]:
    def _wrapper(*args, **kwargs) -> str:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            msg = f"Error executing {func.__name__}: {str(e)}"
            _log.warning(msg)
            return msg

    return _wrapper
