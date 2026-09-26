<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Applied Insurance Reference — Phase 3, Eligibility Readings and Crosswalks

**Unit ID:** `applied-insurance-reference-phase-3`
**Epic:** [applied-insurance-reference](applied-insurance-reference.md)
**Status:** Rolling-wave outline. AIR-3.1 to AIR-3.3 are substrate slices, detailed when their
ADRs are accepted. AIR-3.4 and AIR-3.5 need the cause scheme and are detailed at AIR-2.4.
**Decisions:** [ADR-A100](../../architecture/decisions/ADR-A100-hierarchical-match-over-flat-schemes.md) (D11), [ADR-A103](../../architecture/decisions/ADR-A103-eligibility-set-readings.md) (D12)
**Sketches:** [mork-bridge.md](../sketches/mork-bridge.md), [peril-vocabulary.md](../sketches/peril-vocabulary.md) §6.8

## Scope

Make Eligibility decide correctly when a peril list is flat (A-100) and when a path reaches
several values (A-103), then let reviewed crosswalks carry a flat or simply taxonomic list to the
reference. Milestone M2 is a check across cause, agency and mechanism, run against the reference,
a flat list and a crosswalked list.

AIR-3.1 to AIR-3.3 change substrate. Each follows ADR-A-C2: the ADR's non-insurance examples are
authored as fixtures before the README prose, and no insurance term enters either layer.

## Slices

| Slice | Content | Modules |
|---|---|---|
| AIR-3.1 | A-100: the law beside L11 in the Eligibility README, its two example fixtures, `exe:NoHierarchy` (Executable PATCH), the rule in the IR's expansion and in the SPARQL backend, and the OWL backend's refusal | `ontology/eligibility` (README, examples), `tools/mork_compilers`. `Executable.ttl` gains one individual, a stated deviation from the two-module rule |
| AIR-3.2 | A-103: `elg:ValueReading`, its three individuals, `elg:valueReading` and `elg:negated` (Eligibility MINOR, cascade), fixtures, the IR, SPARQL and SHACL | `ontology/eligibility`, `tools/mork_compilers` |
| AIR-3.3 | A-103 in the SWRL (sound subset, swapped heads under negation) and OWL (`∃`, `∀ ⊓ ∃`, complement) backends | `tools/mork_compilers` |
| AIR-3.4 | crosswalk format: reviewed SKOS triples plus characteristic values on codes that name several things, as a `fnd:DerivedArtefact`. A crosswalk of one market list, and the lookup that lifts codes to reference concepts at ingestion | `insurance/peril/crosswalk/`, `ontology/mork` examples |
| AIR-3.5 | lowering to a market list, list-to-list through the reference, and milestone M2 | as 3.4, `insurance/exposure/examples/` |

Tests at L1 and L2:

- 3.1: on a flat scheme, a required code matches, an excluded code is excluded, every other member
  is Undetermined with `exe:NoHierarchy`, and a hierarchical scheme evaluates as before. SPARQL,
  SHACL and SWRL agree. The OWL backend refuses
- 3.2: each reading over zero, one and several values, including an exclusion read `EveryValue`,
  and a binding without a reading behaving as today. A negated condition swaps Permitted and
  Denied and keeps Undetermined with its diagnostic. SPARQL and SHACL agree
- 3.3: SWRL derives only the sound subset. OWL classes stand in the expected subsumptions
- 3.4: a crosswalk is stale when either edition changes. An inexact mapping never decides
- 3.5 (M2): the cyber write-back profile of peril vocabulary §6.8 decides on the reference,
  is Undetermined with a reason on a flat list, and decides exactly mapped codes of a crosswalked
  list. A risk whose perils are all of sudden onset is Permitted under `EveryValue`

Order and lanes: [machines, branches and merges](applied-insurance-reference-lanes.md). Substrate item
S2 also changes Eligibility, and rebases onto AIR-3.2.

## AIR-3.1 in detail

**Machine:** R (Claude Code). **Branch:** `air/3.1-flat-hierarchy`. **Validation Pack:**
[applied-insurance-reference-3.1](../validation/applied-insurance-reference-3.1.md).
**Decision:** ADR-A100, with its implementation note.

**Invariant:** under `elg:HierarchicalMatch`, a resolved scheme in which no member has a
`skos:broader` link to another member decides only the concepts a condition names. Every other
member is Undetermined with `exe:NoHierarchy`, in every backend, and hierarchical schemes
evaluate exactly as before.

Authored in ADR-A-C2 order: the two example fixtures first, then the law, then the code.

