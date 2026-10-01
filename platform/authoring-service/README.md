<!-- SPDX-License-Identifier: MPL-2.0 -->

# Word authoring POC service

A proof-of-concept HTTP service for the [word authoring add-in](../../apps/word-authoring-addin)
(ADR-A114). **Not a platform contract.** Its code, vocabulary and graph layout may be removed or
rewritten without deprecation; nothing outside this unit may depend on them.

See the [sketch](../../docs/developer/sketches/word-authoring-poc.md), the
[plan](../../docs/developer/plans/word-authoring-poc.md) and
[ADR-A114](../../docs/architecture/decisions/ADR-A114-word-authoring-proof-of-concept.md).

## What this slice (WA2) builds

Maps a validated `document-snapshot` (plan WA1) to the Wording-layer graph the sketch §4
describes, validates it with SHACL, and writes the canonical fixtures used as goldens. The HTTP
API, detection, templates and the runnable service come in WA3 to WA5.

| Package | Holds |
|---|---|
| `json` | the shared Jackson mapper, and `ContractSchemas`, which loads every JSON Schema from the classpath and validates against it |
| `model` | `DocumentSnapshot` and its parts, read by hand from a validated JSON node (`SnapshotReader`), not via Jackson polymorphism |
| `rdf` | `Vocab` (every IRI this service writes), `IriMinter` (the instance IRIs of plan §2.3, each checked against its §2.4 pattern), `WordingMapper` (the mapping of plan §2.3 "Mapping rules"), `CanonicalHash` (an insertion-order-independent content hash) |
| `validation` | `WordingValidator`, which runs the SHACL shapes of `shapes/wording-poc-shapes.ttl` |
| `app` | `FixtureWriter`, which regenerates `contracts/authoring/fixtures/wording/*.nt` from the samples |

## Commands

| Command | Does |
|---|---|
| `mise run check:authoring-service` | builds and runs the unit tests |
| `mise run build:authoring-fixtures` | regenerates the committed `.nt` golden fixtures from the three samples |

## The provisional vocabulary

`src/main/resources/vocab/wording-provisional.ttl` documents every IRI this service writes: the
`wrd:` terms taken provisionally from the
[computable contract substrate sketch](../../docs/developer/sketches/computable-contract-substrate.md)
§4, ahead of CCS slice C3 (which will publish `ontology/wording/` under ADR-A112), and this POC's
own `wap:` terms. The gaps between what the CCS sketch names and what this service needs — noted in
plan §2.6 — are marked `POC gap (plan §2.6)` in the vocabulary file, and are input to CCS C3. `ins:`
terms for the proposed meaning graph (sketch §4.4) are added when WA6 builds the worker that writes
them.

## Store

`WordingValidator` and `WordingMapper` work on an in-memory Jena `Model`. A Fuseki-backed store
seam, over the Graph Store Protocol, arrives in WA5 (decision WA-D5). The service does not use or
extend the semantic dataset SPI (ADR-A71, ADR-A75): see ADR-A114 decision 4.
