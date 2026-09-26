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

### AIR-1.2: Shared contracts, `applied/classification/` and `insurance/common/`

**Machine:** S (Copilot Business). **Branch:** `air/1.2-shared-contracts`, created after AIR-1.1
merges. **Validation Pack:**
[applied-insurance-reference-1.2](../validation/applied-insurance-reference-1.2.md), whose Handoff
section S fills in. **Decisions:** ADR-A98 (decisions 1, 5, 6), ADR-A102.

**Invariant:** every classification the epic needs has one `voc:SchemeContract`, at the lowest
level of sharing that covers its users (epic D5), and the liability role types exist as
`pty:Role` individuals. A cross-domain module imports nothing from a domain.

A scheme contract must name the property it constrains (`voc:constrainsProperty`, required by
Vocabulary's shapes). The modules that will use these classifications (peril, exposure) do not
exist yet, so each module declares one general property per classification, and later modules
declare theirs as sub-properties of it (for example `aeo:peril rdfs:subPropertyOf icm:peril`).
No contract has a `voc:boundScheme` here: reference editions bind themselves when they arrive
(AIR-2.2 and later), and deployments bind their own.

**`ontology/applied/classification/`** (cross-domain, no insurance terms anywhere in it):

| File | Ontology IRI, version IRI | Content |
|---|---|---|
| `spec/classification.ttl` | `https://www.nebularis.org/neuro-semantic/lattice/applied/classification`, `…/lattice/applied/classification/0.1.0` | prefix `cls:` (`…/applied/classification#`). Imports Foundation 0.3.0 and Vocabulary 0.3.0. Three `owl:ObjectProperty`s with range `skos:Concept` and no domain: `cls:territory`, `cls:assetClass`, `cls:industry`. Each has `rdfs:label`, `rdfs:comment` and `fnd:utility` |
| `vocab/classification-vocab.ttl` | `…/lattice/applied/classification/vocab`, `…/lattice/applied/classification-vocab/0.1.0` | prefix `cls-voc:` (`…/applied/classification/vocab#`). Imports the spec 0.1.0. Three `voc:SchemeContract`s: `cls-voc:TerritoryContract`, `cls-voc:AssetClassContract`, `cls-voc:IndustryContract`, each with `fnd:hasIdentity` (a `fnd:PersistentIdentity` node), `fnd:hasGovernanceState fnd:Active`, `skos:prefLabel` and `voc:constrainsProperty` its property |
| `README.md` | | purpose, the three contracts, how a domain specialises the properties, and the no-domain-terms rule |

**`ontology/applied/insurance/common/`:**

| File | Ontology IRI, version IRI | Content |
|---|---|---|
| `spec/common.ttl` | `https://www.nebularis.org/neuro-semantic/insurance/common`, `…/insurance/common/0.1.0` | prefix `icm:` (`…/insurance/common#`). Imports Foundation 0.3.0, Vocabulary 0.3.0, Party 0.5.0 and `…/lattice/applied/classification/0.1.0`. Six `owl:ObjectProperty`s with range `skos:Concept`: `icm:peril`, `icm:mechanism`, `icm:agency`, `icm:consequence`, `icm:harmSubject`, `icm:pool` |
| `vocab/common-vocab.ttl` | `…/insurance/common/vocab`, `…/insurance/common-vocab/0.1.0` | prefix `icm-voc:`. Imports the spec 0.1.0. Six contracts as in classification: `icm-voc:PerilContract`, `icm-voc:MechanismContract`, `icm-voc:AgencyContract`, `icm-voc:ConsequenceContract`, `icm-voc:HarmSubjectContract`, `icm-voc:PoolContract`. Four roles declared as `pty:Obligor` is in `ontology/party/vocab/party-vocab.ttl` (`owl:NamedIndividual`, `pty:Role`, label, comment, `fnd:utility`): `icm-voc:HarmedParty`, `icm-voc:LiableParty`, `icm-voc:Claimant`, `icm-voc:Payee` |
| `README.md` | | purpose, the contracts and roles, the specialisation rule, and what arrives later: the loss event (AIR-4.4) and the liability direction scheme (Phase 5, ADR-A102) |

No `shapes/` directory in either module: neither has a shape of its own yet, and Vocabulary's
and Party's shapes cover the contracts and roles. ADR-A98 decision 3 lists the directories a
module has once it needs them.

**Edit:** `ontology/applied/README.md` (classification now present), `insurance/domain-README.md`
(common now built, with its prefixes), and the applied insurance row of
`docs/architecture/ontology-architecture.md` §3.

**Test:** `tools/test_applied_shared_contracts.py`, modelled on
`tools/test_eligibility_examples.py`. Data is each module's two documents, shapes are Vocabulary's
and Party's shape files, pySHACL with `advanced=True` and `inference="none"`.

**On R at verification:** `mise run build:ontology-catalog` and `mise run build:ontology-releases`
(four new documents).

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AIR12-01 | the four documents / loaded with their import closures (`tools/ontology_catalog.py`) / parse, every import resolves | L1 | + |
| AIR12-02 | the nine contracts / Vocabulary's shapes / conform | L1 | + |
| AIR12-03 | a contract without `voc:constrainsProperty` / Vocabulary's shapes / violation | L1 | − |
| AIR12-04 | the four roles / read / each is a `pty:Role` and an `owl:NamedIndividual` | L1 | + |
| AIR12-05 | `classification`'s import closure / read / contains no document under `neuro-semantic/insurance/` | L1 | − |
| AIR12-06 | every term in `classification/` / searched for insurance terms (peril, policy, premium, claim, insur) / no match | L0 | − |

## Documentation deltas

| Document | Change | Slice |
|---|---|---|
| `ontology/applied/README.md` | domains, the three levels of sharing, module table and dependency direction | 1.1 |
| `docs/architecture/ontology-architecture.md` §3 | applied insurance row in the implementation status table | 1.1 |
| `tools/ontology_catalog.py` | `KNOWN_DEFECTS` entry removed | 1.1 |

## Exit gate

AIR-1.1 and AIR-1.2 signed off in `LOG.md`.
