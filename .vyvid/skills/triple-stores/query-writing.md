## Rules and the checklist

The record is [docs/architecture/efficient-queries-and-shapes.md](../../../docs/architecture/efficient-queries-and-shapes.md) (ADR-A128), and the checklist is STD-042. A rewrite for speed is a PATCH change to the shapes' version, replayed against the old shapes' results first.

A shape or a fixture that changes for speed is replayed against the old results first (R7): `mise run dev:record-validations` before the
change, `mise run dev:replay-validations` before and after it (`tools/validation_replay.py` explains the baseline).

## Writing a SHACL-SPARQL constraint

The shapes in `ontology/eligibility/shapes/constraints.ttl` declare their prefixes inside the query.

## Findings about cost

The design record is [docs/architecture/efficient-queries-and-shapes.md](../../../docs/architecture/efficient-queries-and-shapes.md) (ADR-A128).
