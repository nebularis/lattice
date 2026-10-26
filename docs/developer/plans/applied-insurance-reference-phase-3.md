<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Applied Insurance Reference — Phase 3, Eligibility Readings and Crosswalks

**Unit ID:** `applied-insurance-reference-phase-3`
**Epic:** [applied-insurance-reference](applied-insurance-reference.md)
**Status:** Rolling-wave outline. AIR-3.1 to AIR-3.3 are substrate slices, detailed when their
ADRs are accepted. AIR-3.4 and AIR-3.5 were detailed on 2026-10-13, for the one trip (lanes §4).
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
| AIR-3.4 | crosswalk format: reviewed SKOS triples plus characteristic values on codes that name several things, as a `fnd:DerivedArtefact`. Crosswalks of OED's peril codes and an example house list, and the lookup that lifts codes to reference concepts at ingestion | `insurance/peril/crosswalk/` (the MORK mapping too, since MORK's own examples stay domain-neutral) |
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
S2 also changes Eligibility, and rebases onto AIR-3.2. AIR-3.3 merges before
[normative-rule-substrate](normative-rule-substrate.md) N1, which also changes `tools/mork_compilers/`
(epic §3b).

## AIR-3.1 in detail

**Machine:** R. **Branch:** `air/3.1-flat-hierarchy`. **Validation Pack:**
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

**Machine:** R. **Branch:** `air/3.2-set-readings`. **Validation Pack:**
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
    `docs/architecture/ontology-architecture.md` §3. (`solution-design-specification.md` does not
    cover Eligibility's semantics, so it is unchanged.) Then `mise run build:ontology-catalog` and `mise run
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

## AIR-3.3 in detail

**Machine:** R. **Branch:** `air/3.3-readings-swrl-owl`. **Validation Pack:**
[applied-insurance-reference-3.3](../validation/applied-insurance-reference-3.3.md).
**Decision:** ADR-A103 decisions 3 and 4.

**Blocked (2026-10-13).** Do not start until CCS slice HQ-6a.2 (`ccs/hq6a2-closures-compilers`) has
merged and AIR-3.3-Q1 is answered. HQ-6a.2 adds closed bindings to set readings and changes
`eligibility_ir.py`, `sparql_backend.py` and `test_set_readings.py`, and leaves SWRL and OWL
refusing set readings (HQ6a2-10), which this slice removes. HQ-6a.1 also changed the two examples
AIR33-04 to AIR33-06 read. The branch is created from `main` after that merge, not reused: the old
`air/3.3-readings-swrl-owl` held only the brief and is deleted.

**AIR-3.3-Q1.** What do SWRL and OWL do with a closed binding?

| Option | Consequence |
|---|---|
| (a) compile it as its open reading, with a mapping note | SWRL stays sound, since each rule it emits is fixed by one value and a closure only adds decisions SPARQL makes. OWL's open-world reading also ignores the closure, which fits design-time checks. Closures reach the reasoner routes as their open readings |
| (b) keep refusing closed bindings in SWRL and OWL | simpler, but closures never reach the reasoner routes |

Option (a) is the hypothesis to test. The brief below is amended with the answer.

**Invariant:** the SWRL backend derives only outcomes a set reading fixes from positive facts,
with heads swapped under negation, and every outcome it derives is the SPARQL reference's. The
OWL backend compiles `elg:SomeValue` as `∃path.C`, `elg:EveryValue` as `∀path.C ⊓ ∃path.⊤`,
and negation as a complement, for design-time checks only. Plans without a reading or negation
compile exactly as before.

No ontology changes, so no version bumps, catalog rows or tags. The examples are AIR-3.2's.

1. **Refusals removed.** `compile_rules` and `compile_classes` stop refusing plans for which
   `has_readings` holds. The IR's `has_readings` docstring stops naming the refusal. The other
   OWL refusals stay: unbound conditions, `elg:L14` plans (ADR-A100), and a `SingleValue` binding
   without the `elg:singleValued` claim.
2. **SWRL, concept plans.** The admitted rule is emitted under `SingleValue` and `SomeValue`.
   The denied rule is emitted under `SingleValue` and `EveryValue`. Each rule fires on one value,
   and one Permitted value fixes `SomeValue`, as one Denied value fixes `EveryValue`, so each
   derivation stays sound when a subject has several values.
3. **SWRL, interval plans.** The permit rules are emitted under `SingleValue` and `SomeValue`.
   Under `EveryValue` no rule is emitted: SWRL derives no Denied for an interval today, and
   Permitted needs every value. The mapping note says so, as it does for a unit-specific
   interval on a literal.
4. **SWRL, negation.** A negated plan's rules swap their heads: `exe:permittedUnder` and
   `exe:deniedUnder` for bound plans, `exe:impliesDecision` Permitted and Denied for question
   plans. Which rules are emitted is decided by the reading first (steps 2 and 3), then the heads
   are swapped. The negated medicine condition therefore derives Denied for a medic, and nothing
   else. Profile rules are unchanged: they read the condition's final decision.
5. **SWRL mapping notes** name the reading and negation. The module docstring gains a paragraph
   stating steps 2 to 4.
6. **OWL, readings.** `_along` gains the reading. Under `SingleValue` it is unchanged
   (`≤1 p ⊓ ∃p.…`, with the single-valued shape). Under `SomeValue` it is `∃p₁.∃p₂.…filler`, and
   under `EveryValue` `∀p₁.∀p₂.…filler ⊓ ∃p₁.∃p₂.…⊤`, with `rdfs:Literal` in place of
   `owl:Thing` where the path ends at a literal. A set-read binding needs no `elg:singleValued`
   claim, and gets no single-valued shape (ADR-A103 decision 3 relaxes ADR-A90 for it).
7. **OWL, negation.** A negated condition's class is its subject class intersected with the
   complement of the path restriction: `S ⊓ ¬(…)`. Under the open world this class also holds
   subjects the SPARQL reference leaves Undetermined, which is acceptable for design-time checks
   and stated in the module docstring.
8. **Tests:** `test_set_readings.py` loses AIR32-11's refusal test and gains the rows below. The
   reasoner rows skip when the harness jar is not built, as `test_reasoner.py` does.
9. **Docs:** `tools/mork_compilers/README.md` (the readings paragraph gains SWRL and OWL), the
   Eligibility README's evidence bindings paragraph (the OWL backend compiles claimed paths, and
   set-read paths without a claim), and ADR-A103 gains an implementation note as ADR-A100's.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AIR33-01 | a concept plan read `SomeValue`, and one read `EveryValue` / SWRL / the first has only the admitted rule, the second only the denied rule | L1 | + |
