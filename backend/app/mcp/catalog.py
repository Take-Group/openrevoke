"""MCP tools built from the FastAPI routes: one tool per API operation a token can reach.

Name = operation id (the endpoint function name), description = the endpoint's docstring, input =
path and query parameters plus the JSON body's fields, all in one flat object. Who may see a tool
comes from the route's dependencies: ``require_admin`` (admins), ``get_current_user`` (every
role), none (public, only ``policy.PUBLIC_ALLOWED``). Routes that need the panel cookie
(``get_current_session``: sign-in settings, API tokens) never become tools.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from fastapi.routing import iter_route_contexts

from app.api.auth_deps import get_current_session, get_current_user, require_admin
from app.mcp import policy
from app.mcp.schema import SchemaResolver, is_file

if TYPE_CHECKING:
    from fastapi import FastAPI
    from fastapi.dependencies.models import Dependant


class Access(StrEnum):
    ADMIN = "admin"
    USER = "user"
    PUBLIC = "public"


class BodyMode(StrEnum):
    NONE = "none"
    JSON_FIELDS = "json_fields"  # the body's fields sit next to the parameters
    JSON_BODY = "json_body"  # the body is one argument, ``body`` (not an object, or a name clash)
    MULTIPART = "multipart"  # file fields are text arguments


@dataclass(frozen=True)
class ToolSpec:
    name: str
    title: str
    description: str
    method: str
    path: str
    access: Access
    tag: str
    input_schema: dict[str, Any]
    path_params: tuple[str, ...] = ()
    query_params: tuple[str, ...] = ()
    body_mode: BodyMode = BodyMode.NONE
    body_fields: tuple[str, ...] = ()
    file_fields: tuple[str, ...] = ()
    destructive: bool = False

    @property
    def read_only(self) -> bool:
        return self.method == "GET"


def build_catalog(app: FastAPI) -> list[ToolSpec]:
    document = app.openapi()
    resolver = SchemaResolver(document.get("components", {}).get("schemas", {}))
    # Route contexts carry the dependencies of the routers a route is included in (require_admin).
    access_by_name = {
        route.name: _access(route.dependant)
        for route in iter_route_contexts(app.routes)
        if getattr(route, "dependant", None) is not None
    }
    specs: list[ToolSpec] = []
    for path, operations in document.get("paths", {}).items():
        for method, operation in operations.items():
            name = operation.get("operationId")
            access = access_by_name.get(name)
            if not name or access is None or not _is_tool(name, path, access):
                continue
            specs.append(_spec(name, method.upper(), path, operation, access, resolver))
    return sorted(specs, key=lambda spec: (spec.tag, spec.name))


def _is_tool(name: str, path: str, access: Access | None) -> bool:
    if not path.startswith("/api/") or name in policy.EXCLUDED:
        return False
    return access != Access.PUBLIC or name in policy.PUBLIC_ALLOWED


def _access(dependant: Dependant) -> Access | None:
    """None: the route needs the panel cookie and stays out of the MCP server."""
    calls = _calls(dependant)
    if require_admin in calls:
        return Access.ADMIN
    if get_current_user in calls:
        return Access.USER
    if get_current_session in calls:
        return None
    return Access.PUBLIC


def _calls(dependant: Dependant) -> set[Any]:
    found: set[Any] = set()
    for sub in dependant.dependencies:
        if sub.call is not None:
            found.add(sub.call)
        found |= _calls(sub)
    return found


def _spec(
    name: str, method: str, path: str, operation: dict[str, Any], access: Access, resolver: SchemaResolver
) -> ToolSpec:
    properties: dict[str, Any] = {}
    required: list[str] = []
    path_params: list[str] = []
    query_params: list[str] = []
    for parameter in operation.get("parameters", []):
        location = parameter.get("in")
        if location not in ("path", "query"):
            continue
        schema = resolver.resolve(parameter.get("schema", {}))
        if parameter.get("description"):
            schema["description"] = parameter["description"]
        properties[parameter["name"]] = schema
        if parameter.get("required"):
            required.append(parameter["name"])
        (path_params if location == "path" else query_params).append(parameter["name"])

    body_mode, body_fields, file_fields = _body(operation.get("requestBody"), resolver, properties, required)
    summary = operation.get("summary") or name.replace("_", " ").capitalize()
    tags = operation.get("tags") or [policy.DEFAULT_TAG]
    input_schema: dict[str, Any] = {"type": "object", "properties": properties, "additionalProperties": False}
    if required:
        input_schema["required"] = list(dict.fromkeys(required))
    return ToolSpec(
        name=name,
        title=summary,
        description=_description(operation, summary, method, path),
        method=method,
        path=path,
        access=access,
        tag=tags[0],
        input_schema=input_schema,
        path_params=tuple(path_params),
        query_params=tuple(query_params),
        body_mode=body_mode,
        body_fields=body_fields,
        file_fields=file_fields,
        destructive=method == "DELETE" or name in policy.DESTRUCTIVE,
    )


def _body(
    request_body: dict[str, Any] | None,
    resolver: SchemaResolver,
    properties: dict[str, Any],
    required: list[str],
) -> tuple[BodyMode, tuple[str, ...], tuple[str, ...]]:
    """Adds the body's arguments to ``properties`` and ``required``; returns how to send them."""
    if not request_body:
        return BodyMode.NONE, (), ()
    content = request_body.get("content", {})
    body_required = bool(request_body.get("required"))
    if "multipart/form-data" in content:
        schema = resolver.resolve(content["multipart/form-data"].get("schema", {}))
        files = []
        for field_name, sub in schema.get("properties", {}).items():
            if is_file(sub):
                files.append(field_name)
                sub = {"type": "string", "description": f"{sub.get('description', 'File')}. Pass the file's text."}
            properties[field_name] = sub
        required += schema.get("required", [])
        fields = tuple(schema.get("properties", {}))
        return BodyMode.MULTIPART, fields, tuple(files)
    schema = resolver.resolve(content.get("application/json", {}).get("schema", {}))
    fields = schema.get("properties")
    if schema.get("type") == "object" and fields and not set(fields) & set(properties):
        properties.update(fields)
        if body_required:
            required += schema.get("required", [])
        return BodyMode.JSON_FIELDS, tuple(fields), ()
    properties["body"] = schema
    if body_required:
        required.append("body")
    return BodyMode.JSON_BODY, ("body",), ()


def _description(operation: dict[str, Any], summary: str, method: str, path: str) -> str:
    text = (operation.get("description") or "").strip()
    return f"{summary}. {text}\n\n({method} {path})" if text else f"{summary}. ({method} {path})"
