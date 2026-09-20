<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Outstanding items — Surface layer

This is the single authoritative status source for the Surface layer's outstanding items, superseding the two documents it merges: the original `OUTSTANDING-ITEMS.md` and the later `OUTSTANDING-ITEMS 2.md`, which had drifted apart (2 records `tools/surface/parity.py`, `tools/surface/mork.py`, and the `srf-canon/2` canonicalisation cutover as done; the original still described them as not built). This document keeps 2's more current status throughout and is the one to edit going forward. `OUTSTANDING-ITEMS 2.md` is retained only as a pointer to here.

Everything here is deliberately *not* in the shipped artefacts. Nothing below has been injected into a README, an OWL annotation, a shape message, or a generated module.

Produced as part of the Surface-MORK unified projection programme's Phase 0/1 architecture lock; see [surface-mork-unified-projection-delivery-plan.md](surface-mork-unified-projection-delivery-plan.md) and [adr-bundle-outline-surface-mork-unified-projection.md](adr-bundle-outline-surface-mork-unified-projection.md).

## Status summary

| § | Item | Tag |
|---|---|---|
| 1.1 | Signature scope and law X6 | **Closed** — resolved in [ADR-A16 addendum](../../docs/adr/ADR-A16-surface-projection-mechanism.md#addendumdecision-x6-stands-as-designed-sign-off): X6 stands as designed. Composition across stacked surfaces stated in [ADR-A21](../../docs/adr/ADR-A21-signature-scope-composition-for-stacked-surfaces.md). |
| 1.2 | Read paths as indexed step lists, not `sh:path` | Done — accepted design, no open action. |
| 1.3 | Derivation contract lives in Surface, not Foundation | Decision needed — see §3.1. |
| 1.4 | Generated-term markers are parentage, not typed individuals | Done — accepted design, no open action. |
| 1.5 | Contracts in `execution/`, examples in `surface/examples/` | Done — accepted layout, no open action. |
| 2.1 | `srf:RangePartitionPopulation` (bucketing law, X7) | Deferred, planned — Quantification partition semantics first, Surface admission second. |
| 2.2 | Stacking beyond depth 1 | Deferred, planned — composition laws now stated in [ADR-A21](../../docs/adr/ADR-A21-signature-scope-composition-for-stacked-surfaces.md); cycle detection and hash-chain freshness remain unimplemented. |
| 2.3 | `srf:ExternalIndex` | Deferred — no admission criteria drafted yet; left until a deployment needs it. |
| 3.1 | Foundation migration for `srf:DerivedArtefact` and kin | Decision needed — unaffected by [ADR-A22](../../docs/adr/ADR-A22-mork-governance-and-versioning-foundation-alignment.md), which resolves governance/versioning alignment only, not this. |
| 3.2 | ADR-A01 convention conflict (README vs spec header) | **Closed** — resolved in [ADR-A01](../../docs/adr/ADR-A01-layer-dependency-order.md#decision): header lives in the README's `turtle-spec` fence. |
| 3.3 | Profile identity computed, not modelled | Blocked, partially addressed — `Profile.identity_hash()` now exists in `tools/surface/model.py` as a pure computation (used by the ADR-A21 stack-composition check); whether to assert it into the graph as `srf:profileIdentityHash` still depends on §3.1's Foundation migration decision. |
| 3.4 | R2 parity harness | Done, partially — `tools/surface/parity.py` implements the comparison; wiring to the shared conformance corpus is tracked under [ADR-A28](../../docs/adr/ADR-A28-parity-and-conformance-release-gate.md) and still open. |
| 3.4 | MORK `mrk:ProjectionMapping` | **Closed** — implemented in `tools/surface/mork.py` against `mork/spec/Mork.ttl`; see also [ADR-A18](../../docs/adr/ADR-A18-surface-to-mork-lowering-boundary.md). |
| 3.4 | insure-o port | Blocked — correctly blocked pending manual CSO/FBO port; not a Surface action item. |
| 3.4 | SHACL validation of Surface's own shapes | Blocked — no SHACL engine available in the authoring environment; tracked as a mandatory CI gate under [ADR-A28](../../docs/adr/ADR-A28-parity-and-conformance-release-gate.md). |
| 3.5 | Entailment regimes recorded but not acted on | Deferred, partially addressed — `tools/surface/compile.py::check_entailment_regime` now refuses to compile under anything but `NoEntailment`, closing the *silent* gap; reasoner integration for the other regimes is still not started. |
| 3.7 | ADR-A18 Surface-to-MORK lowering engine (`tools/surface/lowering.py`) | **Verified** — Surface suite passes 54/54, including `lower_projection`, `lower_contract`, `lower_all`/`link_dependencies`, determinism, and MORK interop. |
| 3.5 | Parity cannot check `DefinitionOnly` forms | Deferred — same dependency as entailment regimes above. |
| 3.5 | Blank-node labels visible in emitted modules | Done — accepted trade-off for stable diffs, no open action. |
| 3.5 | `to_canonical_graph` performance | Deferred — watch-item, no fix planned until it bites. |
| 3.6 | Canonicalisation contract `srf-canon/1` → `srf-canon/2` | **Closed** — cutover complete; examples and fixtures declare `srf-canon/2` and generator `0.2.0`. Runbook for future cutovers tracked under [ADR-A27](../../docs/adr/ADR-A27-invalidation-and-minimal-scope-regeneration-policy.md). |
| 4 / 15.1 | `elg:boundScheme` did not exist | **Closed** — fixed as `elg:constrainedByContract`, present in `eligibility/spec/eligibility.ttl`, `eligibility/README.md`, `eligibility/shapes/rules.ttl`. |
| 4 / 15.2 | `elg:HierarchicalClosureRule` unscoped | **Closed** — removed from `eligibility/shapes/`; no remaining reference in the Eligibility layer. |
| 4 / 15.3 | `ins:` vs `ino:` properties | **Closed** — dropped, insure-o is going. |
| 4 / 15.4 | `fnd:GovernanceState` individuals undeclared | **Closed** — corrected 2026-09-18: the previous "Done" tag here was wrong. `docs/architecture/ontology-architecture.md` already recorded this as a real, undeclared gap, and a repo-wide grep confirmed every reference to `fnd:Active` etc. was a forward reference, never a declaration. Now declared in `foundation/vocab/foundation-vocab.ttl` as part of the Phase 4 MORK governance work, which needed them to be real. |
| 3.8 | MORK governance and versioning (ADR-A22) | Implemented, **engine validation pending** — Foundation import, `mork:GenerativeMapping` adopting `fnd:Governable`/`fnd:Version`, `mork:CompilationMode`, and three SHACL shapes are present. Turtle parsing is clean, but SHACL execution remains outstanding. |
| 3.9 | MORK SPARQL/SHACL/SWRL compiler family for Eligibility (ADR-A23, ADR-A24) | **IntervalContainment slice verified** — the focused MORK compiler suite passes 15/15, and generated SPARQL returns `Permitted` for the worked example. SHACL/SWRL engine execution, profile-level artefacts, runtime result tracking, and broader Eligibility strategies remain open. |
| 4 / 15.5 | `bhv:targetsAllowance` README⇄spec drift | **Closed** — hand-remediated; caught by `tools/literate_extract.py --check` going forward. |
| 5 | MORK toolchain join assumptions | Decision needed — namespace and term-name assumptions in `tools/surface/mork.py` need confirming against the live `mork/spec/Mork.ttl`, not re-guessed. |

Items marked **Closed** are excluded from active backlog and are not revisited except for documentation hygiene, per the delivery plan's explicit-closure policy.

---

## 1. Decisions taken during implementation, requiring sign-off

### 1.1 Signature scope, and law X6 — closed

See status summary. The design note stated conservativity (X1) as unconditional: a surface never extends the source-signature consequence set. That holds for indexing, which always mints its own terms. It does **not** hold for promotion. A promotion restates a value onto `srf:promotesTo`, and that property is either one the contract mints in its own target namespace, or one a consuming layer already declares. In the second case the emitted triples are over the authored signature and are indistinguishable from authored facts. No authority annotation on the surface record changes that, because the assertions carry the authored property, not a generated one.

This is exactly the MERIDIAN CSO→FBO case: `fbo:hasLineOfBusiness` is authored, so `DimensionSourcing` is producing authored-signature A-box, not an index.

Modelled as:

- `srf:signatureScope` on every `srf:GeneratedSurface`, valued `srf:LocalSignature` or `srf:SourceSignature`;
- X1 restated to apply to local-signature surfaces;
- law **X6**: a promotion onto a property outside the contract's target namespace declares exact or crosswalk-exact fidelity, and is materialised rather than definitional.

**Resolved:** X6 stands as designed, source-signature promotion stays in Surface rather than moving to MORK's `DataMapping`. See [ADR-A16 addendum](../../docs/adr/ADR-A16-surface-projection-mechanism.md#addendumdecision-x6-stands-as-designed-sign-off) and [ADR-A21](../../docs/adr/ADR-A21-signature-scope-composition-for-stacked-surfaces.md) for the composition rule across stacked surfaces.

### 1.2 Read paths are indexed step lists, not SHACL path nodes — done

The design note proposed `sh:path`. SHACL path syntax nests blank nodes, whose labels do not survive canonicalisation without a blank-node normalisation pass — which would have made the read path the only part of a contract needing one. `srf:PathStep` individuals with `srf:stepIndex` and `srf:stepDirection` give the same sequence-and-inverse expressivity with a form that hashes directly, and follow the positional pattern `qnt:OrderingComponent` already uses. Alternation and zero-or-more remain out of scope, as designed.

The cost: a contract cannot be handed straight to a SHACL engine as a path expression. The compiler would need to synthesise one. Nothing currently needs that.

### 1.3 The derivation contract is in Surface, not Foundation — decision needed

`srf:DerivedArtefact`, `srf:GeneratedSurface`, `srf:ReadSetEntry`, `srf:LawDischarge`, `srf:derivationAuthority`, and the hash properties are all declared in Surface, per the instruction not to pollute Foundation.

ADR-A12 anticipates a Foundation-level `fnd:DerivedArtefact`, and Quantification §12 and Behaviour both name it as a blocking gap. Validation reports, entailment sets, and materialised bins will want the same contract. When Foundation gains it, Surface's classes should become subclasses rather than being restructured — they are shaped to allow that, but the migration is unplanned and the duplication is real in the meantime. See §3.1.

### 1.4 The generated-term markers are parents, not types — done

MERIDIAN asserts `generatedFromConcept` on generated `owl:Class` terms with `rdfs:domain owl:Class` — punning that OWL-API toolchains object to. Marked by parentage instead: every generated class is `rdfs:subClassOf srf:GeneratedClass`, every generated relation `rdfs:subPropertyOf srf:generatedRelation`. Enumerating a surface's inventory is a subclass query, no punning involved. Provenance lives on `srf:GeneratedSymbol` records in the manifest.

### 1.5 Contracts in `execution/`, examples in `surface/examples/` — done

Generated packages for the three worked examples are committed under `surface/execution/<contractKey>/`. The example contract declarations are in `surface/examples/`, not the repository-root `examples/` — root `examples/employment.ttl` and `examples/saas-subscription.ttl` are for cross-layer composition scenarios rather than single-layer worked examples.

---

## 2. Deferred with a planned approach

### 2.1 `srf:RangePartitionPopulation` — the bucketing law — deferred, planned

Declared, rejected by both the compiler and `srf:RangePartitionDeferredShape`. Reopening it needs, in order:

**Step 1 — state the partition precondition.** A range set is *admissible as a population* when its ranges are pairwise disjoint and their union covers the space the carrier's values are drawn from. Neither is implied by `qnt:RangeSet` today. This is Quantification work first: a `qnt:PartitionRangeSet` subclass, or a `qnt:isPartition` flag with a shape checking disjointness and coverage.

**Step 2 — settle boundary behaviour under each `qnt:Closure`.** Adjacent ranges meeting at a boundary `b`:

| Left range ends | Right range starts | Point `b` | Verdict |
|---|---|---|---|
| closed at `b` | open at `b` | in left only | admissible |
| open at `b` | closed at `b` | in right only | admissible |
| closed at `b` | closed at `b` | in both | **overlap** — reject |
| open at `b` | open at `b` | in neither | **gap** — reject |

Law **X7, range partition faithfulness**: a carrier instance whose value is `v` belongs to exactly one bucket symbol, the one whose range contains `v` under that range's declared closure.

**Step 3 — decide what the symbol denotes.** A nominal bucket class needs a datatype restriction (`owl:onDatatype` with `xsd:minInclusive` / `xsd:maxExclusive` facets), OWL 2 DL, not OWL 2 EL. A range-partition surface's profile must declare `srf:OWL2DLEntailment` or materialise.

**Step 4 — naming.** `LocalNameFromValue` has nothing to read for a range. Either ranges gain a required label, or the form requires `DigestLocalName`, or a new `srf:RangeBoundNaming` policy mints from the bounds (`bucket_0_100`, `bucket_100_inf`).

**Step 5 — invalidation.** A range set is a declaration, entering the read set as a `DeclarationSource` entry under the existing freshness rule. No new machinery.

Most of the work is Steps 1–2, and most of that is in Quantification. Surface's own part — a population kind, a naming policy, a bucket-assignment pass in the compiler — is small once the partition guarantee exists.

### 2.2 Stacking beyond depth 1 — deferred, planned

Modelled fully: `srf:permittedStackDepth` on the profile, `srf:stackDepth` on the generated surface, `srf:SurfaceSource` read-set entries, and `srf:S10` checking one against the other. `srf:StackDepthReleaseCeilingShape` caps the permitted depth at 1; deleting that one shape is the entire mechanical change needed to allow deeper stacks.

What deleting it leaves unstated, and what must exist first:

- **The read set becomes a DAG.** At depth *n* a surface's semantic content hash must incorporate the *artefact* hashes of the surfaces it read, so a change three levels down propagates, and nothing yet checks that an input surface was itself fresh when read.
- **X1 needs a composition law.** **Now stated** in [ADR-A21](../../docs/adr/ADR-A21-signature-scope-composition-for-stacked-surfaces.md): `signatureScope` of a stacked surface is `SourceSignature` if any input surface's is.
- **R1 needs a composition law.** **Now stated** in ADR-A21: every surface in a stack shares one profile identity, checked statically.
- **Cycle detection.** Not yet implemented; needed before the depth cap can be lifted.
- **Invalidation cost.** Not yet measured on the FBO chain; the impact-scoping table in the README §11 has no row for stacked regeneration. Tracked under [ADR-A27](../../docs/adr/ADR-A27-invalidation-and-minimal-scope-regeneration-policy.md).

The FBO chain (CSO → promoted dimension → nominal index) is depth 1 and works today.

### 2.3 `srf:ExternalIndex` — deferred

Declared and rejected, following the `bhv:Proportional` precedent — visibly unavailable rather than silently absent. Admitting it needs: a way to name the store and its index without the substrate depending on any particular store; a statement of what "the surface is fresh" means when the index cannot be hashed; and a decision about whether a store-native index can discharge parity (R2) at all. Left until a deployment actually needs it.

---

## 3. Known gaps

### 3.1 Foundation migration — decision needed

The question to settle: does the derived-artefact contract eventually move to Foundation per ADR-A12, with Surface's classes becoming subclasses, or does each generating layer declare its own? If the former, `srf:DerivedArtefact`, `srf:derivationAuthority`, `srf:producedAt`, `srf:artefactHash`, `srf:semanticContentHash`, and the two authority individuals are the migration set. `srf:ReadSetEntry` and the read-source kinds are arguably generic too. `srf:LawDischarge` duplicates `qnt:LawDischarge` in shape but not in namespace; a Foundation-level law register would absorb both. [ADR-A22](../../docs/adr/ADR-A22-mork-governance-and-versioning-foundation-alignment.md) resolves the governance/versioning half of Foundation alignment for MORK specifically; this broader question is unaffected and still open.

### 3.2 ADR-A01 convention conflict — closed

**Resolved** in [ADR-A01](../../docs/adr/ADR-A01-layer-dependency-order.md#decision): the ontology header is authored in the README's `turtle-spec` fence, matching Eligibility, Behaviour, and Surface practice. Foundation, Vocabulary, and Party are the outliers to correct, not the other three layers.

### 3.3 Profile identity is computed, not modelled — blocked

`Profile.identity()` in the compiler concatenates the profile IRI, generator version, canonicalisation version, entailment regime, naming normalisation, symbol mode, and permitted stack depth, and decides whether two artefacts are interchangeable — but it is not represented in the graph. A `srf:profileIdentityHash` on the generated surface would close this, but it interacts with whatever Foundation ends up doing about generation profiles (§3.1), so it waits on that decision.

### 3.4 Not built, or partially built

- **R2 parity harness.** `tools/surface/parity.py` implements the comparison for materialised forms and the `--parity` flag records the discharge. What remains is wiring it to the shared conformance corpus the other layers use, rather than the questions it currently generates itself from the contract. Tracked under [ADR-A28](../../docs/adr/ADR-A28-parity-and-conformance-release-gate.md).
- **MORK `mrk:ProjectionMapping` — closed.** Implemented in `tools/surface/mork.py`, in both directions, against `mork/spec/Mork.ttl` as it stands in this repository. See [ADR-A18](../../docs/adr/ADR-A18-surface-to-mork-lowering-boundary.md).
- **insure-o port.** Correctly blocked: the current insure-o is being dropped in favour of a hand-port of CSO and FBO. The three non-domain examples exercise every mechanism the port needs except range partitions.
- **SHACL validation of Surface's own shapes.** No SHACL engine in the authoring environment, so `shapes/structural.ttl` and `shapes/constraints.ttl` are syntactically checked but not executed against fixtures. The six defect fixtures are exercised through the compiler, which enforces the same laws independently, but compiler agreement is not shape validation. Tracked as a mandatory CI gate under [ADR-A28](../../docs/adr/ADR-A28-parity-and-conformance-release-gate.md).

### 3.5 Compiler limitations worth knowing

- **Entailment regimes are recorded but not acted on.** The compiler always reads asserted triples. Correct for `srf:NoEntailment` profiles; a gap for the others. Closing this means choosing a reasoner (owlrl for RDFS and OWL 2 RL, an external EL reasoner for the nominal form) and deciding whether the compiler materialises entailments before reading or requires the caller to.
- **Parity cannot check `DefinitionOnly` forms.** `srf:R2` compares assertions; a `DefinitionOnly` surface asserts nothing, so those forms report as skipped with the regime named, rather than silently passed. Same dependency as the item above.
- **Blank-node labels in emitted modules are visible.** Minted from the term they belong to (`_:RoleAssignment_job-family_Sales_def_l0`), which keeps regenerated modules diffing cleanly. Hashing does not depend on this any more — the canonical form relabels blank nodes by graph position — so this is now a style choice, kept deliberately for stable diffs, per law `srf:R3`.
- **`to_canonical_graph` is not free.** Superlinear on blank-node-bearing graphs. Read-set inputs are almost always blank-node free, where the cost is a sort. A very large emitted `core.ttl` with one blank-node definition per population member is the case to watch; if it bites, hash the modules per-subject and fold, rather than abandoning the canonical form.

### 3.6 Canonicalisation contract `srf-canon/1` → `srf-canon/2` — closed

The rdflib rewrite hashes `rdflib.compare`'s canonical graph rather than a sorted rendering dependent on deterministic blank-node labels — blank-node-label independent, so a graph read from anywhere hashes stably. This was a change of canonicalisation contract per ADR-A12, and the rehash has been taken: every previously recorded `srf:readHash`, `srf:semanticContentHash`, and `srf:artefactHash` is stale by design, and the three committed example packages were regenerated rather than left looking current (`surface/execution/README.md` gives the regeneration command). Examples and fixtures now declare `srf-canon/2` and generator `0.2.0`. A runbook for any future cutover of this kind is tracked under [ADR-A27](../../docs/adr/ADR-A27-invalidation-and-minimal-scope-regeneration-policy.md).

### 3.7 Surface-to-MORK lowering engine — verified

`tools/surface/lowering.py` implements ADR-A18/A19's lowering stage: `lower_projection` (a `ProjectionContract`, which has no direct-emit form), `lower_contract` (a Promotion/Index declaration, for the configured case where a deployment also wants it mirrored into MORK), and `lower_all`/`link_dependencies` (one mapping graph per batch, with `mork:dependsOnMapping` edges computed from a role binding's declared `bindsCarrier`/`bindsProperty` cross-reference to another contract in the same batch). Every emitted mapping is a bare `mork:DataMapping`, deliberately not yet classified into any `GenerativeMapping` subtype — that classification is OWL-inferred from a generated-artefact property (`generatesShapeDefinition` and its siblings) that only a Phase 5 backend compiler attaches.

The implementation has now been executed. `python3 -m unittest tools.surface.test_surface -v` passes 54/54, including `ContractLoweringTests`, `LoweringDependencyTests`, Projection lowering, determinism, and MORK interop.

**No committed goldens.** `surface/execution/`'s convention is regenerated output, not hand-authored fixtures (see that directory's own README). No lowering output has been committed here for the same reason: a hand-computed "golden" `.ttl` file cannot be verified byte-accurate without running the compiler, and a wrong golden is worse than none. Regenerate with `python -m tools.surface lower --contracts surface/examples/saas-subscription-arr-projection.ttl` once Python is available, and commit the result under `surface/execution/` at that point.

---

## 4. Findings 15.1–15.5

| # | Finding | Status |
|---|---|---|
| 15.1 | `elg:boundScheme` does not exist | **Closed** — fixed as option (c), `elg:constrainedByContract`, present in `eligibility/spec/eligibility.ttl`, `eligibility/README.md`, and read by `eligibility/shapes/rules.ttl`. |
| 15.2 | `elg:HierarchicalClosureRule` unscoped | **Closed** — removed from `eligibility/shapes/` per the L9 replacement at [eligibility-L9-replacement.md](eligibility-L9-replacement.md); no remaining reference in the Eligibility layer. |
| 15.3 | `ins:` vs `ino:` properties | **Closed** — dropped; insure-o is going, `ins:` carries no domain properties, CSO scopes peril via `hasPerilScope` on `TermApplication`. |
| 15.4 | `fnd:GovernanceState` individuals undeclared | **Closed** — see the corrected status summary entry above (§4/15.4); the individuals are now actually declared in `foundation/vocab/foundation-vocab.ttl`. |
| 15.5 | `bhv:targetsAllowance` README⇄spec drift | **Closed** — hand-remediated. `tools/lattice/literate_extract.py --check` would have caught it, and catches the next one. |

---

## 5. The MORK toolchain join — decision needed

`tools/surface/mork.py` is written against `mork/spec/Mork.ttl` and `tools/mork2rml.py` as they appear in this repository's document set, predating full confirmation against a live toolchain checkout. What was assumed, and what to check:

| Assumption | Check |
|---|---|
| MORK terms live at `http://www.nebularis.org/ontologies/Mork#` | Confirmed: `mork/spec/Mork.ttl`'s base and default prefix use this namespace. `mork/targets/insure-o-target.ttl` binds `mk:` to `.../lattice/mork#` — both are bound in `namespaces.py`, and `MORK` is the one used. If the toolchain has settled on the lattice form instead, change one constant. |
| `mrk:GenerativeMapping`, `DataMapping`, `TargetingSpec`, `ParameterBinding` (`paramName`/`paramType`/`paramValue`), `OwlClass`, `mappingScheme`, `mappingFor`, `reviewStatus`, `provenanceCreated` exist with those names | Every one is used by `mork.py`. If any have been renamed, the failures will be silent — they would emit triples nobody reads. Worth a grep before the first production run. |
| `ProjectionMapping`, `generatesClassDefinition`, `ProjectionProvenance`, `hasProjectionProvenance` exist | Confirmed present in `mork/spec/Mork.ttl` (`GenerativeMapping`'s subclasses include `ProjectionMapping`). |
| The compiler is a sibling of `mork2rml.py` under `tools/`, not a member of the MORK package | If the toolchain has a shared package (`mork_communities/` suggests one), `serialise.py` and parts of `namespaces.py` may duplicate utilities that already exist there. |
| `mork_communities/shadow.py` is unrelated | It builds `OwlAxiom` shadows to keep reasoning over mapping graphs sound, a MORK-internal concern. Surface shadows nothing — it restates domain-layer relationships for runtime lookup. Worth confirming there is no naming collision in emitted IRIs if both ever run over one graph. |

**Open question, not yet decided:** whether to reuse MORK's `precedes` derivation ordering for Surface's generated-module order (class definitions before membership assertions before closure relations), rather than `owl:imports`. Surface currently uses `owl:imports` because a surface package is consumed as a unit. If the toolchain expects derivation order expressed as `precedes`, that is a small addition to the manifest, not a compiler change.
