<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Current LATTICE projection plan

Date: 2026-09-18  
Status: Consolidated working plan  
Scope: Surface, MORK, Eligibility executable compilation, and related validation

## 1. Purpose

This document consolidates the planning material under `ontology/surface/docs` into one
current execution plan. It combines the unified Surface-MORK delivery plan,
the live outstanding-task trackers, the MORK Eligibility enhancement design,
the Surface design sketch, the X6 and CSO/FBO analyses, and the Phase 7
runbook.

Where older documents conflict with the current repository, this document uses
the following authority order:

1. Current code and passing tests
2. `ontology/surface/docs/surface-mork-unified-projection-outstanding-tasks.md`
3. `ontology/surface/docs/OUTSTANDING-ITEMS.md`
4. Accepted ADRs under `docs/architecture/decisions`
5. `surface-mork-unified-projection-delivery-plan.md`
6. Earlier design notes and superseded documents

`OUTSTANDING-ITEMS 2.md` is superseded. Earlier statements in
`MorkEnhancements.md` that describe only an RML compiler are historical and no
longer describe the repository.

## 2. Architectural decision

LATTICE uses one top-level authoring model for projection:

```text
Domain and substrate declarations
        |
        v
Surface contracts: Promotion, Index, Projection
        |
        v
Surface validation and normalisation
        |
        v
MORK mapping graph
        |
        v
Deterministic compiler backends
        |
        v
RML, SPARQL, SHACL, SWRL, and future runtime artefacts
```

Surface is the author-facing contract layer. MORK is the machine-facing,
provenance-rich mapping graph. The internal implementation is staged, but the
author does not need to author raw MORK internals.

Surface has three subsystems:

- **Promotion**: restate a reachable value as a direct property.
- **Index**: create retrieval symbols, memberships, direct properties, and
  closure relations.
- **Projection**: declare richer mapping intent involving construction,
derivation, joins, or expansion, then lower it into MORK.

No third standalone projection language should be introduced.

## 3. Semantic boundaries

### Surface owns

- author-facing projection contracts
- read paths and deterministic restatement
- index and closure declarations
- fidelity, signature scope, authority, and realisation policy
- generated-surface read sets, hashes, freshness, and invalidation
- Surface-to-MORK lowering

### MORK owns

- machine-readable mapping graphs
- mapping DAGs and precedence
- parameter bindings and targeting specifications
- generative mapping classification
- mapping provenance, governance state, versioning, supersession, and effective dates
- compiler-facing mapping intent

### Backend compilers own

- executable IR and target-specific compilation
- SPARQL, SHACL, SWRL, RML, and future native target emission
- target validation and backend-specific limitations

### Eligibility owns

- declarative business semantics
- conditions, strategies, range sets, decisions, and profiles
- three-valued semantic outcomes

Eligibility must not depend on OWL alone for interval arithmetic, missing-data
handling, or three-valued evaluation.

## 4. Decisions already made

- X6 remains in Surface. Exact or exact-crosswalk source-signature promotions
  may target authored properties only when materialised. Lossy promotions must
  use generated properties. Definition-only authored-property chains remain
  prohibited.
- Surface is the top-level Projection authoring layer and lowers into MORK.
- `mork:ProjectionMapping` is present and Surface MORK interoperation is
  implemented.
- Eligibility L9 was replaced with a semantic closure law. The old unscoped
  `elg:HierarchicalClosureRule` was removed. Materialised closure belongs to
  governed generated surfaces.
- `elg:constrainedByContract` is the Eligibility-to-Vocabulary binding path.
- Surface acts only on `srf:NoEntailment` today. Richer entailment regimes are
  refused explicitly rather than silently under-compiled.
- `RangePartitionPopulation`, deeper stacking, and `ExternalIndex` remain
  deferred.
- Generated surface authority is capped below authoritative status.
- The root Python environment is managed by `pyproject.toml` and
  `requirements-lock.txt`. The retained GitHub Action is manual-only.

## 5. Current implementation status

