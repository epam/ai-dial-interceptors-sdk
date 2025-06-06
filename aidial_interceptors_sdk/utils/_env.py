import os
from typing import List, Optional


def get_env(name: str, err_msg: Optional[str] = None) -> str:
    if (val := os.getenv(name)) is not None:
        return val

    raise Exception(err_msg or f"{name} env variable is not set")


def get_env_list(name: str, default: List[str] | None = None) -> List[str]:
    if (value := os.getenv(name)) is None:
        return default or []
    return value.split(",")
