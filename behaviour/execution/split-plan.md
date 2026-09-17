<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Behaviour execution split plan

Execution concerns remain split from the authored ontology:

- `spec/`, `vocab/`, `shapes/`, and `projection/` remain normative declaration sources
- execution artefacts are derived outputs only
- operational evaluators may implement direct SPARQL, SHACL, materialised, projected, or compiled profiles per ADR-A15

At Gate 3 this split is documented only. No generator is built yet.
