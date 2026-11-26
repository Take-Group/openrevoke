"""Cells of CSV exports that people open in a spreadsheet."""


def safe_cell(value: str | None) -> str:
    """Every cell: names, roles and notes come from people, syncs and the Slack model. A leading
    = + - @ (or a tab or carriage return before one) would run as a formula in a spreadsheet."""
    text = value or ""
    # Spreadsheets skip leading spaces and line breaks before they look for a formula.
    first = text.lstrip(" \n")[:1]
    return f"'{text}" if first in ("=", "+", "-", "@", "\t", "\r") or text[:1] in ("\t", "\r") else text