| AIR33-02 | an interval plan read `SomeValue`, and one read `EveryValue` / SWRL / permit rules, and no rule with a mapping note | L1 | + |
| AIR33-03 | a negated concept plan, question-based and bound / SWRL / heads swapped | L1 | + |
| AIR33-04 | the admissions example / SWRL through the harness / stem Permitted for ada and dee, no-medicine and the profile Denied for dee, nothing else | L2 | + |
| AIR33-05 | the trial example / SWRL through the harness / none-excluded Denied for pat-2, no Permitted derived | L2 | + |
| AIR33-06 | both examples, every condition and profile / SWRL and SPARQL / every SWRL derivation equals SPARQL's decision (soundness) | L2 | + |
| AIR33-07 | a `SomeValue` binding without the claim / OWL / `∃` restrictions, no `≤1`, no single-valued shape | L1 | + |
| AIR33-08 | an `EveryValue` binding over a two-step path, and one ending at a literal / OWL / `∀ ⊓ ∃⊤`, with `rdfs:Literal` at the literal end | L1 | + |
| AIR33-09 | one condition compiled under each reading / reasoner / `EveryValue` ⊑ `SomeValue`, claimed `SingleValue` ⊑ both, `SomeValue` ⋢ `EveryValue` | L2 | + |
| AIR33-10 | the admissions example / reasoner / stem ⊓ no-medicine satisfiable, the medicine condition ⊓ its negation unsatisfiable | L2 | + |
| AIR33-11 | a `SingleValue` binding without the claim, an unbound condition, an `elg:L14` plan / OWL / refused as before | L1 | − |
| AIR33-12 | a plan with readings / compiled twice / identical graphs | L1 | + |
| AIR33-13 | the existing compiler tests / unchanged / pass (non-weakening) | L1 | + |

