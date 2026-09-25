<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Applied Ontology Readiness - Design Sketch

**Unit ID:** `applied-ontology-readiness`
**Status:** Design sketch for human review. No implementation is claimed.
**Trigger:** human request, 2026-09-25. Close the gaps an applied (domain)
ontology meets when it is built on LATTICE.
**Baseline:** commit `9a12da4`.
**Plan:** [applied-ontology-readiness.md](../plans/applied-ontology-readiness.md)
**Status record:** [applied-ontology-readiness.md](../status/applied-ontology-readiness.md)

## Premise

An applied ontology imports LATTICE layers, declares its own classes,
properties, concept schemes and conditions, and expects three things from the
substrate: that it can load LATTICE reproducibly, that its declarations mean
what the substrate documents, and that the compilers turn its declarations
into executable and checkable forms with provenance. Each gap below breaks one
of these for any applied ontology, independent of its domain.

## Worked examples (non-domain, per ADR-A-C2)

- **Clinical trial.** Admit adults with a solid tumour, excluding tumours of
  the central nervous system, with a dose ceiling of 2 mg per kg of body
  weight and a screening visit within 3 business days of consent. Two trial
  arms must not admit the same patient.
- **Employment.** Grant a relocation benefit to every job family except
  contractor grades. The benefit's notice period is 20 business days. A
  revised policy must not silently admit a job family the previous revision
  excluded.
- **Lending.** A facility limit is stated as USD 10 million or EUR 9 million,
  each figure authoritative in its own currency, with no conversion between
  them.
- **SaaS subscription.** A service credit is 10% of the monthly fee. A
  subscription agreement exists in two language versions, both
  authoritative, each expressing the same uptime obligation.

## Gaps

| ID | Area | Gap | Evidence |
|---|---|---|---|
| AO1 | Eligibility | Examples report warnings since `9a12da4`. The declaration warning also fires on admission profiles. Two examples carry older violations (L8 operational profile, profile structural properties) | Baseline pySHACL run (status record). `ontology/eligibility/shapes/constraints.ttl` |
| AO2 | Eligibility | Concept inclusion and exclusion (L10 to L13) landed without an ADR | commit `9a12da4` |
| AO3 | Eligibility | No concept-valued candidate. `elg:candidateValue` ranges over `qnt:Value`, and `hierarchical-match.ttl` uses it for a concept | `ontology/eligibility/README.md` §5 |
| AO4 | Loading | Version IRIs do not dereference. The per-layer catalogs are stale and machine-specific. No check that an import target exists | six `catalog-v001.xml` files. `surface/execution/job-family/` imports `surface/0.0.1` |
| AO5 | Versioning | The version check skips documents with no version IRI and runs in no CI workflow. The policy contradicts itself on PATCH. Bump level for import-only changes is undefined | `tools/ontology_version_check.py`, `.github/workflows/`, `ontology-versioning-policy.md` |
| AO6 | Compilation | Only interval conditions compile. Exact, set and hierarchical match, inclusion and exclusion, and profile aggregation are refused | [eligibility-compiler status](../status/eligibility-compiler.md) |
| AO7 | Compilation | Candidates are read from `elg:Question` only, never from the applied ontology's own properties | [mork-eligibility-compiler sketch](mork-eligibility-compiler.md) |
| AO8 | Compilation | No backend emits OWL classes for design-time subsumption, satisfiability and overlap checks | `tools/mork_compilers` |
| AO9 | Provenance | Surface and Executable provenance terms are not aligned with PROV-O, which Foundation imports. The Foundation derived-artefact contract is undecided | [surface outstanding items](../status/surface-outstanding-items.md) §1.3 |
| AO10 | Quantification | No derived value space for rates (open question 4) | `ontology/quantification/README.md` §13 |
| AO11 | Quantification | No calendar binding for business-day extents (open question 2) | as above |
| AO12 | Quantification | No way to state one bound independently in several units, without conversion | `qnt:Bound` has one value on one space |
| AO13 | Instrument | `ins:inProvision` is functional, so one obligation cannot be expressed by several provisions | `ontology/instrument/README.md` §4 |

Already closed, and not repeated here: Quantification `unresolvedReason`
domain and Instrument `ins:Element` disjointness (`9a12da4`), and Surface and
Eligibility honouring `voc:SchemeBinding` (`vocabulary-temporal-binding`).

## Invariants to protect

1. Every example under `ontology/<layer>/examples/` validates against its
   layer's shapes with no violation and no unexplained warning.
2. Any LATTICE document loads, with its import closure, from a checkout with
   no machine-specific configuration.
3. A version IRI identifies exactly one content of its document.
4. Every compiled form of a condition (SPARQL, SHACL, SWRL, OWL) derives from
   one IR plan, so no two forms can disagree about what the condition means.
5. No backend derives `Undetermined` from absence of evidence where ADR-A24
   forbids it, and every `Undetermined` carries a diagnostic.
6. Substrate text stays domain-neutral (ADR-A-C1, ADR-A-C2).

## Proposed deliverables

