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

**Invariant:** each applied insurance module has its own spec, shapes and `.version`, the catalog
and versioning checks cover it, and no known defect remains in applied insurance.

1. `git rm` the legacy spec, vocab, shapes and `.version` under `ontology/applied/insurance/`.
2. Remove its `KNOWN_DEFECTS` entry from `tools/ontology_catalog.py`, and regenerate catalogs.
3. Write `applied/README.md` (domains, and how common elements are shared, per A-98) and the
   insurance domain README.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AIR11-01 | the tree / `check:ontology-catalog` / passes, with no applied insurance known defect | L1 | + |
| AIR11-02 | the tree / `check:ontology-versioning` / passes | L1 | + |
| AIR11-03 | the repository / search for the legacy namespaces `…/ontology/nsd/` and `…/insurance/contract` / no remaining reference outside history | L1 | − |

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
