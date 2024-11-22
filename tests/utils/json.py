from typing import Any, Callable

Check = Callable[[str, Any], None]


def _print_type(ty: type) -> str:
    return f"{ty.__module__}.{ty.__name__}"


def has_type(ty: type) -> Check:
    def _check(path: str, value: Any):
        assert isinstance(
            value, ty
        ), f"The value is not of the {_print_type(ty)!r} type: {value!r}"

    return _check


def memorize(check: Check) -> Check:
    first_value = sentinel = object()
    first_path = None

    def _check(path: str, value: Any) -> None:
        check(path, value)

        nonlocal first_value, first_path
        if first_value is sentinel:
            first_value = value
            first_path = path
        else:
            assert (
                first_value == value
            ), f"The first value and the given value isn't the same: {first_value!r} @ {first_path!r} != {value!r} @ {path!r}"

    return _check


class MatchingException(Exception):
    path: str
    msg: str

    def __init__(self, path: str, msg: str):
        super().__init__(msg)
        self.path = path
        self.msg = msg

    def __str__(self) -> str:
        return f"{self.path}: {self.msg}"


def _match_objects(path: str, actual: Any, expected: Any) -> None:
    try:
        if isinstance(expected, dict):
            assert isinstance(
                actual, dict
            ), f"The actual value is not a dict: {_print_type(type(actual))!r}"
            assert (e_keys := list(sorted(expected.keys()))) == (
                a_keys := list(sorted(actual.keys()))
            ), f"The expected keys are not matching with actual keys: {e_keys} != {a_keys}"

            for k, v in expected.items():
                _match_objects(f"{path}.{k}", actual[k], v)

        elif isinstance(expected, tuple):
            assert isinstance(
                actual, tuple
            ), f"The actual value is not a tuple: {_print_type(type(actual))}"
            assert (e_len := len(expected)) == (
                a_len := len(actual)
            ), f"The expected length is not matching with actual length: {e_len} != {a_len}"

            for i in range(len(expected)):
                _match_objects(f"{path}[{i}]", actual[i], expected[i])

        elif isinstance(expected, list):
            assert isinstance(
                actual, list
            ), f"The actual value is not a list: {_print_type(type(actual))}"

            assert (e_len := len(expected)) == (
                a_len := len(actual)
            ), f"The expected length is not matching with actual length: {e_len} != {a_len}"

            for i in range(len(expected)):
                _match_objects(f"{path}[{i}]", actual[i], expected[i])

        elif callable(expected):
            expected(path, actual)

        else:
            assert (
                expected == actual
            ), f"The expected value is mismatching the actual value: {actual!r} != {expected!r}"

    except AssertionError as e:
        raise MatchingException(path=path, msg=str(e)[:100]) from e


def match_objects(actual: Any, expected: Any) -> None:
    _match_objects("actual", actual, expected)
