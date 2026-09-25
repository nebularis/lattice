<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Applied ontology readiness

**Unit ID:** `applied-ontology-readiness`
**Status:** Proposed, awaiting human review before implementation
**Trigger:** human request, 2026-09-25
**Sketch:** [applied-ontology-readiness.md](../sketches/applied-ontology-readiness.md)
**Status record:** [applied-ontology-readiness.md](../status/applied-ontology-readiness.md)
**ADRs:** [A-87](../../architecture/decisions/ADR-A87-eligibility-concept-inclusion-and-exclusion.md),
[A-88](../../architecture/decisions/ADR-A88-ontology-import-resolution-for-consumers.md),
[A-89](../../architecture/decisions/ADR-A89-eligibility-ir-concept-conditions-and-profile-aggregation.md),
[A-90](../../architecture/decisions/ADR-A90-eligibility-design-time-owl-class-backend.md),
[A-91](../../architecture/decisions/ADR-A91-eligibility-candidate-evidence-binding.md),
[A-92](../../architecture/decisions/ADR-A92-derived-artefact-contract-and-prov-o-alignment.md),
and the [ADR-A86 proposed addendum](../../architecture/decisions/ADR-A86-ontology-semantic-versioning.md#proposed-addendum-2026-09-25-guarantees-consumers-rely-on).
All Proposed.

## Scope

Close gaps AO1 to AO13 from the sketch, in three phases. Phase A changes no
semantics. Phase B extends the Eligibility compilers. Phase C extends
Foundation, Surface, Executable, Quantification and Instrument. No slice
starts before the ADR it names is ratified. Phase A slices AOR-2 and AOR-3 are
detailed to implementation level. Phase B slices are detailed to module, file
and test-case level. Phase C slices are outlined and are detailed when their
ADRs are drafted.

## Conventions for every slice

- Default execution mode. The agent writes, then hands off a "Commands to run"
  block. The human runs it.
- Each slice delivers its Validation Pack at
  `docs/developer/validation/applied-ontology-readiness-<slice>.md`, updates
  the status record and `docs/developer/INDEX.md`, and edits any normative
  document it contradicts in the same slice.
- Every ontology change is classified under ADR-A86 and runs the
  import-pinning cascade checklist. The classification of import-only changes
  follows addendum item 1 once ratified. Until then the slice states its
  classification and asks.
- SHACL validation in tests uses the union of the example and the layer's
  `spec/*.ttl` as data, so `sh:targetClass` reaches subclass instances, with
  pySHACL `advanced=True` and `inference="none"`.
- Substrate text and examples stay domain-neutral (ADR-A-C2).

## Phase A: Consumable baseline

### AOR-1: Governance records (this slice)

ADRs A-87 to A-92 (Proposed), the ADR-A86 proposed addendum, the sketch, this
plan, the status record, the ADR catalogue rows, and `INDEX.md` entries. L0.
Gate: human review of the ADRs and of the open questions in the sketch.

### AOR-2: Eligibility examples and the declaration warning

**Invariant:** every Eligibility example validates with no violation and no
warning. The declaration warning targets conditions that match candidates
directly (ADR-A87 item 4).

**Depends on:** ADR-A87 ratified. Sketch open questions 1 and 2 answered.

**Changes:**

1. `ontology/eligibility/examples/hierarchical-match.ttl`
   - `ex:hierarchical-condition` gains `elg:requiredConcept ex:fire`, preceded
     by a comment: `# Removing elg:requiredConcept raises
     elg:ConceptConditionDeclarationShape (sh:Warning), because the condition
     would state nothing to match against.`
   - `ex:hierarchical-profile` declares `elg:matchStrategy
     elg:HierarchicalMatch`, `elg:compatibilityOperation elg:AllRequired` and `elg:wildcardSemantics
     elg:NoWildcard`, following the interval example's convention (open
     question 1). This clears three pre-existing `elg:ConditionShape`
     violations.
   - `ex:decision` gains `elg:usesOperationalProfile ex:reference-profile`,
     with `ex:reference-profile a elg:OperationalProfile`. This clears the
     pre-existing L8 violation.
   - If open question 2 is accepted, the condition gains
     `elg:constrainedByContract` to a `voc:SchemeContract` bound to a
     `voc:ConceptScheme` holding the three concepts.
   - The candidate keeps `elg:candidateValue` until AOR-5 introduces
     `elg:candidateConcept`.
