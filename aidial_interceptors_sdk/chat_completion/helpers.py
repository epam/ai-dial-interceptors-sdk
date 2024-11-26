from typing import Awaitable, Callable, List, TypeVar, overload

from aidial_interceptors_sdk.utils.not_given import NOT_GIVEN, NotGiven

T = TypeVar("T")
P = TypeVar("P")


@overload
async def traverse_dict_value(
    path: P,
    d: dict,
    key: str,
    on_value: Callable[
        [P, T | NotGiven | None],
        Awaitable[T | NotGiven | None],
    ],
) -> dict: ...


@overload
async def traverse_dict_value(
    path: P,
    d: NotGiven,
    key: str,
    on_value: Callable[
        [P, T | NotGiven | None],
        Awaitable[T | NotGiven | None],
    ],
) -> NotGiven: ...


@overload
async def traverse_dict_value(
    path: P,
    d: None,
    key: str,
    on_value: Callable[
        [P, T | NotGiven | None],
        Awaitable[T | NotGiven | None],
    ],
) -> None: ...


async def traverse_dict_value(
    path: P,
    d: dict | NotGiven | None,
    key: str,
    on_value: Callable[
        [P, T | NotGiven | None],
        Awaitable[T | NotGiven | None],
    ],
) -> dict | NotGiven | None:
    if d is None or isinstance(d, NotGiven):
        return d

    old_value = d.get(key, NOT_GIVEN)
    new_value = await on_value(path, old_value)

    if new_value is NOT_GIVEN:
        if old_value is NOT_GIVEN:
            return d
        else:
            return {k: v for k, v in d.items() if k != key}
    else:
        return {**d, key: new_value}


@overload
async def traverse_required_dict_value(
    path: P,
    d: None,
    key: str,
    on_value: Callable[[P, T], Awaitable[T]],
) -> None: ...


@overload
async def traverse_required_dict_value(
    path: P,
    d: NotGiven,
    key: str,
    on_value: Callable[[P, T], Awaitable[T]],
) -> NotGiven: ...


@overload
async def traverse_required_dict_value(
    path: P,
    d: dict,
    key: str,
    on_value: Callable[[P, T], Awaitable[T]],
) -> dict: ...


async def traverse_required_dict_value(
    path: P,
    d: dict | NotGiven | None,
    key: str,
    on_value: Callable[[P, T], Awaitable[T]],
) -> dict | NotGiven | None:
    if d is None or isinstance(d, NotGiven):
        return d

    old_value = d.get(key)

    if old_value is None:
        raise ValueError(f"Missing required key {key!r} in a dictionary")

    new_value = await on_value(path, old_value)
    return {**d, key: new_value}


@overload
async def traverse_list(
    create_elem_path: Callable[[int], P],
    lst: NotGiven,
    on_elem: Callable[[P, T], Awaitable[List[T] | T]],
) -> NotGiven: ...


@overload
async def traverse_list(
    create_elem_path: Callable[[int], P],
    lst: None,
    on_elem: Callable[[P, T], Awaitable[List[T] | T]],
) -> None: ...


@overload
async def traverse_list(
    create_elem_path: Callable[[int], P],
    lst: List[T],
    on_elem: Callable[[P, T], Awaitable[List[T] | T]],
) -> List[T]: ...


async def traverse_list(
    create_elem_path: Callable[[int], P],
    lst: List[T] | NotGiven | None,
    on_elem: Callable[[P, T], Awaitable[List[T] | T]],
) -> List[T] | NotGiven | None:
    if lst is None or isinstance(lst, NotGiven):
        return lst

    ret: List[T] = []
    for idx, elem in enumerate(lst):
        idx = elem.get("index", idx) if isinstance(elem, dict) else idx
        elem = await on_elem(create_elem_path(idx), elem)
        if isinstance(elem, list):
            ret.extend(elem)
        else:
            ret.append(elem)

    return ret
