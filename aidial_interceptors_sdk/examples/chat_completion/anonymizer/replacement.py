from __future__ import annotations

import logging
import re
from typing import List

from aidial_sdk.pydantic_v1 import BaseModel

from .replacements import Replacements

_log = logging.getLogger(__name__)


class Replacement(BaseModel):
    entity_type: str
    idx: int

    def print(self):
        return f"[{self.entity_type}-{self.idx}]"

    @classmethod
    def parse(cls, text: str) -> Replacement | None:
        regexp = r"\[(\w+)-(\d+)\]"
        match = re.match(regexp, text)
        if match:
            return cls(entity_type=match.group(1), idx=int(match.group(2)))
        return None


def parse_anonymized_string(entities: List[str], s: str) -> List[str | int]:
    ret = []

    def _append(x: str | int):
        if isinstance(x, int) or (isinstance(x, str) and x):
            ret.append(x)

    i = 0
    n = len(s)
    last_match = 0

    while i < n:
        found = False
        if s[i] == "[":
            for j, e in enumerate(entities):
                if s[i + 1 : i + len(e) + 2] == e + "]":
                    _append(s[last_match:i])
                    _append(j)
                    i += len(e) + 2
                    last_match = i
                    found = True
                    break

        if not found:
            i += 1

    _append(s[last_match:])
    return ret


def create_indexed_replacements(
    replacements: Replacements,
    entities: List[str],
    original: str,
    anonymized: str,
) -> Replacements | None:
    anonymized_parsed = parse_anonymized_string(entities, anonymized)

    entity_indices = []
    regexp = ""

    for segment in anonymized_parsed:
        if isinstance(segment, int):
            regexp += "(.*?)"
            entity_indices.append(segment)
        else:
            regexp += re.escape(segment)

    match = re.fullmatch(regexp, original)
    if not match:
        _log.debug("Replacement parsing was unsuccessful")
        return None

    groups = match.groups()
    if len(groups) != len(entity_indices):
        _log.debug(
            f"Number of group matches ({len(groups)}) doesn't "
            f"match the expected number ({len(entity_indices)})"
        )
        return None

    for original_text, entity_index in zip(groups, entity_indices):
        replacements.get_replacement(entities[entity_index], original_text)

    return replacements
