<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Conformance-Level Ladder

Companion reference for [decisions/ADR-A14-conformance-levels.md](decisions/ADR-A14-conformance-levels.md). This document is the detailed, living version of the ladder; the ADR records the decision to adopt it.

| Level | Description | Required for | Typical checks |
|---|---|---|---|
| **L0 — RDF ingestible** | Syntactically valid RDF with source provenance | Storage, discovery | Parses under the target syntax; carries a source-graph-role annotation (ADR-A13) |
| **L1 — Mapped/mapping-pending** | Confirmed mappings, mapping hypotheses, or explicit unmapped markers present | MORK-style integration | Every asserted mapping traces to a mapping activity |
| **L2 — Semantically classified** | Resources related to LATTICE classes/properties, possibly incompletely | Exploratory query | Resources typed against a known class; incompleteness is not an error |
| **L3 — Declaration-conformant** | Dimension sets, state spaces, transitions, authorities, etc. satisfy authoring shapes | Declaration governance | Authoring SHACL shapes pass; declaration reaches a governance state permitting further use |
| **L4 — Analysis-ready** | Suitable for stated SPARQL/reasoning/materialisation profiles | Candidate detection (E1/B-P1), gap analysis | Read-set/dependency analysis completes; no unresolved structural blocker |
| **L5 — Operationally evaluable** | Required facts, closure assumptions, evaluator profile, `Undetermined` dispositions present | Eligibility decisions | Every consumption point has a disposition for `Undetermined`; witnessed dimensions are complete for the stated evaluation |
| **L6 — Authoritative execution-ready** | Additionally satisfies transaction/authority/idempotency/ambiguity/effect requirements | Behaviour authoritative execution | Selection policy present and unambiguous; authority satisfiable; effect payloads complete; target bindings resolve |
| **L7 — Projection-conformant** | A materialised/external representation demonstrably consistent with its declared contract | External system integration | Projection matches its source under the synchronisation contract (ADR-A12) |

## Using the ladder

- State the level a fixture or check targets. Do not describe a graph as "invalid" without naming which level it fails.
- Higher levels are not a superset validation pass over lower ones — L6 does not imply an L0 syntax check was skipped, but a graph may legitimately sit at L2 for months without ever needing L5.
- SHACL shapes are organised by the level/profile they check, not as one monolithic shape graph, so that an L2 fixture failing an L6 shape is not surfaced as a CI failure.