## AIR-3.4 in detail

**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-3.4] …`, the
last being `[AIR-3.4] Handoff`. **Validation Pack:**
[applied-insurance-reference-3.4](../validation/applied-insurance-reference-3.4.md). **Decisions:**
ADR-A100 (decisions 4 and 5), ADR-A13 (MORK review). **Sketch:** MORK bridge §3, §4.1, §6, §7,
peril vocabulary §9.2. **Decided 2026-10-14:** AIR-3.4-Q1 and AIR-3.4-Q2 (below), at their
leanings.

**Invariant:** a crosswalk is a reviewed graph of SKOS mapping triples and characteristic values,
recorded as a derived artefact whose read set is the two scheme editions. Only an exact mapping
lifts a value to the reference, and a crosswalk is stale as soon as either edition changes.

**AIR-3.4-Q1, which lists.** Decided: OED's peril codes in full, published with the reference
because Oasis's licence allows it (PV-O6), and AIR-2.7's example house list, which has a code of
every shape MORK bridge §4.1 names. The CBAA cause-of-loss list (several hundred codes, sketch
§9.2) waits until its owner's terms are confirmed, and its review is a person's task (PV-O5), so it
is not in the trip.

**AIR-3.4-Q2, where a lifted value goes.** Decided: a derived property, `aeo:liftedPeril`
(`⊑ icm:peril`), written beside `aeo:peril` by the lift, never instead of it. The operative value
stays the drafter's (MORK bridge B1), a check written against the reference reads the lifted
value, and an inexact mapping writes nothing (B5). The alternatives, lifting inside Eligibility at
evaluation or replacing the recorded code, are a substrate change and a breach of B1.

### Files

The module's `crosswalk/` directory (ADR-A100 decision 4, MORK bridge §7). Each crosswalk is a
document of its own, `0.1.0`, with an `owl:Ontology` importing the peril vocabulary at the branch
version, and a README section in the peril module's README with its own `@output-file`.

| File | Ontology IRI | Content |
|---|---|---|
| `crosswalk/oed-perils.ttl` | `…/insurance/peril/crosswalk/oed` | the OED peril code list as a scheme (`oed:` prefix, each code a concept with its code as `skos:notation`), and its crosswalk to the cause scheme |
| `crosswalk/house-list.ttl` | `…/insurance/peril/crosswalk/house-list` | the crosswalk of `ex:HouseList` (AIR-2.7), an example, with its note saying so |
| `crosswalk/house-list-ingestion.ttl` | as an example, no `owl:Ontology` | the MORK mapping that looks codes up at ingestion |

The MORK mapping is an insurance example, so it lives here and not in `ontology/mork/examples/`,
whose examples stay domain-neutral (ADR-A-C2). The phase table's "`ontology/mork` examples" is
corrected to match.

### Crosswalk content

Each crosswalk is one `fnd:DerivedArtefact` node (the crosswalk), `prov:used` the two schemes'
version IRIs (its read set), with `prov:wasAttributedTo` a reviewer (an example reviewer in the
examples, and for OED the maintainer at verification) and evidence citing the source list's
publication. Its mapping triples, by code shape (MORK bridge §4.1):

| House code | Crosswalk |
|---|---|
| `FIRE` | `skos:exactMatch prl:T.FIR` |
| `FLOOD` | `skos:closeMatch prl:N.HYD.FLD`. The house definition includes surge, so it is not exact |
| `STORM` | `skos:narrowMatch prl:N.MET.TC`, `prl:N.MET.ETC`, `prl:N.MET.SCS`, `prl:N.MET.LWS` (the code is broader than each) |
| `QUAKE` | `skos:exactMatch prl:N.GEO.EQ` |
| `THEFT` | `skos:exactMatch prl:H.THF` |
| `CYBER` | `skos:exactMatch prl:C` |
| `LIGHTNING-FIRE` | `skos:exactMatch prl:N.MET.SCS.LTG`, with `prl:typicalMechanism prl-voc:Fire` on the code |
| `DELAY` | no cause match. `prl:typicalConsequence prl-voc:Delay` on the code |

For OED, the group codes map by membership of AIR-2.5's model groupings (a group code's notation is
already on its grouping), single codes by `skos:exactMatch` where AIR-2.3's `prl:CatModelCode`
notation put them, and by close, broad or narrow matches otherwise, each with a note on the
difference. The crosswalk agrees with those notations, and a test checks it.

### Code (`tools/peril_crosswalk.py`)

- `lift(graph, crosswalk)`: for each `aeo:peril` (and `aeo:unitPeril`) value with an exact mapping,
  write `aeo:liftedPeril` and one `fnd:DerivationRun`, as a separate graph. Close, broad and narrow
  mappings write nothing.
- `stale(crosswalk_graph, current)`: true when a scheme version the crosswalk used differs from the
  one in force.

The code-level characteristic values reach a loss cause through AIR-4.4's effective characteristics
derivation, which reads `prl:typicalMechanism` on whatever concept `aeo:peril` names, so no second
mechanism is needed.

### Ingestion (`crosswalk/house-list-ingestion.ttl`)

A MORK data mapping for a loss row with a cause code field: a `mork:Lookup` with
`mork:referenceDataPath skos:notation` against `ex:HouseList`, producing the `aeo:LossCause` with
its `aeo:peril`. The test compiles it with `tools/mork/src/mork2rml.py` and checks the triples map holds the
lookup. Running RML is not required, so the lift test starts from a graph shaped as the mapping
produces.

### Shapes (peril `constraints.ttl`)

| Shape | Rule | Severity |
|---|---|---|
| crosswalk targets | every mapping target resolves to a concept or a collection | violation |
| no mixed exactness | no code maps `skos:exactMatch` and `skos:broadMatch` to concepts in one `skos:broader` chain | violation |
| read set | a crosswalk names exactly two scheme versions in `prov:used` | violation |
| lifted from exact | an `aeo:liftedPeril` value is the target of an exact mapping of the `aeo:peril` beside it | violation |

This slice declares `aeo:liftedPeril` in the exposure spec's `losses-requirements-cover` region
(AIR-4.4 comes earlier in the trip), and the last shape goes with the exposure shapes.

### Tests

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AIR34-01 | both crosswalks / loaded / parse, every target resolves | L1 | + |
| AIR34-02 | the OED crosswalk / compared with AIR-2.3's notations / every exact match agrees | L1 | + |
| AIR34-03 | loss causes with `FIRE`, `FLOOD`, `STORM` / `lift` / `FIRE` lifted to T.FIR, nothing for the other two | L2 | + |
| AIR34-04 | the house crosswalk with the cause scheme's version changed / `stale` / true | L2 | − |
| AIR34-05 | a code mapped exact to N.HYD.FLD and broad to N.HYD.FLD.FLU / the shapes / violation | L1 | − |
| AIR34-06 | a hand-written `aeo:liftedPeril` from a close mapping / the shapes / violation | L1 | − |
| AIR34-07 | a `LIGHTNING-FIRE` cause with no recorded mechanism / AIR-4.4's derivation / effective mechanism Fire, defaulted | L2 | + |
| AIR34-08 | the ingestion mapping / `mork2rml` / compiles, with the lookup | L1 | + |
| AIR34-09 | every crosswalk / the documentation shape / each mapping's code has a note where the match is not exact | L1 | + |

## AIR-3.5 in detail

**Machine:** S (Copilot Business, moved from R on 2026-10-13). **Branch:** `air/applied-reference`,
commits `[AIR-3.5] …`, the last being `[AIR-3.5] Handoff`. **Validation Pack:**
[applied-insurance-reference-3.5](../validation/applied-insurance-reference-3.5.md). **Decisions:**
ADR-A100, ADR-A103. **Sketch:** MORK bridge §4.2, §4.3, peril vocabulary §6.8. **Milestone:** M2.

**Invariant:** a reference concept lowers to a list's code only through an exact mapping, a
list-to-list correspondence through the reference is exact only when both legs are, and the cyber
write-back check decides on the reference, is Undetermined with a reason on a flat list, and
decides exactly mapped codes of a crosswalked list.

### Code (`tools/peril_crosswalk.py`)

- `lower(graph, crosswalk, concept)`: the code mapped exactly to the concept, or else the code
  nearest above it, flagged inexact. A code is above a concept when it maps exactly to one of the
  concept's broader concepts, or by `skos:narrowMatch` to the concept or one of them (the code is
  the broader). Or else nothing, with a note. It never invents a code (MORK bridge §4.2).
- `compose(first, second)`: the list-to-list correspondences through the reference, each exact only
  when both legs are exact (MORK bridge §4.3), as a derived artefact whose read set is both
  crosswalks.

### Milestone M2 (`insurance/exposure/examples/m2.ttl`)

The cyber write-back profile of sketch §6.8, with three changes since the sketch: it binds
`aeo:effectiveAgency` and `aeo:effectiveMechanism` (AIR-4.4, Q11), the contracts are
`icm-voc:AgencyContract` and `icm-voc:MechanismContract`, and a second copy binds
`aeo:liftedPeril` for the crosswalked case. Loss causes and recorded decisions, by the SPARQL
backend:

| Case | Cause | Recorded | Decision |
|---|---|---|---|
| reference | C.NML.SWF | agency Accidental, mechanism Fire | Permitted |
| reference | C.MAL.RAN | agency MaliciousCriminal, mechanism Fire | Denied |
| reference | C.NML.CFG | agency Negligent, mechanism Explosion | Permitted |
| flat list, under `ex:london-market` | `CYBER` | agency Accidental, mechanism Fire | Undetermined, `exe:NoHierarchy` on the cyber condition |
| crosswalked, lifted profile | `CYBER`, lifted to C | agency Accidental, mechanism Fire | Permitted |
| crosswalked, lifted profile | `FLOOD` (close match, not lifted) | none | Undetermined, `exe:MissingCandidate` |

And the onset check of phase 3's test list: an existing cover whose `aeo:perilScope` is T.FIR and
N.MET.TC.WND, a condition requiring `Sudden` on the path `aeo:perilScope` then `prl:onset`, read
`elg:EveryValue`: Permitted, and Denied when N.CLI.DRT is added.

### Tests

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AIR35-01 | `lower` of T.FIR into the house list / called / `FIRE`, exact | L2 | + |
| AIR35-02 | `lower` of N.MET.TC.WND, and of T.NUC, into the house list / called / `STORM` flagged inexact, and no code with a note | L2 | − |
| AIR35-03 | `lower` of N.GEO.EQ.SHK into the house list / called / `QUAKE`, flagged inexact | L2 | + |
| AIR35-04 | `compose` of the house crosswalk and the OED crosswalk / called / `FIRE` to OED's fire code exact where both legs are, `FLOOD` inexact | L2 | + |
| AIR35-05 | M2 / SPARQL / the decisions in the table, with their diagnostics | L2 | + |
| AIR35-06 | M2 / SHACL / agrees with SPARQL | L2 | + |
| AIR35-07 | the onset check / SPARQL / Permitted, then Denied with N.CLI.DRT | L2 | + |
| AIR35-08 | the M2 file / every exposure shape / no result | L1 | + |

## Documentation deltas

| Document | Change | Slice |
|---|---|---|
| `ontology/eligibility/README.md`, examples | the A-100 law, the A-103 readings | 3.1, 3.2 |
| `tools/mork_compilers/README.md` | both laws in every backend | 3.1 to 3.3 |
| `docs/architecture/ontology-architecture.md` | Eligibility section, and the MORK section on proposals that end as crosswalks | 3.2, 3.4 |

## Exit gate

A-100 and A-103 Accepted and implemented. M2 demonstrated. MB-Q2 answered.
