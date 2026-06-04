"""MoC Contract v1 conformance (real QA layer, was a v1 placeholder skip).

Validates that (1) every JSON Schema is a valid Draft 2020-12 schema, (2) the
OpenAPI document covers the REST surface and only $refs existing schemas, and
(3) the reference matrix-context REST server passes the full executable
conformance suite (shape + behaviour). Requires the `conformance` extra
(jsonschema, PyYAML), which is included in `dev`.
"""
import pytest

pytest.importorskip("jsonschema")

from jsonschema import Draft202012Validator  # noqa: E402

from moc_contract import CONTRACT_VERSION, OBJECTS  # noqa: E402
from moc_contract.conformance import in_process_client, run  # noqa: E402
from moc_contract.loader import all_schemas, validate  # noqa: E402


def test_all_schemas_are_valid_draft202012():
    schemas = all_schemas()
    assert set(schemas) == set(OBJECTS)              # every declared object exists
    for name, schema in schemas.items():
        Draft202012Validator.check_schema(schema)    # raises if invalid
        assert schema["$id"].endswith(f"{name}.json")


def test_reference_server_is_moc_v1_compatible():
    report = run(in_process_client())
    failures = [(n, d) for n, ok, d in report.checks if not ok]
    assert report.ok, f"{report.failed} conformance failures: {failures}"
    assert report.passed >= 30


def test_contract_version_is_semver_one():
    assert CONTRACT_VERSION.split(".")[0] == "1"


def test_validate_rejects_malformed_objects():
    # A MemoryItem missing required fields must fail validation.
    assert validate("memory_item", {"id": "x"})            # errors -> truthy
    assert not validate("memory_item", {                   # complete -> no errors
        "id": "x", "content": "c", "expert": "semantic",
        "scope": "/", "importance": 0.5, "tags": []})


def test_openapi_covers_surface_and_refs_exist():
    yaml = pytest.importorskip("yaml")
    from pathlib import Path

    import moc_contract
    root = Path(moc_contract.__file__).parent
    spec = yaml.safe_load((root / "openapi.yaml").read_text())
    assert spec["openapi"].startswith("3.1")
    assert spec["info"]["version"] == CONTRACT_VERSION

    paths = set(spec["paths"])
    expected = {"/health", "/version", "/experts", "/scopes", "/items",
                "/items/{id}", "/remember", "/recall", "/pack", "/inspect",
                "/router/explain", "/forget"}
    assert expected <= paths

    # Every external $ref points at a schema file that exists.
    import json
    refs = set()

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "$ref" and isinstance(v, str) and v.startswith("./schemas/"):
                    refs.add(v)
                else:
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(spec)
    assert refs, "expected external schema $refs in openapi.yaml"
    for r in refs:
        target = root / r[2:]
        assert target.exists(), f"openapi $ref to missing schema: {r}"
        json.loads(target.read_text())   # and it parses
