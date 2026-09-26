<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Applied Insurance Reference — Phase 1, Module Split

**Unit ID:** `applied-insurance-reference-phase-1`
**Epic:** [applied-insurance-reference](applied-insurance-reference.md)
**Status:** Proposed. Starts when A-98 is Accepted.
**Status record:** the epic [status record](../status/applied-insurance-reference.md) (lanes §5)

## Starting point

`ontology/applied/insurance/` holds one legacy module: `spec/structure/contract.ttl` (2,705
lines, `owl:versionIRI …/insurance/contract/0.2.0`), `vocab/structure-vocab.ttl` and shared
`shapes/`. The spec does not parse as Turtle (a `KNOWN_DEFECTS` entry in
`tools/ontology_catalog.py`), imports pre-LATTICE namespaces, and nothing in the repository
imports it. Epic D1 drops it.

## Scope

Drop the legacy module, create the layout A-98 decides, and give the domain its shared scheme
contracts. The applied and insurance domain READMEs, `insurance/common/` and
`applied/classification/` are created here. Each later module's
directory is created by the phase that fills it. A new contract module waits for Phase 5 (epic
D2).

## Slices

### AIR-1.1: Drop the legacy contract module, create the layout

**Machine:** S (Copilot Business). **Branch:** `air/1.1-layout`. **Validation Pack:**
[applied-insurance-reference-1.1](../validation/applied-insurance-reference-1.1.md), whose Handoff
section S fills in.

**Invariant:** the legacy module and its known defect are gone, no ontology or tool file refers to
it, and the applied layer's READMEs describe the layout of ADR-A98.

**Remove** (`git rm`):

| Path under `ontology/applied/insurance/` | |
|---|---|
| `spec/structure/contract.ttl`, `spec/structure/README.md`, `spec/structure/catalog-v001.xml` | the legacy spec |
| `vocab/structure-vocab.ttl` | its vocabulary |
| `shapes/structural.ttl`, `shapes/constraints.ttl`, `shapes/.version` | its shapes |

**Edit:**

1. `tools/ontology_catalog.py`: delete the `KNOWN_DEFECTS` entry for
   `ontology/applied/insurance/spec/structure/contract.ttl`. Nothing else in that file changes.
2. `ontology/applied/README.md`: rewrite it. Cover the domains and the cross-domain modules, the
   three levels of sharing (ADR-A98 decision 1), the one-way dependency direction (decision 5 as
   amended), namespaces (decision 6), per-module versioning (ADR-A86), and a module table:
   `capacity/` (cross-domain, present), `classification/` (cross-domain, AIR-1.2), `insurance/`
   (domain, see its `domain-README.md`).
3. `ontology/applied/insurance/domain-README.md`: new. The insurance domain, its modules with
   their state and slice (`common/` AIR-1.2, `peril/` Phase 2, `exposure/` Phase 4, `submission/`
   AIR-6.1, `claims/` and `contract/` deferred by epic D2), the dependency order, the prefixes of
   ADR-A98 decision 6, and links to the epic and the sketches. One sentence records that the
   legacy contract module was dropped (epic D1) and remains available at its release tags.
4. `docs/architecture/ontology-architecture.md` §3: add a row for the applied insurance domain,
   stating the legacy module is dropped and the modules are planned under the epic.
5. `docs/architecture/ontology-versioning-policy.md`: the "Still open" paragraph on the
   `insurance/` namespace family is answered by ADR-A98 decision 6 (deliberate). Replace it with
   one sentence saying so. Leave the table rows above it, which are history.

**Leave unchanged:** `docs/architecture/ontology-releases.md` (released history), every ADR, and
other units' plans, status records and validation packs.

**On R at verification:** `mise run build:ontology-catalog` (regenerates the root catalog without
the legacy entries).

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AIR11-01 | the tree / `mise run check:ontology-catalog` / passes, and `KNOWN_DEFECTS` has no applied insurance entry | L1 | + |
| AIR11-02 | the tree / `mise run check:ontology-versioning` / passes | L1 | + |
| AIR11-03 | `ontology/` and `tools/` / search for `ontology/nsd`, `neuro-semantic/insurance/contract` and `structure-vocab` / no match | L1 | − |
| AIR11-04 | `ontology/applied/README.md` and `insurance/domain-README.md` / read against ADR-A98 / every module, level and prefix agrees | L0 | + |

### AIR-1.2: Shared contracts, `insurance/common/` and `applied/classification/`

**Invariant:** every classification has one `voc:SchemeContract`, at the lowest level of sharing
that covers its users (epic D5).

1. `applied/classification/`: territory, asset class and industry contracts (D8). Imports
   Foundation and Vocabulary by exact version IRI.
2. `applied/insurance/common/`: peril, peril mechanism, peril agency, consequence, harm subject
   and pool contracts, and the party role types of A-102 (harmed, liable, claimant, payee) (D7).
   Imports Foundation, Vocabulary, Party and `classification/`. Prefix per A-98 (not `ins:`,
   which Instrument owns). The loss event class is added by AIR-4.4, when exposure first needs
   it.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AIR12-01 | `classification` and `common` / loaded with their closures / parse, no unresolved import | L1 | + |
| AIR12-02 | each contract / Vocabulary shapes / conforms | L1 | + |
| AIR12-03 | a contract with no `voc:boundScheme` and no binding / Vocabulary shapes / reported | L1 | − |
| AIR12-04 | the role types / Party shapes / each is a `pty:Role`, occupancies may be unfilled | L1 | + |
| AIR12-05 | `classification` / import closure / contains no insurance module | L1 | − |

## Documentation deltas

| Document | Change | Slice |
|---|---|---|
| `ontology/applied/README.md` | domains, the three levels of sharing, module table and dependency direction | 1.1 |
| `docs/architecture/ontology-architecture.md` §3 | applied insurance row in the implementation status table | 1.1 |
| `tools/ontology_catalog.py` | `KNOWN_DEFECTS` entry removed | 1.1 |

## Exit gate

AIR-1.1 and AIR-1.2 signed off in `LOG.md`.
