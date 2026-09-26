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
     industry classification (manufacturing above food processing and textiles, plus retail and
     wholesale), and a `voc:SchemeBinding` scoped to one lender that binds the lender's flat
     sector list. The list reuses only concepts whose broader concept lies outside it (food
     processing, textiles, retail, wholesale), because `skos:broader` belongs to concepts and a
     reused parent and child would carry their link into the list. One `HierarchicalMatch`
     condition requires manufacturing or retail and excludes textiles. Recorded decisions: under
     the classification, food processing and retail Permitted, textiles and wholesale Denied.
     Under the lender's list, retail Permitted, textiles Denied, food processing and wholesale
     Undetermined with `exe:NoHierarchy`.
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
9. **Tests**: a new `test_flat_schemes.py`, reusing the SHACL and SWRL helpers of
   `test_concept_backends.py` (which already imports `test_hierarchical_conditions.py`, so new
   cases there would import in a cycle), and the two examples added to
   `tools/test_eligibility_examples.py`'s `EXAMPLES`. The one existing change registers
   `exe:NoHierarchy` in `test_concept_backends.py`'s closed set of diagnostics.
10. **Docs**: `tools/mork_compilers/README.md` (L14 in each backend), and the Eligibility row of
    `docs/architecture/ontology-architecture.md` §3. Then `mise run build:ontology-catalog` and
    `mise run build:ontology-releases`.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AIR31-01 | the lending example under the classification / SPARQL / food processing and retail Permitted, textiles and wholesale Denied | L1 | + |
| AIR31-02 | the lending example under the lender's list / SPARQL / retail Permitted, textiles Denied | L1 | + |
| AIR31-03 | the same / SPARQL / food processing and wholesale Undetermined with `exe:NoHierarchy`, plan has `no_hierarchy` | L1 | + |
| AIR31-04 | the employment example / expanded / contractors Denied, every other title Undetermined | L1 | − |
| AIR31-05 | a candidate outside the lender's list / SPARQL / Undetermined with `exe:OutsideScheme` | L1 | − |
| AIR31-06 | the lender's list / SPARQL / every member's decision equals the expansion, Undetermined rows carry `exe:NoHierarchy` | L2 | + |
| AIR31-07 | the same / SHACL / admitted and undetermined sets equal the expansion's | L2 | + |
| AIR31-08 | the same / SWRL / derives Permitted for retail and Denied for textiles only | L1 | + |
| AIR31-09 | a `no_hierarchy` plan / OWL backend / `IRCompileError` | L1 | − |
| AIR31-10 | both examples / Eligibility shapes / no result | L1 | + |
| AIR31-11 | the existing hierarchical tests / unchanged / pass (non-weakening) | L1 | + |

Adversarial probes for the gate: disabling the L14 branch in `_expand` fails AIR31-06, 07 and 08.
Disabling it in `sparql_backend.concept_select` fails AIR31-03, 04, 06 and 07.

## AIR-3.2 in detail

**Machine:** R (Claude Code). **Branch:** `air/3.2-set-readings`. **Validation Pack:**
[applied-insurance-reference-3.2](../validation/applied-insurance-reference-3.2.md).
**Decision:** ADR-A103.

**Invariant:** a bound condition reads several values by the reading its binding declares, a
negated condition swaps Permitted and Denied and keeps Undetermined with its diagnostic, a
binding without a reading and a condition without negation evaluate exactly as before, and the
SWRL and OWL backends refuse what they cannot yet compile.

Authored in ADR-A-C2 order: examples, then laws and README, then code.

