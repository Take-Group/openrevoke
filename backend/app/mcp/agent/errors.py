"""``ToolError``: its own module, so ``api.py`` and ``base.py`` do not import each other."""


class ToolError(Exception):
    """A message for the assistant: what went wrong and what to call instead."""
