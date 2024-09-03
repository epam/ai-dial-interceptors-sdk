from typing import Dict, Generic, Hashable, Set, TypeVar

from aidial_sdk.pydantic_v1 import BaseModel

_Index = TypeVar("_Index", bound=Hashable)


class IndexMapper(BaseModel, Generic[_Index]):
    """
    Used to maintain consistent mapping between indexed values in the incoming and outgoing streams, given that outgoing stream may include additional elements at fixed indices.
    """

    migrated: Dict[_Index, int] = {}
    used_indices: Set[int] = set()

    fresh_index: int = 0

    def reserve(self, index: int | None = None) -> int:
        if index is None:
            return self._get_fresh_index()

        if index in self.used_indices:
            raise ValueError(f"Index {index} is already taken")

        self.used_indices.add(index)
        return index

    def __call__(self, index: _Index) -> int:
        if index not in self.migrated:
            self.migrated[index] = self._get_fresh_index()
        return self.migrated[index]

    def _get_fresh_index(self) -> int:
        while self.fresh_index in self.used_indices:
            self.fresh_index += 1
        self.used_indices.add(self.fresh_index)
        return self.fresh_index
