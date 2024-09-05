import os
from typing import List, Optional


def get_env(name: str, err_msg: Optional[str] = None) -> str:
    if name in os.environ:
        val = os.environ.get(name)
        if val is not None:
            return val

    raise Exception(err_msg or f"{name} env variable is not set")


def get_env_list(name: str, default: List[str] = []) -> List[str]:
    value = os.getenv(name)
    if value is None:
        return default
    return value.split(",")
