"""Cells of CSV exports that people open in a spreadsheet."""


def safe_cell(value: str | None) -> str:
    """Every cell: names, roles and notes come from people, syncs and the Slack model. A leading
    = + - @ (or a tab or carriage return before one) would run as a formula in a spreadsheet."""
    text = value or ""
    return f"'{text}" if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text