2. `ontology/eligibility/examples/condition-taxonomy.ttl`
   - Adds the `skos:` prefix and four concepts: `ex:full-time`,
     `ex:part-time` (an employment basis), `ex:tier-standard`,
     `ex:tier-premium` (a subscription tier).
   - `ex:exact-condition` gains `elg:requiredConcept ex:full-time`.
     `ex:set-condition` gains `elg:requiredConcept ex:tier-standard,
     ex:tier-premium`. Each carries the comment from change 1.
3. `ontology/eligibility/examples/interval-containment.ttl`
   - `ex:decision-1` gains `elg:usesOperationalProfile` as in change 1. Its
     declaration warning on `ex:profile-a` is cleared by change 4, not by
     giving the profile a concept.
4. `ontology/eligibility/shapes/constraints.ttl` and its mirror in
   `ontology/eligibility/README.md` §7: the first `sh:sparql` of
   `elg:ConceptConditionDeclarationShape` adds
   `FILTER NOT EXISTS { $this elg:hasCondition ?member }`. The two blocks stay
   identical.
5. Version: `eligibility/spec` 0.3.0 → 0.3.1 (PATCH, a shape brought into line
   with documented intent), in `spec/eligibility.ttl` and the README header.
   Cascade to every importer of `lattice/eligibility/0.3.0`:
   `eligibility/vocab/eligibility-vocab.ttl`, `instrument/spec/instrument.ttl`
   and README, `behaviour/spec/behaviour.ttl` and README,
   `applied/capacity/spec/applied_capacity_execution_spec_capx_Version2.ttl`.
   The enumeration is re-run before and after editing.
6. New `tools/test_eligibility_examples.py` (pytest, rdflib and pySHACL, both
   existing root dependencies).
7. `mise.toml`: new task `check:eligibility-examples` (folded into
   `check:ontology-catalog` on 2026-09-25, which runs every `tools/test_*.py`)
   (`python -m pytest tools/test_eligibility_examples.py -q`), added to the
   aggregate `check`.
8. `tools/README.md` lists the new test.

Examples declare no `owl:Ontology`, so changes 1 to 3 carry no version impact.

**Test cases:**

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AOR2-01 | `hierarchical-match.ttl` / validated / no results | L1 | + |
| AOR2-02 | `condition-taxonomy.ttl` / validated / no results | L1 | + |
| AOR2-03 | `interval-containment.ttl` / validated / no results | L1 | + |
| AOR2-04 | `hierarchical-match.ttl` without `ex:hierarchical-condition`'s required concept / validated / exactly one declaration warning, focused on that condition | L1 | - |
| AOR2-05 | as AOR2-04 for `ex:exact-condition` | L1 | - |
| AOR2-06 | as AOR2-04 for `ex:set-condition` | L1 | - |
| AOR2-07 | a profile with `elg:hasCondition` and a concept match strategy, no concepts / validated / no declaration warning | L1 | + |
| AOR2-08 | a condition with `SetMembership`, no concepts, no `elg:hasCondition` / validated / one declaration warning | L1 | - |
| AOR2-09 | a condition whose excluded concept lies outside every required concept / validated / one `elg:ReachableExclusionShape` warning | L1 | - |
| AOR2-10 | the shape in `constraints.ttl` and the README §7 block / parsed / isomorphic | L3 | + |

