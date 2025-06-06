from abc import ABC, abstractmethod

from .replacements import Replacements


class Anonymizer(ABC):
    @abstractmethod
    def collect_replacements(
        self, text: str, *, replacements: Replacements | None = None
    ) -> Replacements:
        pass
