import re
from typing import Any, List

from aidial_sdk.pydantic_v1 import BaseModel


class MarkdownTable(BaseModel):
    title: str | None = None
    headers: List[Any]
    rows: List[List[Any]] = []

    def add_row(self, row: List[Any]) -> None:
        if len(row) != len(self.headers):
            raise ValueError(
                f"Number of headers ({len(self.headers)}) does not match number of cells in a row ({len(row)})"
            )
        self.rows.append(row)

    def add_rows(self, *rows: List[Any]) -> None:
        for row in rows:
            self.add_row(row)

    def is_empty(self) -> bool:
        return not self.rows

    def to_markdown(self) -> str:
        rows = [self.headers, ["---"] * len(self.headers), *self.rows]
        ret = "\n".join(
            f"|{'|'.join(map(escape_table_cell, row))}|" for row in rows
        )
        if self.title:
            ret = f"\n\n### {self.title}\n\n" + ret
        return ret

    def to_markdown_opt(self) -> str:
        if self.is_empty():
            return ""
        return self.to_markdown()


def escape_table_cell(value: Any) -> str:
    return _escape_new_lines(_escape_code_blocks(str(value)))


def _escape_new_lines(text: str) -> str:
    return text.replace("\n", "<br>")


def _escape_code_blocks(text: str) -> str:
    in_code_block = False
    ret = []

    open_regexp = re.compile(r"^```([^\s`]+)?\s*$")
    close_regexp = re.compile(r"^```\s*$")

    for line in text.splitlines(keepends=True):
        if open_regexp.match(line) and not in_code_block:
            in_code_block = True
            ret.append("<pre>")
        elif close_regexp.match(line) and in_code_block:
            in_code_block = False
            ret.append("</pre>")
        else:
            ret.append(line)

    return "".join(ret)
