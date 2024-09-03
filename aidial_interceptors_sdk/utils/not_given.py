from typing import Literal

from typing_extensions import override


class NotGiven:
    """
    A sentinel singleton class used to distinguish omitted keyword arguments
    from those passed in with the value None (which may have different behavior).

    Copied from https://github.com/openai/openai-python/blob/40f4cdb52a7494472c32e26c70f54bb41bb2bb57/src/openai/_types.py#L107-L133
    """

    def __bool__(self) -> Literal[False]:
        return False

    @override
    def __repr__(self) -> str:
        return "NOT_GIVEN"


NOT_GIVEN = NotGiven()