1. **Examples** in `ontology/eligibility/examples/`, no `owl:Ontology`, no insurance terms:
   - `flat-scheme-lending.ttl`: a contract whose unscoped `voc:boundScheme` is a hierarchical
     industry classification (manufacturing above food processing and textiles, plus retail),
     and a `voc:SchemeBinding` scoped to one lender that binds the lender's flat sector list
     (the same concepts, no `skos:broader`). One `HierarchicalMatch` condition requires
     manufacturing and excludes textiles. Recorded decisions: under the classification, food
     processing is Permitted. Under the lender's list, manufacturing is Permitted, textiles Denied,
     food processing and retail Undetermined with `exe:NoHierarchy`.
   - `flat-scheme-employment.ttl`: an exclusion-only condition ("every role except contractors")
     over a flat job-title list. Contractors are Denied, and every other title is Undetermined,
     not Permitted, since L12's default inclusion needs the hierarchy to know a title is not a
     kind of contractor.
2. **The law** `elg:L14` in `ontology/eligibility/vocab/eligibility-vocab.ttl` and its README
   mirror (§4 law list and the decision table, next to L11), with `elg:lawRegister
   elg:SemanticLaw`: "Hierarchy precondition. Under hierarchical match, when no member of the
   resolved scheme has a broader concept within the scheme, a candidate that is a member and is
   neither a required nor an excluded concept leaves the condition undetermined." The README's
   "`HierarchicalMatch` is valid when…" sentence cites L14. Eligibility vocab 0.6.0 → 0.7.0
   (MINOR, a new individual).
3. **The diagnostic** `exe:NoHierarchy` in `ontology/mork/spec/Executable.ttl`, beside
   `exe:AboveExclusion`, citing `elg:L14`. Executable 0.5.0 → 0.6.0 (MINOR). No ontology imports
   either document, so the cascade is the catalog and the release register only.
4. **The IR** (`tools/mork_compilers/src/mork_compilers/eligibility_ir.py`): `_expand` takes
   whether the resolved ordering has any `skos:broader` link. When the match is hierarchical and it
   has none, a member is Denied if it is an excluded concept, Permitted if it is a required
   concept, and Undetermined otherwise. `ConceptPlan` gains a derived `no_hierarchy` property
   the backends read.
5. **SPARQL** (`sparql_backend.concept_select`): a plan with `no_hierarchy` uses the equality
   decision with Undetermined as its last branch, and reports `exe:NoHierarchy` as the diagnostic.
   Scheme membership still wraps it, so a non-member stays `exe:OutsideScheme`.
6. **SHACL** (`shacl_backend`): reads the expansion already. Its Undetermined message names
   `exe:NoHierarchy` for such a plan.
7. **SWRL**: no change. `concept_facts` reads the expansion, so Undetermined members derive nothing.
8. **OWL** (`owl_backend`): refuse a plan with `no_hierarchy` with an `IRCompileError` citing
   ADR-A100, since a design-time class cannot express Undetermined.
9. **Tests**: new cases in `test_hierarchical_conditions.py`, and the two examples added to
   `tools/test_eligibility_examples.py`'s `EXAMPLES`. No existing test changes.
10. **Docs**: `tools/mork_compilers/README.md` (L14 in each backend), and the Eligibility row of
    `docs/architecture/ontology-architecture.md` §3. Then `mise run build:ontology-catalog` and
    `mise run build:ontology-releases`.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AIR31-01 | the lending example under the classification / expanded / food processing Permitted | L1 | + |
| AIR31-02 | the lending example under the lender's list / expanded / manufacturing Permitted, textiles Denied | L1 | + |
| AIR31-03 | the same / expanded / food processing and retail Undetermined, plan has `no_hierarchy` | L1 | + |
| AIR31-04 | the employment example / expanded / contractors Denied, every other title Undetermined | L1 | − |
| AIR31-05 | a candidate outside the lender's list / SPARQL / Undetermined with `exe:OutsideScheme` | L1 | − |
| AIR31-06 | the lender's list / SPARQL / every member's decision equals the expansion, Undetermined rows carry `exe:NoHierarchy` | L2 | + |
| AIR31-07 | the same / SHACL / admitted and undetermined sets equal the expansion's | L2 | + |
| AIR31-08 | the same / SWRL / derives Permitted for manufacturing and Denied for textiles only | L1 | + |
| AIR31-09 | a `no_hierarchy` plan / OWL backend / `IRCompileError` | L1 | − |
| AIR31-10 | both examples / Eligibility shapes / no result | L1 | + |
| AIR31-11 | the existing hierarchical tests / unchanged / pass (non-weakening) | L1 | + |

Adversarial probe for the gate: remove the flat branch from `_expand` and AIR31-03 fails.

## Documentation deltas

| Document | Change | Slice |
|---|---|---|
| `ontology/eligibility/README.md`, examples | the A-100 law, the A-103 readings | 3.1, 3.2 |
| `tools/mork_compilers/README.md` | both laws in every backend | 3.1 to 3.3 |
| `docs/architecture/ontology-architecture.md` | Eligibility section, and the MORK section on proposals that end as crosswalks | 3.2, 3.4 |
| `docs/architecture/solution-design-specification.md` | set readings as an evaluation feature | 3.2 |

## Exit gate

A-100 and A-103 Accepted and implemented. M2 demonstrated. MB-Q2 answered.
