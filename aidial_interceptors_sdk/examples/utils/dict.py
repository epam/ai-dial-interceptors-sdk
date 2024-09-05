from typing import Any, Callable, List, TypeVar

Path = List[str | int]
PathLike = Path | str


def _parse_path(path: str) -> Path:
    ret: Path = []
    for segment in path.split("."):
        if not segment:
            raise ValueError("Invalid empty path segment.")
        if segment[0] == "!":
            ret.append(int(segment[1:]))
        else:
            ret.append(segment)

    return ret


def _to_path(path: Path | str) -> Path:
    if isinstance(path, str):
        return _parse_path(path)
    else:
        return path


def _update_at_path(
    obj: Any,
    path: Path,
    acc_path: Path,
    fn: Callable[[Path, Any], Any],
    **kwargs: Any,
) -> Any:
    """
    Immutable modification of a nested value in a dictionary or list.

    If a dict key is missing, then it's created, unless drill_down is False.
    If list/tuple index is missing, then an error is raised.
    Catch-all "*" index is supported for lists.
    """

    drill_down = kwargs.get("drill_down", False)
    strict = kwargs.get("strict", True)

    if path == []:
        return fn(acc_path, obj)

    key = path[0]
    rest = path[1:]

    if isinstance(obj, dict):
        value = obj.get(key, None)
        if value is None and not drill_down:
            return obj
        else:
            return {
                **obj,
                key: _update_at_path(
                    value, rest, acc_path + [key], fn, **kwargs
                ),
            }

    if isinstance(obj, list):
        if key == "*":
            indices = set(range(len(obj)))
        else:
            if isinstance(key, int):
                index = key
            elif strict:
                raise ValueError(f"Invalid list index: {key!r}")
            else:
                return obj

            if index < 0 or index >= len(obj) and strict:
                raise ValueError(
                    f"Invalid index ({index}) for a list of length {len(obj)}"
                )
            indices = {index}

        return [
            (
                _update_at_path(elem, rest, acc_path + [i], fn, **kwargs)
                if i in indices
                else elem
            )
            for i, elem in enumerate(obj)
        ]

    if isinstance(obj, tuple):
        if isinstance(key, int):
            index = key
        elif strict:
            raise ValueError(f"Invalid tuple index: {key!r}")
        else:
            return obj

        if index < 0 or index >= len(obj) and strict:
            raise ValueError(
                f"Invalid index ({index}) for a tuple of length {len(obj)}"
            )

        return tuple(
            (
                _update_at_path(elem, rest, acc_path + [i], fn, **kwargs)
                if i == index
                else elem
            )
            for i, elem in enumerate(obj)
        )

    if obj is None:
        if isinstance(key, int):
            if strict:
                raise ValueError("Cannot index into None")
            else:
                return obj
        else:
            if drill_down:
                return {
                    key: _update_at_path(
                        obj, rest, acc_path + [key], fn, **kwargs
                    )
                }
            else:
                return obj

    if strict:
        raise ValueError(
            f"Cannot get a value at path {path} in a scalar value of type {type(obj).__name__}"
        )
    else:
        return obj


def update_at_path(
    obj: Any, path: PathLike, fn: Callable[[Path, Any], Any], **kwargs
) -> Any:
    return _update_at_path(obj, _to_path(path), [], fn, **kwargs)


def set_at_path(obj: dict, path: PathLike, value: Any, **kwargs) -> dict:
    return update_at_path(obj, path, lambda path, _value: value, **kwargs)


T = TypeVar("T")


def get_at_path(obj: Any, path: PathLike) -> Any:
    values = collect_at_path(obj, path)
    return None if values == [] else values[-1]


def collect_at_path(obj: Any, path: PathLike) -> List[Any]:
    ret = []

    def fn(path, value):
        ret.append(value)
        return value

    update_at_path(obj, path, fn)
    return ret
