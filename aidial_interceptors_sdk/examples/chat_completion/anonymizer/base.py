from abc import ABC, abstractmethod

from .replacements import Replacements


class Anonymizer(ABC):
    @abstractmethod
    async def collect_replacements(
        self, text: str, *, replacements: Replacements | None = None
    ) -> Replacements:
        pass
