import inspect
from typing import Any, Callable, Coroutine, TypeVar

from aidial_sdk.exceptions import invalid_request_error

T = TypeVar("T")


async def call_with_extra_body(
    func: Callable[..., Coroutine[Any, Any, T]], arg: dict
) -> T:
    if _has_kwargs_argument(func):
        return await func(**arg)

    expected_args = set(inspect.signature(func).parameters.keys())
    actual_args = set(arg.keys())

    extra_args = actual_args - expected_args

    if extra_args and "extra_body" not in expected_args:
        raise invalid_request_error(
            f"Unrecognized request argument supplied: {extra_args}."
        )

    arg["extra_body"] = arg.get("extra_body") or {}

    for extra_arg in extra_args:
        arg["extra_body"][extra_arg] = arg[extra_arg]
        del arg[extra_arg]

    return await func(**arg)


def _has_kwargs_argument(func: Callable[..., Coroutine[Any, Any, Any]]) -> bool:
    """
    Determines if the given function accepts a variable keyword argument (**kwargs).
    """
    signature = inspect.signature(func)
    for param in signature.parameters.values():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            print(param)
            return True
    return False
