"""Load the MoC Contract JSON Schemas and build a validation registry.

Schemas live in ``schemas/*.json`` and cross-reference each other by ``$id``
(``https://schemas.agent-matrix.org/moc/v1/<name>.json``). This module loads them
all into a ``referencing`` registry so a ``Draft202012Validator`` can resolve the
``$ref``s between objects.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict

SCHEMA_DIR = Path(__file__).parent / "schemas"
BASE_URI = "https://schemas.agent-matrix.org/moc/v1/"


@lru_cache(maxsize=1)
def all_schemas() -> Dict[str, dict]:
    """Map schema name (file stem) -> parsed schema dict."""
    return {p.stem: json.loads(p.read_text()) for p in sorted(SCHEMA_DIR.glob("*.json"))}


def schema_uri(name: str) -> str:
    return f"{BASE_URI}{name}.json"


@lru_cache(maxsize=1)
def registry():
    """A ``referencing`` registry containing every schema, keyed by ``$id``."""
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012

    resources = []
    for name, schema in all_schemas().items():
        uri = schema.get("$id", schema_uri(name))
        resources.append((uri, Resource.from_contents(schema, default_specification=DRAFT202012)))
    return Registry().with_resources(resources)


def validator_for(name: str):
    """Return a Draft 2020-12 validator for the named schema."""
    from jsonschema import Draft202012Validator

    schemas = all_schemas()
    if name not in schemas:
        raise KeyError(f"unknown schema: {name!r}; have {sorted(schemas)}")
    return Draft202012Validator(schemas[name], registry=registry())


def validate(name: str, instance) -> list:
    """Validate ``instance`` against the named schema. Returns a list of human
    error strings (empty == valid)."""
    v = validator_for(name)
    return [f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}"
            for e in v.iter_errors(instance)]