**One command:** `mise run check:ontology-catalog` (originally `check:eligibility-examples`).
**Also run:** `mise run check:ontology-versioning`, and
`grep -rl 'lattice/eligibility/0.3.0' ontology tools` returns nothing.
**Artefacts to inspect:** the three example diffs and their comments.
**Adversarial probe:** revert change 4 and show AOR2-03 and AOR2-07 fail.
**Non-coverage:** other layers' examples (a repository-wide example check is a
candidate follow-up), and compiled evaluation of the examples (AOR-5, AOR-6).
**Estimate:** 80k tokens.

### AOR-3: Versioning guarantees

**Invariant:** a version IRI identifies one content, and CI enforces it.

**Depends on:** ADR-A86 and its addendum ratified.

**Changes:**

1. `tools/ontology_version_check.py` fails for a document under a `spec/` or
   `vocab/` directory, or under `ontology/applied/*/spec/`, that declares
   `owl:Ontology` without `owl:versionIRI`. Examples and test fixtures stay
   exempt (nine MORK example and test documents today).
2. New `tools/test_ontology_version_check.py` turns the manual mutation probe
   recorded by `ontology-semantic-versioning` into tests.
3. `.github/workflows/platform.yml`: the Python job checks out with
   `fetch-depth: 0` and runs
   `python tools/ontology_version_check.py --base-ref origin/main`.
4. `docs/architecture/ontology-versioning-policy.md`: the cascade checklist
   applies to every bump, and the propagation rule from addendum item 1 is
   added to "What changes the number".
5. The four modules under `ontology/surface/execution/job-family/` are
   regenerated with the Surface CLI from `ontology/surface/examples/employment-job-family.ttl`,
   with the `produced_at` recorded in their manifest, so they import
   `lattice/surface/0.3.0`. The regeneration command is recorded in the status
   record.

**Test cases:** content changed with version unchanged is flagged (-).
Content and version changed together pass (+). An untouched file passes (+).
A `spec/` document without a version IRI is flagged (-). An example document
without one passes (+). A document that gains `owl:Ontology` in the change
without a version IRI is flagged (-). The job-family modules import only IRIs
declared in the tree (+, checked by AOR-4's tool once it exists, by grep until
then). All L1.

**One command:** `python -m pytest tools/test_ontology_version_check.py -q`.
**Non-coverage:** changing ontology IRIs (addendum item 4).
**Estimate:** 90k tokens.

### AOR-4: Consumer catalog and import resolution

**Invariant:** every LATTICE document loads with its import closure from a
checkout, with no machine-specific configuration (ADR-A88).

**Depends on:** ADR-A88 ratified. AOR-3 (job-family imports fixed).

**Changes:**

1. New `tools/ontology_catalog.py` with three commands. `write` generates
   `ontology/catalog-v001.xml` (every ontology IRI and version IRI declared
   under `ontology/`, relative paths, external imports listed explicitly) and
   the directory stubs. `check` fails on drift, on an import target with no
   entry, and on an entry whose file does not declare its IRI. `closure` loads
   a document's import closure into an `rdflib` graph through the catalog.
2. The six existing `catalog-v001.xml` files are replaced by generated stubs.
   The `mork/spec` catalog's `Mork.owl` mapping is kept as an entry if
   `Mork.owl` still exists.
3. New `tools/test_ontology_catalog.py`.
4. `mise.toml`: `build:ontology-catalog` and `check:ontology-catalog`, the
   latter added to the aggregate `check`. CI runs the check.
5. `docs/architecture/ontology-architecture.md` §2 gains a "Consuming LATTICE
   from an applied ontology" paragraph: pin a commit, chain the catalog with
   `nextCatalog`, upgrade by the ADR-A86 cascade checklist, treat every bump as
   potentially breaking at major version zero, run the consumer's own gate.
6. `docs/architecture/ontology-versioning-policy.md`: regenerating the catalog
   is a step of every bump.