1. **Examples** in `ontology/eligibility/examples/`, no insurance terms:
   - `set-reading-admissions.ttl`: applicants bound through `ex:holdsQualification`. One
     condition, read `elg:SomeValue`, requires mathematics or physics. A second, read
     `elg:SomeValue` and `elg:negated true`, requires medicine ("holds no qualification in
     medicine"). Recorded: history and physics admitted, history alone refused, no
     qualification Undetermined, a medic refused by the negated condition.
   - `set-reading-trial.ttl`: patients bound through `ex:hasDiagnosis`, read `elg:EveryValue`,
     over a permitted list that excludes one diagnosis. Recorded: all permitted admitted, one
     excluded refused.
2. **Eligibility spec** (`spec/eligibility.ttl` and its README mirror, 0.6.0 → 0.7.0, MINOR):
   `elg:ValueReading` (a class, added to the disjoint classes axiom), `elg:valueReading`
   (functional object property, domain `elg:EvidenceBinding`, range `elg:ValueReading`),
   `elg:negated` (functional datatype property, domain `elg:Condition`, range `xsd:boolean`).
3. **Eligibility vocabulary** (0.7.0 → 0.8.0, MINOR): `elg:SingleValue`, `elg:SomeValue`,
   `elg:EveryValue`, and the laws `elg:L15` (set readings, as ADR-A103 decision 1 states them)
   and `elg:L16` (negation, decision 4). README: the evidence bindings paragraph and the law
   list.
4. **Eligibility shapes** (`.version` 0.1.0 → 0.2.0, MINOR): the structural shapes gain
   `sh:maxCount 1` for `elg:valueReading` and `elg:negated`, mirroring the functional axioms.
5. **Cascade** (ADR-A86 addendum item 1, each MINOR): every importer of `eligibility/0.6.0`
   re-pins, and so on through their importers: `eligibility-vocab`, Instrument 0.6.0 → 0.7.0,
   Behaviour 0.6.0 → 0.7.0 (it imports Eligibility and Instrument), and the Capacity execution
   profile 0.6.0 → 0.7.0, with their README mirrors. The list is re-derived with `grep` before and
   after editing.
6. **IR:** `EvidencePath.reading` (default `elg:SingleValue`), and `negated` on concept and
   interval plans. Readings apply to bound conditions only. A question offering several
   candidates stays Undetermined (`exe:SeveralCandidates`).
7. **SPARQL:** for `SomeValue` and `EveryValue`, decide each value as a single candidate is
   decided, then group by subject and aggregate by strong Kleene logic. No value is Undetermined
   with `exe:MissingCandidate`. A set that is Undetermined reports a diagnostic of one of its
   Undetermined values. Negation swaps the final decision. Profiles read the condition's final
   decision.
8. **SHACL:** the same readings and negation, through the SPARQL-based constraints.
9. **SWRL and OWL:** refuse a plan with a reading other than `SingleValue`, or with negation, with
   an `IRCompileError` naming AIR-3.3, until that slice lands.
10. **Tests:** `tools/mork_compilers/src/mork_compilers/test_set_readings.py`, and both examples
    in `tools/test_eligibility_examples.py`.
11. **Docs:** Eligibility README, `tools/mork_compilers/README.md`, the Eligibility row of
    `docs/architecture/ontology-architecture.md` §3, and `solution-design-specification.md` (set
    readings as an evaluation feature). Then `mise run build:ontology-catalog` and `mise run
    build:ontology-releases`.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AIR32-01 | `SomeValue` over {Permitted, Denied}, {Denied, Denied}, {Denied, Undetermined} / SPARQL / Permitted, Denied, Undetermined | L1 | + |
| AIR32-02 | `EveryValue` over {Permitted, Permitted}, {Permitted, Denied}, {Permitted, Undetermined} / SPARQL / Permitted, Denied, Undetermined | L1 | + |
| AIR32-03 | an exclusion read `EveryValue`, one value excluded / SPARQL / Denied | L1 | − |
| AIR32-04 | a subject with no value under each reading / SPARQL / Undetermined, `exe:MissingCandidate` | L1 | − |
| AIR32-05 | a binding without a reading, and one read `SingleValue`, reaching two values / SPARQL / Undetermined, `exe:SeveralCandidates`, as before | L1 | − |
| AIR32-06 | a negated condition, question-based and bound / SPARQL / Permitted and Denied swap, Undetermined keeps its diagnostic | L1 | + |
| AIR32-07 | the negated `SomeValue` medicine condition / SPARQL / a medic Denied, a non-medic Permitted | L1 | + |
| AIR32-08 | an interval condition read `EveryValue` / SPARQL / Denied when one value is outside | L1 | − |
| AIR32-09 | an `AllRequired` profile over a set-read and a negated condition / SPARQL / strong Kleene over their final decisions | L1 | + |
| AIR32-10 | both examples / SHACL / agrees with SPARQL for every subject | L2 | + |
| AIR32-11 | a plan with a reading or negation / SWRL and OWL backends / `IRCompileError` naming AIR-3.3 | L1 | − |
| AIR32-12 | both examples / Eligibility shapes / no result | L1 | + |
| AIR32-13 | a binding with two readings, a condition negated twice / Eligibility shapes / violation | L1 | − |
| AIR32-14 | the existing compiler and examples tests / unchanged / pass (non-weakening) | L1 | + |
| AIR32-15 | the cascade / `check:ontology-versioning` / every importer re-pinned and bumped, every version listed | L1 | + |

## Documentation deltas

| Document | Change | Slice |
|---|---|---|
| `ontology/eligibility/README.md`, examples | the A-100 law, the A-103 readings | 3.1, 3.2 |
| `tools/mork_compilers/README.md` | both laws in every backend | 3.1 to 3.3 |
| `docs/architecture/ontology-architecture.md` | Eligibility section, and the MORK section on proposals that end as crosswalks | 3.2, 3.4 |
| `docs/architecture/solution-design-specification.md` | set readings as an evaluation feature | 3.2 |

## Exit gate

A-100 and A-103 Accepted and implemented. M2 demonstrated. MB-Q2 answered.
