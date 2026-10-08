"""Contract tests for the word authoring POC (ADR-A118, plan WA1).

Validates every JSON Schema under ``contracts/authoring`` and the two authoring event schemas
under ``contracts/events``, the OpenAPI document, the three templates and samples, and the
fixtures, against the rules in docs/developer/plans/word-authoring-poc.md section "WA1".
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterator

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO = Path(__file__).resolve().parents[2]
CONTRACTS = REPO / "contracts"
AUTHORING = CONTRACTS / "authoring"
EVENTS = CONTRACTS / "events"
OPENAPI_FILE = CONTRACTS / "openapi" / "authoring-service.openapi.json"
TEMPLATES_DIR = AUTHORING / "templates"
SAMPLES_DIR = AUTHORING / "samples"
VALID_FIXTURES_DIR = AUTHORING / "fixtures" / "valid"
INVALID_FIXTURES_DIR = AUTHORING / "fixtures" / "invalid"

SCHEMA_PATTERN = re.compile(r"^https://json-schema\.org/draft/2020-12/schema$")
AUTHORING_ID_PATTERN = re.compile(r"^https://schemas\.nebularis\.org/lattice/authoring/[a-z-]+/0\.1\.0$")
EVENTS_ID_PATTERN = re.compile(r"^https://schemas\.nebularis\.org/lattice/events/[a-z-]+/0\.1\.0$")

UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
KEY_PATTERN = re.compile(r"^[a-z][a-z0-9-]{0,39}$")

EXPECTED_ROUTES = {
    ("get", "/api/health"),
    ("get", "/api/templates"),
    ("get", "/api/templates/{templateId}"),
    ("get", "/api/samples"),
    ("get", "/api/samples/{sampleId}"),
    ("get", "/api/documents/{documentId}"),
    ("put", "/api/documents/{documentId}/snapshot"),
    ("get", "/api/jobs/{jobId}"),
    ("get", "/api/documents/{documentId}/revisions/{revision}/analysis"),
    ("get", "/api/documents/{documentId}/revisions/{revision}/graph/{kind}"),
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _schema_files() -> list[Path]:
    return sorted(AUTHORING.glob("*.schema.json")) + [
        EVENTS / "wording-analysis-request.schema.json",
        EVENTS / "wording-analysis-result.schema.json",
    ]


def _schema_name(path: Path) -> str:
    return path.name[: -len(".schema.json")]


def _schemas() -> dict[str, dict]:
    return {_schema_name(path): _load(path) for path in _schema_files()}


def _registry() -> Registry:
    resources = [(schema["$id"], Resource.from_contents(schema)) for schema in _schemas().values()]
    return Registry().with_resources(resources)


def _validator(name: str, schema: dict, registry: Registry) -> Draft202012Validator:
    return Draft202012Validator(schema, registry=registry)


def _walk(node: Any) -> Iterator[Any]:
    """Yield every dict or list found anywhere within ``node``, including ``node`` itself."""
    yield node
    if isinstance(node, dict):
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk(item)


def _find_refs(node: Any) -> Iterator[str]:
    for value in _walk(node):
        if isinstance(value, dict) and "$ref" in value and isinstance(value["$ref"], str):
            yield value["$ref"]


def _object_schemas(schema: dict) -> Iterator[tuple[str, dict]]:
    """Yield (location, fragment) for the top-level schema and each ``$defs`` entry that is an object schema."""
    if schema.get("type") == "object":
        yield ("<top level>", schema)
    for def_name, fragment in schema.get("$defs", {}).items():
        if isinstance(fragment, dict) and fragment.get("type") == "object":
            yield (f"$defs/{def_name}", fragment)


# --- AC-01: schema version and $id ------------------------------------------------------------


def test_every_schema_has_the_2020_12_schema_and_a_matching_id():
    for path in _schema_files():
        schema = _load(path)
        assert SCHEMA_PATTERN.match(schema.get("$schema", "")), f"{path.name}: wrong $schema"
        name = _schema_name(path)
        expected_pattern = EVENTS_ID_PATTERN if path.parent == EVENTS else AUTHORING_ID_PATTERN
        assert expected_pattern.match(schema.get("$id", "")), f"{path.name}: wrong $id"
        assert schema["$id"].rsplit("/", 2)[1] == name, f"{path.name}: $id does not name the file"


# --- AC-02: additionalProperties false and required equal to properties ----------------------


def test_every_object_schema_closes_additional_properties_and_requires_every_property():
    for path in _schema_files():
        schema = _load(path)
        for location, fragment in _object_schemas(schema):
            properties = set(fragment.get("properties", {}).keys())
            required = set(fragment.get("required", []))
            assert fragment.get("additionalProperties") is False, f"{path.name} {location}: not closed"
            assert required == properties, f"{path.name} {location}: required {required} != properties {properties}"


# --- AC-03: no format keyword -----------------------------------------------------------------


def test_no_schema_uses_the_format_keyword():
    for path in _schema_files():
        schema = _load(path)
        for value in _walk(schema):
            if isinstance(value, dict):
                assert "format" not in value, f"{path.name}: uses format"


# --- AC-04: every $ref resolves, including its pointer ----------------------------------------


def test_every_ref_in_the_schemas_and_the_openapi_file_resolves():
    registry = _registry()
    for path in _schema_files():
        schema = _load(path)
        resolver = registry.resolver(base_uri=schema["$id"])
        for ref in _find_refs(schema):
            resolver.lookup(ref)  # raises if unresolved

    openapi = _load(OPENAPI_FILE)
    resolver = registry.resolver()
    for ref in _find_refs(openapi):
        resolver.lookup(ref)


# --- AC-05, AC-06, AC-07: fixtures validate as expected ----------------------------------------


def _fixture_cases() -> list[tuple[Path, bool]]:
    cases = [(path, True) for path in sorted(VALID_FIXTURES_DIR.glob("*.json"))]
    cases += [(path, False) for path in sorted(INVALID_FIXTURES_DIR.glob("*.json"))]
    return cases


@pytest.mark.parametrize("path,expected_valid", _fixture_cases(), ids=lambda value: getattr(value, "name", str(value)))
def test_each_fixture_validates_as_expected(path: Path, expected_valid: bool):
    prefix = path.stem.split("--", 1)[0]
    schemas = _schemas()
    assert prefix in schemas, f"{path.name}: no schema named {prefix!r}"
    registry = _registry()
    validator = _validator(prefix, schemas[prefix], registry)
    errors = list(validator.iter_errors(_load(path)))
    if expected_valid:
        assert errors == [], f"{path.name}: expected to validate, got {[e.message for e in errors]}"
    else:
        assert errors != [], f"{path.name}: expected to fail validation"


def test_zero_case_fixtures_fail_for_the_right_reason():
    schemas = _schemas()
    registry = _registry()

    zero_parts = _validator("document-snapshot", schemas["document-snapshot"], registry)
    errors = [e.message for e in zero_parts.iter_errors(_load(INVALID_FIXTURES_DIR / "document-snapshot--zero-parts.json"))]
    assert any("is too short" in message or "minItems" in message or "[]" in message for message in errors), errors

    no_term = _validator("document-snapshot", schemas["document-snapshot"], registry)
    errors = list(no_term.iter_errors(_load(INVALID_FIXTURES_DIR / "document-snapshot--definition-without-term.json")))
    assert errors != []


# --- AC-08: templates validate, keys unique ----------------------------------------------------


def _templates() -> dict[str, dict]:
    return {path.stem: _load(path) for path in sorted(TEMPLATES_DIR.glob("*.json"))}


def test_each_template_validates_and_has_unique_keys():
    registry = _registry()
    validator = _validator("authoring-template", _schemas()["authoring-template"], registry)
    for template_id, template in _templates().items():
        errors = list(validator.iter_errors(template))
        assert errors == [], f"{template_id}: {[e.message for e in errors]}"
        section_keys = [section["sectionKey"] for section in template["sections"]]
        assert len(section_keys) == len(set(section_keys)), f"{template_id}: duplicate section keys"
        variable_keys = [variable["variableKey"] for variable in template["variables"]]
        assert len(variable_keys) == len(set(variable_keys)), f"{template_id}: duplicate variable keys"


# --- AC-09: samples validate and cross-check against their template ---------------------------


def _samples() -> dict[str, dict]:
    return {path.stem: _load(path) for path in sorted(SAMPLES_DIR.glob("*.json"))}


def _literal_text(element: dict) -> str:
    return "".join(part["text"] for part in element["parts"] if part["kind"] == "literal")


def test_each_sample_validates_and_cross_checks_against_its_template():
    registry = _registry()
    validator = _validator("document-snapshot", _schemas()["document-snapshot"], registry)
    templates = _templates()

    for sample_id, sample in _samples().items():
        errors = list(validator.iter_errors(sample))
        assert errors == [], f"{sample_id}: {[e.message for e in errors]}"

        assert UUID_PATTERN.match(sample["documentId"]), f"{sample_id}: documentId is not a Uuid"
        assert KEY_PATTERN.match(sample["templateId"]), f"{sample_id}: templateId is not a Key"
        assert sample["templateId"] in templates, f"{sample_id}: names a template that does not exist"
        template = templates[sample["templateId"]]
        template_section_keys = {section["sectionKey"] for section in template["sections"]}

        element_ids = set()
        defined_terms_by_element: dict[str, str] = {}
        references: list[tuple[str, str]] = []
        for section in sample["sections"]:
            assert section["sectionKey"] in template_section_keys, (
                f"{sample_id}: section {section['sectionKey']} is not in its template"
            )
            for element in section["elements"]:
                element_ids.add(element["elementId"])
                if element["kind"] == "definition":
                    defined_terms_by_element[element["elementId"]] = element["definedTerm"]
                for part in element["parts"]:
                    if part["kind"] == "reference":
                        references.append((element["elementId"], part["targetElementId"]))

        for from_id, target_id in references:
            assert target_id in element_ids, f"{sample_id}: {from_id} references an element not in the sample"

        for element_id, term in defined_terms_by_element.items():
            element = next(
                e
                for section in sample["sections"]
                for e in section["elements"]
                if e["elementId"] == element_id
            )
            assert term in _literal_text(element), f"{sample_id}: definition {element_id} does not state its own term"


# --- AC-10: the OpenAPI file has exactly WA4's routes ------------------------------------------


def test_openapi_version_and_routes_match_wa4():
    openapi = _load(OPENAPI_FILE)
    assert openapi["openapi"] == "3.1.0"
    routes = {
        (method, path)
        for path, operations in openapi["paths"].items()
        for method in operations
    }
    assert routes == EXPECTED_ROUTES


# --- AC-11: the three samples together show every demo feature --------------------------------


def test_the_samples_together_show_every_demo_feature():
    samples = _samples()
    facility = samples["facility-agreement"]
    licence = samples["software-licence"]
    policy = samples["property-policy"]

    def all_literals(sample: dict) -> str:
        return " ".join(
            part["text"]
            for section in sample["sections"]
            for element in section["elements"]
            for part in element["parts"]
            if part["kind"] == "literal"
        )

    assert "[Agent]" in all_literals(facility), "no bracket placeholder"
    assert "GBP 250" in all_literals(facility), "no unmarked money amount"
    assert "120 days" in all_literals(facility), "no unmarked duration"

    policy_variable_keys = {v["variableKey"] for v in policy["variables"]}
    referenced_variable_keys = {
        part["variableKey"]
        for section in policy["sections"]
        for element in section["elements"]
        for part in element["parts"]
        if part["kind"] == "variable"
    }
    unreferenced = policy_variable_keys - referenced_variable_keys
    assert unreferenced == {"period-start"}, f"expected only period-start unreferenced, got {unreferenced}"

    assert any(u["text"] == "Fees are exclusive of VAT." for u in licence["unmarked"]), "no unmarked entry"

    grant_clauses = [
        _literal_text(element) + "".join(p.get("text", "") for p in element["parts"] if p["kind"] != "literal")
        for section in licence["sections"]
        if section["sectionKey"] == "grant"
        for element in section["elements"]
    ]
    assert any("shall not" in text for text in grant_clauses), "no misplaced Prohibition-shaped clause in Grant"