**Test cases:** every import in the tree resolves (+). A removed catalog entry
is reported (-). An entry pointing at a file that declares a different IRI is
reported (-). A hand edit to the catalog is reported as drift (-). The closure
of `behaviour/spec/behaviour.ttl` loads and contains a term from each of its
transitive imports (+). A fixture applied ontology in a temporary directory,
with its own catalog chaining to LATTICE's by relative path, loads its closure
(+). Generation is byte-identical across two runs (L2, +). A Protégé load of
one spec document through its stub (manual, recorded in the VP, and the
ADR-A88 open question).

**One command:** `mise run check:ontology-catalog`.
**Non-coverage:** serving documents at their IRIs.
**Estimate:** 140k tokens.

## Phase B: Executable coverage

All Phase B slices touch `tools/mork_compilers` and at most one ontology
layer. Each adds cases to `test/conformance/` so ADR-A28 parity covers them.
Each depends on AOR-2 and on the ADRs named.

| Slice | Scope | Modules | Depends on | Level | Estimate |
|---|---|---|---|---|---|
| AOR-5 | `elg:candidateConcept`. IR concept plan for `ExactMatch` and `SetMembership` with required and excluded concepts. SPARQL backend. Examples migrated from `candidateValue`. Eligibility MINOR with cascade | `ontology/eligibility`, `tools/mork_compilers` | A-89 | L1, L2 | 150k |
| AOR-6 | `HierarchicalMatch` in the IR. Scheme resolution through `tools/vocabulary` with explicit instant and scope. `QueryTime` closure in SPARQL. The ADR-A87 decision table, including L11 | `tools/mork_compilers` | AOR-5, and the `temporal-binding-consumer-hardening` Finding 1 decision | L1, L2 | 180k |
| AOR-7 | `Expanded` closure. SHACL and SWRL backends for concept plans. `exe:ConceptMatchPlan` and the diagnostic vocabulary. Executable MINOR | `tools/mork_compilers`, `ontology/mork` | AOR-6 | L1, L2 | 180k |
| AOR-8 | Profile aggregation for `AllRequired` and `AnySufficient` on all three backends. `DimensionConsistent` refused with a diagnostic | `tools/mork_compilers` | AOR-7 | L1, L2 | 130k |
| AOR-9 | `elg:EvidenceBinding`, `elg:EvidenceStep`, `elg:aboutSubject`. The IR reads candidates through bindings. Eligibility MINOR with cascade | `ontology/eligibility`, `tools/mork_compilers` | A-91, AOR-8 | L1, L2 | 180k |
| AOR-10 | OWL backend: hierarchy and condition classes, `exe:OwlArtefact`, sibling-disjointness option | `tools/mork_compilers`, `ontology/mork` | A-90, AOR-9, the path encoding decision, and the ADR-A83 harness | L1, L4 | 170k |
| AOR-11 | Profile classes and the subsumption, satisfiability and overlap checks through the harness CLI | `tools/mork_compilers` | AOR-10 | L4 | 150k |

**Test-case outline for Phase B.** Each slice's VP carries, as applicable:

- one positive case per decision-table row (Permitted, Denied, Undetermined)
  per strategy
- exclusion precedence (L10), a candidate above an exclusion (L11), and an
  exclusion-only condition (L12)
- a scheme with a scoped binding resolved at two instants either side of its
  handover, giving different plans, and a refusal when the instant is missing
- SPARQL and each other backend agreeing on every shared corpus case
  (ADR-A28)
- no SWRL rule deriving `Undetermined`, checked over the generated rules (-)
- every `Undetermined` carrying a diagnostic
- determinism: two compilations of the same inputs give identical artefact
  hashes (L2)
- for AOR-10 and AOR-11: a revised profile that admits a new concept is
  reported as not subsumed (-), a profile with an exclusion covering its only
  inclusion is unsatisfiable (-), two profiles with disjoint required concepts
  do not overlap only when the disjointness option is set (+ and -)

Each Phase B slice's single command is `mise run check:python-root` until a
`check:mork-compilers` task exists. AOR-5 adds that task (running
`python -m pytest tools/mork_compilers -q`) and wires it into `check`.

