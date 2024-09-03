from typing import Any, Callable

import pytest

from aidial_interceptors_sdk.utils.dict import (
    Path,
    PathLike,
    get_at_path,
    set_at_path,
    update_at_path,
)


class TestCase:
    __test__ = False

    def __init__(
        self,
        obj: Any,
        path: PathLike,
        fn: Callable[[Path, Any], Any],
        expected: Any,
        drill_down: bool = False,
        strict: bool = True,
    ):
        self.obj = obj
        self.path = path
        self.fn = fn
        self.drill_down = drill_down
        self.expected = expected
        self.strict = strict


@pytest.mark.parametrize(
    "case, expected_error_message",
    [
        (
            TestCase(
                obj={"a": 1},
                path="b",
                fn=lambda p, v: 2,
                drill_down=True,
                expected={"a": 1, "b": 2},
            ),
            None,
        ),
        (
            TestCase(
                obj={"a": 1},
                path="a",
                fn=lambda p, v: v + 1,
                drill_down=True,
                expected={"a": 2},
            ),
            None,
        ),
        (
            TestCase(
                obj=[1, 2, 3],
                path="!1",
                fn=lambda p, v: v * 2,
                drill_down=True,
                expected=[1, 4, 3],
            ),
            None,
        ),
        (
            TestCase(
                obj=[1, 2, 3],
                path="*",
                fn=lambda p, v: v * 2,
                drill_down=True,
                expected=[2, 4, 6],
            ),
            None,
        ),
        (
            TestCase(
                obj=(1, 2, 3),
                path="!1",
                fn=lambda p, v: v * 2,
                drill_down=True,
                expected=(1, 4, 3),
            ),
            None,
        ),
        (
            TestCase(
                obj={"a": {"b": 2}},
                path="a.b",
                fn=lambda p, v: v * 2,
                drill_down=True,
                expected={"a": {"b": 4}},
            ),
            None,
        ),
        (
            TestCase(
                obj={"a": {}},
                path="a.b",
                fn=lambda p, v: 3,
                drill_down=True,
                expected={"a": {"b": 3}},
            ),
            None,
        ),
        (
            TestCase(
                obj=[[1, 2], [3, 4]],
                path="!1.!0",
                fn=lambda p, v: v + 1,
                drill_down=True,
                expected=[[1, 2], [4, 4]],
            ),
            None,
        ),
        (
            TestCase(
                obj=None,
                path="a",
                fn=lambda p, v: 1,
                drill_down=True,
                expected={"a": 1},
            ),
            None,
        ),
        pytest.param(
            TestCase(
                obj=[1, 2],
                path="!2",
                fn=lambda p, v: v,
                drill_down=True,
                expected=None,
            ),
            "Invalid index (2) for a list of length 2",
        ),
        pytest.param(
            TestCase(
                obj=(1, 2),
                path="!2",
                fn=lambda p, v: v,
                drill_down=True,
                expected=None,
            ),
            "Invalid index (2) for a tuple of length 2",
        ),
        pytest.param(
            TestCase(
                obj=None,
                path="!0",
                fn=lambda p, v: v,
                drill_down=True,
                expected=None,
            ),
            "Cannot index into None",
        ),
        pytest.param(
            TestCase(
                obj=[{"a": 1}, [], 1, {}, None, {"b": 3}, {"a": 3, "b": 4}],
                path="*.a",
                fn=lambda p, v: 2 * v,
                drill_down=False,
                strict=False,
                expected=[
                    {"a": 2},
                    [],
                    1,
                    {},
                    None,
                    {"b": 3},
                    {"a": 6, "b": 4},
                ],
            ),
            None,
        ),
    ],
)
def test_modify_at_path(case: TestCase, expected_error_message: str | None):
    if expected_error_message is not None:
        with pytest.raises(ValueError) as exc_info:
            update_at_path(
                case.obj,
                case.path,
                case.fn,
                drill_down=case.drill_down,
                strict=case.strict,
            )
        assert str(exc_info.value) == expected_error_message
    else:
        assert (
            update_at_path(
                case.obj,
                case.path,
                case.fn,
                drill_down=case.drill_down,
                strict=case.strict,
            )
            == case.expected
        )


@pytest.mark.parametrize(
    "obj, path, value, expected",
    [
        ({"a": 1}, "a", 2, {"a": 2}),
        ({"a": 1}, "b", 3, {"a": 1, "b": 3}),
        ({"a": {"b": 2}}, "a.b", 4, {"a": {"b": 4}}),
        ([1, 2, 3], "!1", 4, [1, 4, 3]),
        ([1, 2, 3], "*", 5, [5, 5, 5]),
        ((1, 2, 3), "!1", 4, (1, 4, 3)),
        (None, "a", 1, {"a": 1}),
    ],
)
def test_set_at_path(obj, path, value, expected):
    assert (
        set_at_path(obj, path, value, drill_down=True, strict=False) == expected
    )


@pytest.mark.parametrize(
    "obj, path, expected, expected_error_message",
    [
        ({"a": 1}, "a", 1, None),
        ({"a": {"b": 2}}, "a.b", 2, None),
        ([1, 2, 3], "!1", 2, None),
        ((1, 2, 3), "!1", 2, None),
        ({"a": 1}, "b", None, None),
        (None, "a", None, None),
        (
            1.0,
            "a",
            None,
            "Cannot get a value at path ['a'] in a scalar value of type float",
        ),
        ([1.0], "a", None, "Invalid list index: 'a'"),
    ],
)
def test_get_at_path(obj, path, expected, expected_error_message):
    if expected_error_message is not None:
        with pytest.raises(ValueError) as exc_info:
            get_at_path(obj, path)
        assert str(exc_info.value) == expected_error_message
    else:
        assert get_at_path(obj, path) == expected
