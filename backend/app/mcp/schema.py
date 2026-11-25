"""JSON Schemas of tool inputs from the OpenAPI document: ``$ref`` inlined, titles dropped.

MCP clients differ in how well they follow ``$ref``; inlined schemas work everywhere. Titles
repeat the property names and only cost the model tokens.
"""

from typing import Any

_SCHEMA_LISTS = ("anyOf", "oneOf", "allOf", "prefixItems")
_REF_PREFIX = "#/components/schemas/"


class SchemaResolver:
    def __init__(self, components: dict[str, Any]) -> None:
        self.components = components

    def resolve(self, schema: dict[str, Any]) -> dict[str, Any]:
        return self._walk(schema, ())

    def _walk(self, schema: Any, seen: tuple[str, ...]) -> Any:
        if not isinstance(schema, dict):
            return schema
        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith(_REF_PREFIX):
            name = ref.removeprefix(_REF_PREFIX)
            if name in seen:  # a recursive model: stop here
                return {"type": "object"}
            merged = {**self.components.get(name, {}), **{k: v for k, v in schema.items() if k != "$ref"}}
            return self._walk(merged, (*seen, name))
        out: dict[str, Any] = {}
        for key, value in schema.items():
            if key in ("title", "discriminator"):
                continue
            if key == "properties" and isinstance(value, dict):
                out[key] = {name: self._walk(sub, seen) for name, sub in value.items()}
            elif key in ("items", "additionalProperties", "not") and isinstance(value, dict):
                out[key] = self._walk(value, seen)
            elif key in _SCHEMA_LISTS and isinstance(value, list):
                out[key] = [self._walk(sub, seen) for sub in value]
            else:
                out[key] = value
        return out


def is_file(schema: dict[str, Any]) -> bool:
    """An upload field of a multipart body (OpenAPI 3.0 and 3.1 spellings)."""
    return schema.get("format") == "binary" or "contentMediaType" in schema