| Phase | Current status |
|---|---|
| 0. Architecture and ADR lock | Complete |
| 1. Surface Projection vocabulary and shapes | Complete |
| 2. Surface compiler and entailment guard | Verified |
| 3. Surface-to-MORK lowering | Verified for current scope |
| 4. MORK ontology/governance/versioning | Implemented and SHACL-verified for current fixtures |
| 5. Compiler family and Eligibility IntervalContainment slice | Verified |
| 6. Eligibility tranche | Absorbed into Phase 5 for current slice |
| 7. Provenance and invalidation | Complete for stack depth 1 |
| 8. Conformance and parity | Complete for current Surface/Eligibility scope |
| 9. Migration and rollout | Not started |
| 10. Scale and optimisation | Not started |

### Verification evidence

- Surface suite: 61 tests passing.
- MORK compiler suite: 15 tests passing.
- Combined compiler tests in the clean locked environment: 76 passing.
- Surface extraction check: four artefacts consistent with `ontology/surface/README.md`.
- Generated interval SPARQL returns `Permitted` for the worked example.
- MORK governance SHACL passes under `pyshacl`.
- Generated Eligibility SHACL passes the valid case and rejects missing
  candidate evidence and an out-of-range candidate.
- Shared Surface parity passes 16 comparisons across three cases:
  employment index, SaaS multi-hop promotion, and clinical crosswalk
  promotion.
- Phase 8 gate passes through `python -m tools.phase8_conformance`.
- Clean temporary environment installs from `requirements-lock.txt` and passes
  the compiler and conformance gates.

## 6. MORK and Eligibility delivery

### 6.1 MORK compiler family

The repository now has:

- existing RML tooling
- shared Eligibility IR for `IntervalContainment`
- SPARQL backend producing `mork:QueryTemplate`
- SHACL backend producing generated shapes
- SWRL backend producing positive-only rules
- `ontology/mork/spec/Executable.ttl`
- Foundation-aligned MORK governance and versioning

The current Eligibility compiler intentionally does not yet provide:

- a native backend
- profile-level aggregate artefacts
- runtime result tracking
- machine-readable diagnostic result resources
- non-IntervalContainment strategies
- a domain-facing executable projection contract

### 6.2 Eligibility next tranche

After the current verified slice, implement in this order:

1. Profile-level `AllRequired` and `AnySufficient` artefacts.
2. Explicit executable result and diagnostic vocabulary.
3. Runtime result tracking for `EvaluationRun`, `ConditionResult`,
   `ProfileResult`, and `Diagnostic`.
4. The domain-facing Executable Projection Contract, or a documented ADR
   rejection of it. The preferred direction is to keep it within the unified
   Surface Projection model rather than create a third authoring language.
5. Typed adapters such as decimal literal to Quantification value.
6. Additional strategies: ExactMatch, SetMembership, and Wildcard.
7. SWRL expansion only for semantics that remain positive and monotonic.

The native backend stays undefined until a concrete runtime artefact and
consumer exist.

## 7. Phase 7: provenance and invalidation

Phase 7 is complete for the current stack-depth-1 scope.

Implemented in `tools/surface/invalidation.py`:

- recorded read-set digest comparison
- conservative stale detection for changed or missing inputs
- read-set extraction from generated manifests
- transitive SurfaceSource impact propagation
- Surface contract changes propagated through `mork:mappingFor`
- MORK dependency propagation through `mork:dependsOnMapping`
- generated artefact propagation through `mork:generatedBy`
- executable-plan artefact propagation through `exe:compiledFromMapping` and
  `exe:producesArtefact`
- broad regeneration for profile changes
- broad regeneration for canonicalisation changes
- deterministic `RegenerationPlan` output

The operational procedure is in
`ontology/surface/docs/phase7-invalidation-regeneration-runbook.md`.

Deeper stacking remains deferred until the system has:

- transitive artefact-hash freshness
- surface DAG cycle rejection
- stale-input rejection at every stack level
- measured regeneration impact cost
- a formal profile identity representation in generated records

## 8. Phase 8: conformance and parity

Phase 8 is complete for the current Surface/Eligibility validation scope.

The shared conformance manifest supports explicit Surface cases using:

- `ex:surfaceContractFile`
- `ex:surfaceContractKey`

