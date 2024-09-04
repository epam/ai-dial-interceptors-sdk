import re
from collections import defaultdict
from typing import Dict, List, Optional

from aidial_sdk.pydantic_v1 import BaseModel
from spacy import load

from aidial_interceptors_sdk.examples.utils.markdown import MarkdownTable

_PIPELINE = load("en_core_web_sm")

DEFAULT_LABELS_TO_REDACT = [
    "PERSON",
    "ORG",
    "GPE",  # Geo-political entity
    "PRODUCT",
]


class Replacement(BaseModel):
    entity_type: str
    idx: int

    def print(self):
        return f"[{self.entity_type}-{self.idx}]"

    @classmethod
    def parse(cls, text: str) -> Optional["Replacement"]:
        regexp = r"\[(\w+)-(\d+)\]"
        match = re.match(regexp, text)
        if match:
            return cls(entity_type=match.group(1), idx=int(match.group(2)))
        return None


class SpacyAnonymizer(BaseModel):
    labels_to_redact: List[str] = DEFAULT_LABELS_TO_REDACT

    replacements: Dict[str, str] = {}
    """
    Mapping from original text to anonymized text, e.g.
    {"John Doe": "[PERSON-1]"}
    """

    types: Dict[str, int] = defaultdict(int)
    """
    Counting the number of replacements for each type, e.g.
    {"PERSON": 2, "ORG": 1}
    """

    def _get_replacement(self, text: str, text_type: str) -> str:
        if text not in self.replacements:
            self.types[text_type] += 1
            text_idx = self.types[text_type]
            self.replacements[text] = f"[{text_type}-{text_idx}]"

        return self.replacements[text]

    def _is_replacement(self, text: str, start: int, end: int) -> bool:
        return bool(
            Replacement.parse(text[start:end])
            or Replacement.parse(
                text[max(0, start - 1) : min(end + 1, len(text))]
            )
        )

    def anonymize(self, text: str) -> str:
        doc = _PIPELINE(text)
        redacted = []
        idx = 0

        for ent in doc.ents:
            redacted.append(doc.text[idx : ent.start_char])
            if (
                ent.label_ in self.labels_to_redact
                and not self._is_replacement(
                    doc.text, ent.start_char, ent.end_char
                )
            ):
                redacted += self._get_replacement(ent.text, ent.label_)
            else:
                redacted.append(doc.text[ent.start_char : ent.end_char])
            idx = ent.end_char

        redacted.append(doc.text[idx:])

        return "".join(redacted)

    def is_empty(self) -> bool:
        return not bool(self.replacements)

    def replacements_to_markdown_table(self) -> str:
        table = MarkdownTable(
            title="Anonymized entities",
            headers=["Original", "Anonymized"],
        )
        for k, v in self.replacements.items():
            table.add_row([k, v])
        return table.to_markdown()

    def highlight_anonymized_entities(self, text: str) -> str:
        for v in self.replacements.values():
            text = text.replace(v, f"**{v}**")
        return text

    def deanonymize(self, text: str) -> str:
        for k, v in self.replacements.items():
            text = text.replace(v, k)
            # For cases when the model doesn't respect brackets
            text = text.replace(v[1:-1], k)
        return text