| Gaps | Decision | Deliverable |
|---|---|---|
| AO1, AO2 | [ADR-A87](../../architecture/decisions/ADR-A87-eligibility-concept-inclusion-and-exclusion.md) | Examples declare concepts, each with a comment naming the warning its removal raises. The declaration warning skips profiles. An example check in `mise` |
| AO5 | [ADR-A86 addendum](../../architecture/decisions/ADR-A86-ontology-semantic-versioning.md#addendum-2026-09-25-guarantees-consumers-rely-on) | Check flags missing version IRIs and runs in CI. Policy corrected. Job-family modules regenerated |
| AO4 | [ADR-A88](../../architecture/decisions/ADR-A88-ontology-import-resolution-for-consumers.md) | Generated root catalog, directory stubs, resolution check, consumer guide |
| AO3, AO6 | [ADR-A89](../../architecture/decisions/ADR-A89-eligibility-ir-concept-conditions-and-profile-aggregation.md) | Concept candidate, concept plans, closure modes, profile aggregation, diagnostics |
| AO7 | [ADR-A91](../../architecture/decisions/ADR-A91-eligibility-candidate-evidence-binding.md) | Evidence bindings from domain properties |
| AO8 | [ADR-A90](../../architecture/decisions/ADR-A90-eligibility-design-time-owl-class-backend.md) | OWL backend and reasoner checks |
| AO9 | [ADR-A92](../../architecture/decisions/ADR-A92-derived-artefact-contract-and-prov-o-alignment.md) | `fnd:DerivedArtefact`, PROV-O alignment of Surface and Executable |
| AO10 to AO13 | ADRs drafted at the start of Phase C | See below |

### Phase C candidates (no ADR yet)

- **AO10 derived rates.** Declare a rate space as the quotient of two value
  spaces (`qnt:DerivedValueSpace`, numerator and denominator spaces), so
  "2 mg per kg" and "10% of the monthly fee" are typed values rather than
  dimensionless numbers. A percentage is the case where both spaces coincide.
  The quotient's evaluation stays with operation capabilities.
- **AO11 calendar binding.** Quantification's open question 2 leans towards
  binding a calendar through `qnt:UnitContract`. A business-day unit is then
  a unit whose conversion to elapsed days needs a calendar context, the same
  `Contextual` conversion rule Quantification already has. Calendar content
  stays deployment-supplied.
- **AO12 alternative bounds.** A bound set whose members are alternative
  statements of one limit, one per unit, with an explicit rule for how a
  candidate in a given unit is compared (only against the member in its own
  unit, `Undetermined` if none). No conversion is implied.
- **AO13 provision attachment.** Remove `owl:FunctionalProperty` from
  `ins:inProvision`. Its inverse, `ins:hasObligation`, is already
  unrestricted. Under ADR-A86 this widens a cardinality and is MINOR. It also removes an
  entailment (two provisions of one obligation are no longer inferred equal),
  which the ADR must state as a judgement call.

## Proposed phases

| Phase | Slices | Gate |
|---|---|---|
| A. Consumable baseline | AOR-1 records, AOR-2 examples, AOR-3 versioning guarantees, AOR-4 catalog | No new semantics. Every example conforms, every import resolves |
| B. Executable coverage | AOR-5 to AOR-11 | Concept conditions, profiles and evidence bindings compile to every backend, with SPARQL parity |
| C. Substrate extensions | AOR-12 to AOR-17 | Each slice gated on its own ratified ADR |

Details, dependencies and token estimates are in the
[plan](../plans/applied-ontology-readiness.md).

## Coordination with other units

- `eligibility-compiler`: Phase B carries that unit's deferred items (other
  condition kinds, profile aggregation). Its Part B reasoning harness
  (ADR-A83) gates AOR-10 and AOR-11.
- `temporal-binding-consumer-hardening`: its Finding 1 option decides how a
  resolution instant enters compilation. AOR-6 follows the same option.
- `ontology-semantic-versioning`: AOR-3 implements the proposed ADR-A86
  addendum. That unit's own slices are unchanged.
- Surface outstanding items §1.3 and §3.1 are resolved by ADR-A92, if
  accepted.

## Deliberate non-coverage

- Serving documents at their IRIs (ADR-A88 item 5).
- Changing ontology IRIs to the `…/lattice/` base (ADR-A86 addendum item 4).
- Semantics for `elg:DimensionConsistent`.
- The ADR-A03 question of whether an admission profile should carry a match
  strategy and wildcard policy at all (see open questions).
- Repairing `tools/literate_extract.py` drift across the core layers, already
  recorded by `ontology-semantic-versioning`.
- SPC integration.

## Open questions

1. **Profiles as conditions.** ADR-A03 makes `elg:AdmissionProfile` a
   condition, so `elg:ConditionShape` requires a profile to declare a match
   strategy, compatibility operation and wildcard policy. The interval example
   gives its profile `elg:SetMembership` to satisfy the shape. AOR-2 follows
   that convention. Should `ConditionShape` exempt profiles instead?
2. **Example scope.** Should AOR-2 also bind `hierarchical-match.ttl` to a
   scheme contract (`elg:constrainedByContract`), so the example is
   evaluable under L9? Recommended, at a small cost.
3. **Phasing.** Should this unit become an epic with one plan per phase, given
   seventeen slices?