The public command is:

```bash
python3 -m tools.surface.cli parity \
  --shared-corpus test/conformance/manifest.ttl \
  --root .
```

The CI-equivalent local gate is:

```bash
python3 -m tools.phase8_conformance
```

The GitHub Action remains committed at
`.github/workflows/phase8-conformance.yml` but is manual-only while package
management is being stabilised.

Remaining outside the current Phase 8 bar:

- Behaviour automation against the shared corpus
- SWRL reasoner execution
- OWL consistency checking
- DefinitionOnly parity under a reasoner
- broader Projection and domain-binding corpus cases

## 9. Package management

The canonical shared environment is declared at the repository root:

- `pyproject.toml`: core and optional dependency tiers
- `requirements-lock.txt`: pinned core validation closure
- `tools/README.md`: virtualenv installation instructions

Install the core validation environment with:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -c requirements-lock.txt ".[reasoning]"
```

The MORK package remains independently installable from `tools/mork/python/pyproject.toml`.
The root environment is the canonical environment for cross-package Surface,
MORK, SHACL, and conformance gates.

## 10. Open decisions and deferred capabilities

### Decision required

1. Foundation ownership boundary for generic derived-artefact primitives,
   read-set evidence, law discharges, profile identity, and hashes.
2. Whether to adopt the Executable Projection Contract domain-binding layer.
3. Confirmation of live MORK namespace and toolchain join assumptions.

### Deferred capability

1. Range partition semantics and X7.
2. Surface stacking beyond depth 1.
3. ExternalIndex admission and freshness semantics.
4. Entailment regimes beyond NoEntailment.
5. Profile identity hash materialisation.
6. Eligibility strategies beyond IntervalContainment.
7. Profile-level Eligibility artefacts and runtime results.
8. SWRL and OWL engine validation.
9. Behaviour conformance automation.
10. Full CSO-to-FBO semantic compiler behavior.

### Blocked domain work

The insure-o port remains blocked on the manual CSO/FBO port and is not a
Surface implementation defect.

## 11. Phase 9: migration and rollout

When the open decisions are settled:

1. publish authoring guidance for Surface Projection contracts
2. publish raw-MORK-to-Surface migration guidance
3. define Draft, Review, and Production compilation profiles
4. define deprecation policy for direct raw MORK authoring where Surface can
   express the intent
5. pilot one domain-bound Eligibility projection
6. pilot one CSO-to-FBO Projection scenario
7. test rollback and regeneration procedures
8. enable the retained GitHub Action after package-management and CI policy
   sign-off

Production release gates must include deterministic hashes, provenance
completeness, governance state, parity, and freshness.

## 12. Phase 10: scale and optimisation

After the pilot:

1. benchmark lowering and backend compilation
2. cache validated intermediate graphs
3. stress-test large populations and vocabularies
4. measure invalidation and regeneration cost
5. define a high-throughput generation profile
6. preserve parity and provenance under optimisation

## 13. Immediate execution order

1. Resolve the Foundation derived-artefact boundary.
2. Decide and specify the Executable Projection Contract.
3. Confirm MORK toolchain term and namespace assumptions.
4. Add profile identity materialisation if the Foundation decision permits it.
5. Complete Eligibility profile aggregation and runtime result tracking.
6. Add broader shared corpus cases for Projection and Behaviour.
7. Add SWRL and OWL reasoner validation.
8. Begin Phase 9 pilot migration.

## 14. Historical documents

The following documents are retained as rationale or historical material:

- `surface-projection-design-sketch.md`: original Surface mechanism design and
  laws.
- `x6SignatureScopeDecisionAnalysis.md`: plain-language X6 decision analysis.
- `csoFboSurfaceTripleCheck.md`: CSO/FBO complexity boundary analysis.
- `eligibility-L9-replacement.md`: completed L9 amendment.
- `MorkEnhancements.md`: MORK and Eligibility design source, with implemented
  portions now reflected above.
- `adr-bundle-outline-surface-mork-unified-projection.md`: ADR authoring map.
- `OUTSTANDING-ITEMS 2.md`: superseded by `OUTSTANDING-ITEMS.md`.
