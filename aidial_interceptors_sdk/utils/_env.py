import logging
import os
from collections.abc import Callable
from typing import TypeVar

_log = logging.getLogger(__name__)


def get_env(name: str, err_msg: str | None = None) -> str:
    if (val := os.getenv(name)) is not None:
        return val

    raise Exception(err_msg or f"{name} env variable is not set")


def get_env_list(name: str, default: list[str] | None = None) -> list[str]:
    if (value := os.getenv(name)) is None:
        return default or []
    return value.split(",")


_T = TypeVar("_T")


def get_envs(names: list[str], parser: Callable[[str], _T], default: _T) -> _T:
    for name in names:
        if os.getenv(name) is not None:
            if name != names[-1]:
                _log.warning(
                    f"The environment variable {name!r} is deprecated. "
                    f"Use {names[-1]!r} instead."
                )
            return parser(name)
    return default
