"""Sample data built from the OpenAPI snapshot, so mocked responses have the API's real shapes."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any, Dict, List, cast

SPEC_PATH = Path(__file__).resolve().parent.parent / "openapi" / "openapi.json"


@cache
def spec() -> Dict[str, Any]:
    return cast(Dict[str, Any], json.loads(SPEC_PATH.read_text()))


def operation(method: str, path: str) -> Dict[str, Any]:
    return cast(Dict[str, Any], spec()["paths"][path][method.lower()])


def sample(schema: Dict[str, Any], depth: int = 0) -> Any:
    """A deterministic value matching ``schema``."""
    if "$ref" in schema:
        return sample(spec()["components"]["schemas"][schema["$ref"].split("/")[-1]], depth)
    if "allOf" in schema:
        out: Dict[str, Any] = {}
        for part in schema["allOf"]:
            value = sample(part, depth)
            if isinstance(value, dict):
                out.update(cast(Dict[str, Any], value))
        return out
    for key in ("oneOf", "anyOf"):
        if key in schema:
            return sample(schema[key][0], depth)
    if "enum" in schema:
        return next((v for v in schema["enum"] if v is not None), None)
    if "const" in schema:
        return schema["const"]
    kind: Any = schema.get("type")
    if isinstance(kind, list):
        kind = next((k for k in cast(List[str], kind) if k != "null"), "null")
    if kind is None and "properties" in schema:
        kind = "object"
    if kind == "object":
        if depth > 6:
            return {}
        props = cast(Dict[str, Dict[str, Any]], schema.get("properties", {}))
        return {k: sample(v, depth + 1) for k, v in props.items()}
    if kind == "array":
        return [] if depth > 6 else [sample(schema.get("items", {}), depth + 1)]
    if kind == "string":
        fmt = schema.get("format")
        if fmt == "uuid":
            return "00000000-0000-4000-8000-000000000001"
        if fmt == "date-time":
            return "2026-11-18T15:00:00.000Z"
        return "sample"
    if kind == "integer":
        return 1
    if kind == "number":
        return 1.5
    if kind == "boolean":
        return True
    return None


def success_response(method: str, path: str) -> tuple[int, Any]:
    """The first 2xx status and a sample body for an operation."""
    for code, response in sorted(operation(method, path)["responses"].items()):
        if code.startswith("2"):
            content = response.get("content", {})
            if not content:
                return int(code), None
            media_type, media = next(iter(content.items()))
            if media_type != "application/json":
                return int(code), b"\x00binary"
            return int(code), sample(media.get("schema", {}))
    raise AssertionError(f"no 2xx response for {method} {path}")