## Phase C: Substrate extensions

Each slice is gated on the ADR named, drafted 2026-09-25. Each is
an ontology change with the ADR-A86 cascade. Test cases are fixed when the ADR
is ratified.

| Slice | Scope | Decision | Version impact | Estimate |
|---|---|---|---|---|
| AOR-12 | `fnd:DerivedArtefact`, `fnd:DerivationRun`, derivation kinds in Foundation vocab. `srf:DerivedArtefact` alignment. Carries the ADR-A91 step-list lift if accepted by then | A-92 | Foundation, Surface MINOR. Foundation cascades to every layer | 200k |
| AOR-13 | Executable aligned directly to PROV-O, without importing Foundation (ADR-A92 item 3 as rewritten) | A-92 | Executable MINOR | 90k |
| AOR-14 | Derived rate spaces (sketch AO10) | [A-93](../../architecture/decisions/ADR-A93-quantification-derived-rate-spaces.md) | Quantification MINOR, cascades | 150k |
| AOR-15 | Calendar binding through `qnt:UnitContract` (AO11) | [A-94](../../architecture/decisions/ADR-A94-quantification-calendar-binding.md) | Quantification MINOR, cascades | 150k |
| AOR-16 | Alternative bounds stated per unit (AO12) | [A-95](../../architecture/decisions/ADR-A95-quantification-alternative-bounds.md) | Quantification MINOR, cascades | 120k |
| AOR-17 | `ins:inProvision` no longer functional (AO13) | [A-96](../../architecture/decisions/ADR-A96-instrument-provision-attachment.md) | Instrument MINOR, cascades | 60k |

AOR-14 to AOR-16 each change Quantification. If ratified together they should
land as one Quantification bump, to cascade once.

## Documentation obligations

| Document | Change | Slice |
|---|---|---|
| `docs/architecture/decisions/` | A-87 to A-92, A-86 addendum, catalogue | AOR-1 |
| `docs/architecture/decisions/` | Phase C ADRs | AOR-14 to AOR-17 |
| `ontology/eligibility/README.md` | shape mirror and version (AOR-2), new terms (AOR-5, AOR-9) | AOR-2, AOR-5, AOR-9 |
| `docs/architecture/ontology-versioning-policy.md` | propagation rule, catalog step | AOR-3, AOR-4 |
| `docs/architecture/ontology-architecture.md` | §2 consumer paragraph (AOR-4), §3 status rows, §11 items | AOR-4 onwards |
| `ontology/mork/README.md`, `tools/mork_compilers` docs | new plans, backends, closure modes | AOR-5 to AOR-11 |
| `ontology/foundation/README.md`, `ontology/surface/README.md` | new and aligned terms | AOR-12 |
| [eligibility-compiler status](../status/eligibility-compiler.md) | deferred items marked as carried here | AOR-5 |
| [surface outstanding items](../status/surface-outstanding-items.md) §1.3, §3.1 | closed on AOR-12 | AOR-12 |
| `docs/developer/INDEX.md`, status record | every slice | all |
| Root `README.md`, `docs/architecture/solution-design-specification.md`, `data-architecture.md`, `ux-design.md` | checked, no change planned. No new directory is introduced | none |

## Acceptance

Phase A closes when AOR-2 to AOR-4 are signed off and `mise run check` is
green with the new tasks included. Phase B closes when AOR-5 to AOR-11 are
signed off and the shared conformance corpus covers every concept strategy and
both evaluable compatibility operations. Phase C slices close individually.

## Token budget

| Phase | Estimate |
|---|---|
| A (AOR-1 to AOR-4) | 460k, of which AOR-1 about 150k |
| B (AOR-5 to AOR-11) | 1.14M |
| C (AOR-12 to AOR-17) | 770k plus ADR drafting, about 40k per ADR |

Estimates cover agent input and output for authoring and one round of fixes
from human-reported failures. Actuals are recorded in the status record.
