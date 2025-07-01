from collections import defaultdict
from typing import Dict

from pydantic import BaseModel

from aidial_interceptors_sdk.examples.utils.markdown import MarkdownTable


class Replacements(BaseModel):
    replacements: Dict[str, str] = {}
    """
    Map from an original value to its anonymized replacement in a text
    """

    indices: Dict[str, int] = defaultdict(int)

    def get_replacement(self, entity: str, original_text: str) -> str:
        if original_text not in self.replacements:
            self.indices[entity] += 1
            index = self.indices[entity]
            self.replacements[original_text] = f"[{entity}-{index}]"

        return self.replacements[original_text]

    def is_empty(self) -> bool:
        return not bool(self.replacements)

    def to_markdown_table(self) -> str:
        table = MarkdownTable(
            title="Anonymized entities", headers=["Original", "Anonymized"]
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

    def anonymize(self, text: str) -> str:
        for k, v in self.replacements.items():
            text = text.replace(k, v)
        return text
