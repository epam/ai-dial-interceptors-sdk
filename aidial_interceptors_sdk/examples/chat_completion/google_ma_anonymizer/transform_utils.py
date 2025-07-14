from typing import Any, Dict, List, Mapping, Sequence

from tabulate import tabulate


def transform_to_table(records: List[Dict[str, str]]) -> str:
    if not records:
        return "*(no findings)*"
    headers = list(records[0].keys())
    rows = [[rec.get(col, "") for col in headers] for rec in records]
    return tabulate(rows, headers=headers, tablefmt="github")


def transform_to_table_by_schema(
    rows: Sequence[Mapping[str, Any]], schema: Sequence[str]
) -> str:
    """Return a markdown table with a fixed column schema."""
    normalized: List[List[Any]] = [
        [row.get(col, "") for col in schema] for row in rows
    ]
    return tabulate(normalized, headers=schema, tablefmt="github")
