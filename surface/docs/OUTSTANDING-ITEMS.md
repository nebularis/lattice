<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Outstanding items — Surface layer

Everything here is deliberately *not* in the shipped artefacts. Nothing below has been injected into a README, an OWL annotation, a shape message, or a generated module.

---

## 1. Decisions I took during implementation that you have not seen

### 1.1 Signature scope, and law X6 — needs your sign-off

This is the one place where implementation forced a change to the design you approved, and it is material.

The design note stated conservativity (X1) as unconditional: a surface never extends the source-signature consequence set. That holds for indexing, which always mints its own terms. It does **not** hold for promotion. A promotion restates a value onto `srf:promotesTo`, and that property is either one the contract mints in its own target namespace, or one a consuming layer already declares. In the second case the emitted triples are over the authored signature and are indistinguishable from authored facts. No authority annotation on the surface record changes that, because the assertions carry the authored property, not a generated one.

This is exactly the MERIDIAN CSO→FBO case: `fbo:hasLineOfBusiness` is authored, so `DimensionSourcing` is producing authored-signature A-box, not an index.

Rather than weaken X1 or pretend the case away, I modelled it:

- `srf:signatureScope` on every `srf:GeneratedSurface`, valued `srf:LocalSignature` or `srf:SourceSignature`;
- X1 restated to apply to local-signature surfaces;
- new semantic law **X6**: a promotion onto a property outside the contract's target namespace declares exact or crosswalk-exact fidelity, and is materialised rather than definitional.

The two consequences the compiler enforces: a lossy promotion (derived, or crosswalk-inexact) may not target an authored property at all — it lands on a generated one where its derived nature is visible in the IRI; and a definition-only promotion may not emit a property-chain axiom onto an authored property, because an axiom on an authored term is not conservative under anyone's reading.

**What you need to decide:** whether X6 is the right rule, or whether source-signature promotion should instead be pushed out of Surface entirely and treated as a mapping concern (MORK's `DataMapping`), leaving Surface strictly conservative. The second is cleaner in theory and costs you the ability to express the FBO dimension-sourcing table as surface contracts. I took the first because the FBO port is the driver, but it is reversible now and expensive to reverse after the port.

### 1.2 Read paths are indexed step lists, not SHACL path nodes

The design note proposed `sh:path`. SHACL path syntax nests blank nodes, whose labels do not survive canonicalisation without a blank-node normalisation pass — which would have made the read path the only part of a contract needing one. `srf:PathStep` individuals with `srf:stepIndex` and `srf:stepDirection` give the same sequence-and-inverse expressivity with a form that hashes directly, and follow the positional pattern `qnt:OrderingComponent` already uses. Alternation and zero-or-more remain out of scope, as designed.

The cost: a contract cannot be handed straight to a SHACL engine as a path expression. The compiler would need to synthesise one. Nothing currently needs that.

### 1.3 The derivation contract is in Surface, not Foundation

You said: do not pollute Foundation. So `srf:DerivedArtefact`, `srf:GeneratedSurface`, `srf:ReadSetEntry`, `srf:LawDischarge`, `srf:derivationAuthority`, and the hash properties are all declared in Surface.

ADR-A12 anticipates a Foundation-level `fnd:DerivedArtefact`, and Quantification §12 and Behaviour both name it as a blocking gap. Validation reports, entailment sets, and materialised bins will want the same contract. When Foundation gains it, Surface's classes should become subclasses rather than being restructured — they are shaped to allow that, but the migration is unplanned and the duplication is real in the meantime. See §3.1.

### 1.4 The generated-term markers are parents, not types

MERIDIAN asserts `generatedFromConcept` on generated `owl:Class` terms with `rdfs:domain owl:Class` — punning that OWL-API toolchains object to. I marked generated terms by parentage instead: every generated class is `rdfs:subClassOf srf:GeneratedClass`, every generated relation `rdfs:subPropertyOf srf:generatedRelation`. Enumerating a surface's inventory is a subclass query, no punning involved, and wrapper mode therefore adds no class-as-individual statements of its own. Provenance lives on `srf:GeneratedSymbol` records in the manifest, as you specified.

### 1.5 Contracts in `execution/`, examples in `surface/examples/`

Generated packages for the three worked examples are committed under `surface/execution/<contractKey>/`, per your item 11. The example contract declarations are in `surface/examples/`, not the repository-root `examples/` — root `examples/employment.ttl` and `examples/saas-subscription.ttl` are still empty and are, on my reading, for cross-layer composition scenarios rather than single-layer worked examples. Move them if that reading is wrong; the compiler takes paths, so nothing breaks.

---

## 2. Deferred with a planned approach

### 2.1 `srf:RangePartitionPopulation` — the bucketing law

Declared, rejected by both the compiler and `srf:RangePartitionDeferredShape`. Here is what reopening it needs, in the order it needs it.

**The problem.** Every other population is a set of IRIs the generator can enumerate and mint from. A range set is a set of intervals over an ordered value space. Minting one symbol per interval is straightforward; the difficulty is that the symbols must partition, and `qnt:RangeSet` does not currently guarantee that they do.

**Step 1 — state the partition precondition.** A range set is *admissible as a population* when its ranges are pairwise disjoint and their union covers the space the carrier's values are drawn from. Neither is implied by `qnt:RangeSet` today: ranges may overlap, and there is no notion of a covered domain. So the first piece of work is in Quantification, not Surface: a `qnt:PartitionRangeSet` subclass, or a `qnt:isPartition` flag with a shape that checks disjointness and coverage. Without it the surface would silently mint overlapping buckets and a carrier instance would land in two of them, which breaks index faithfulness (X2) with no diagnostic.

**Step 2 — settle boundary behaviour under each `qnt:Closure`.** This is the substantive part. Adjacent ranges meeting at a boundary `b` fall into three cases:

| Left range ends | Right range starts | Point `b` | Verdict |
|---|---|---|---|
| closed at `b` | open at `b` | in left only | admissible |
| open at `b` | closed at `b` | in right only | admissible |
| closed at `b` | closed at `b` | in both | **overlap** — reject |
| open at `b` | open at `b` | in neither | **gap** — reject |

So the partition check is a pairwise closure-compatibility check at each shared boundary, not just an interval-arithmetic check. Unbounded ends and the empty range need their own rows. The law to state — call it **X7, range partition faithfulness** — is: a carrier instance whose value is `v` belongs to exactly one bucket symbol, and it is the bucket whose range contains `v` under that range's declared closure. Exactly one, for every `v` in the covered space: that is the whole content of the law, and it is what the two rejected rows above protect.

**Step 3 — decide what the symbol denotes.** A nominal bucket class is `Carrier ⊓ ∃R.{v : v ∈ range}`, which is not expressible with `owl:hasValue` — it needs a datatype restriction (`owl:onDatatype` with `xsd:minInclusive` / `xsd:maxExclusive` facets). That is OWL 2 DL but not OWL 2 EL, so a range-partition surface cannot claim the EL-safety that the nominal form currently claims, and its profile must declare `srf:OWL2DLEntailment` or materialise. This is a real constraint and should be stated when the form is admitted, not discovered afterwards.

**Step 4 — naming.** `LocalNameFromValue` has nothing to read: a range has no local name. Either ranges gain a required label for this purpose, or the form requires `DigestLocalName` over the range's canonical form, or a new `srf:RangeBoundNaming` policy mints from the bounds (`bucket_0_100`, `bucket_100_inf`). The third reads best and is fragile under reparameterisation — changing a boundary renames the symbol and invalidates everything downstream, which is arguably correct but should be a stated consequence.

**Step 5 — invalidation.** A range set is a declaration, so it enters the read set as a `DeclarationSource` entry and the existing freshness rule covers it unchanged. No new machinery.

Estimated shape of the work: most of it is Step 1 and Step 2, and most of that is in Quantification. Surface's own part — a population kind, a naming policy, a bucket-assignment pass in the compiler — is small once the partition guarantee exists.

### 2.2 Stacking beyond depth 1

Modelled fully: `srf:permittedStackDepth` on the profile, `srf:stackDepth` on the generated surface, `srf:SurfaceSource` read-set entries, and `srf:S10` checking one against the other. The compiler computes depth from input surfaces and refuses to exceed the profile's permitted depth. `srf:StackDepthReleaseCeilingShape` caps the permitted depth at 1 for this release; deleting that one shape is the entire mechanical change needed to allow deeper stacks.

What deleting it would leave unstated, and what must be written first:

- **The read set becomes a DAG.** At depth 1 a surface's read set is a list of source hashes. At depth *n* an entry may name a surface whose own read set names further surfaces, so freshness is a transitive question and the honest form is a hash chain: a surface's semantic content hash must incorporate the *artefact* hashes of the surfaces it read, so that a change three levels down propagates. The current implementation already does this correctly at depth 1 (a `SurfaceSource` entry carries the input's artefact hash) but nothing checks that the input surface was itself fresh when read. At depth > 1 that check is mandatory, otherwise a fresh-looking surface can sit on a stale one.
- **X1 needs a composition law.** Conservativity composes: a local-signature surface over a local-signature surface is local-signature. But a surface over a *source-signature* promotion is not conservative over the original source, because its input already was not. So the composition rule is: `signatureScope` of a stacked surface is `SourceSignature` if any input surface is. That is one line in the compiler and one clause in X1, but it must be written down before the depth cap is lifted.
- **R1 needs a composition law too.** Determinism composes only if every surface in the chain is regenerated under the same profile identity. Mixed-profile stacks are not obviously wrong but are not obviously reproducible either. Simplest defensible rule: every surface in a stack shares one profile, checked statically.
- **Cycle detection.** Two surfaces reading each other is currently impossible only because depth is capped. At arbitrary depth it needs the same treatment as the closure basis: a traversal, refused on a cycle.
- **Invalidation cost.** The reason the design note hesitated. A change at the bottom of a depth-*n* stack regenerates *n* artefacts, and the impact-scoping table in §11 of the README has no row for it. Worth measuring on the FBO chain before lifting the cap.

The FBO chain (CSO → promoted dimension → nominal index) is depth 1 and works today.

### 2.3 `srf:ExternalIndex`

Declared and rejected, following the `bhv:Proportional` precedent — visibly unavailable rather than silently absent. Admitting it needs: a way to name the store and its index without the substrate depending on any particular store; a statement of what "the surface is fresh" means when the index is not in the graph and cannot be hashed; and a decision about whether a store-native index can discharge parity (R2) at all, given that the comparison would run outside RDF. I would leave this until a deployment actually needs it — the answers depend heavily on which store.

---

## 3. Known gaps in what I have built

### 3.1 Foundation migration

See §1.3. The question to settle: does the derived-artefact contract eventually move to Foundation per ADR-A12, with Surface's classes becoming subclasses, or does each generating layer declare its own? If the former, `srf:DerivedArtefact`, `srf:derivationAuthority`, `srf:producedAt`, `srf:artefactHash`, `srf:semanticContentHash`, and the two authority individuals are the migration set. `srf:ReadSetEntry` and the read-source kinds are arguably generic too. `srf:LawDischarge` duplicates `qnt:LawDischarge` in shape but not in namespace; a Foundation-level law register would absorb both.

### 3.2 ADR-A01 convention conflict — ontology headers in READMEs

ADR-A01's convention note says no layer README duplicates its ontology header inside a `turtle-spec` fence; the header is authored once, directly in `spec/<layer>.ttl`. But Eligibility's and Behaviour's READMEs both *do* include their headers in `turtle-spec`, so the convention is already not held.

I included the header in `surface/README.md` §6.1, because extraction has to produce a complete file — a header-less `spec/surface.ttl` would need a hand-maintained fragment prepended, which reintroduces exactly the drift the literate-spec discipline exists to prevent. Someone should decide which way the convention goes and make the three layers agree. My recommendation is to amend ADR-A01 to match practice.

### 3.3 Profile identity is computed, not modelled

`Profile.identity()` in the compiler concatenates the profile IRI, generator version, canonicalisation version, entailment regime, naming normalisation, symbol mode, and permitted stack depth. It decides whether two artefacts are interchangeable, and it is not represented in the graph — nothing records *which* identity a surface was produced under beyond naming the profile, which may itself have changed. A `srf:profileIdentityHash` on the generated surface would close this. I did not add it because it interacts with whatever Foundation ends up doing about generation profiles (§3.1).

### 3.4 Not built

- **R2 parity harness.** The conformance corpus comparison — same question against the surface and against the source — is the only thing that makes a surface trustworthy, and it is the one law with no implementation here. It needs a SPARQL engine, which this environment does not have. It should extend the existing conformance corpus rather than growing its own.
- **MORK `mrk:ProjectionMapping`.** Sketched in the design note, not cut. The compiler's structure (contract → plan → emit) maps onto the `mork2rml` catamorphism, but I did not want to shape the Surface layer around MORK before you had seen it standing alone.
- **insure-o port.** Correctly blocked: you are dropping the current insure-o and porting CSO and FBO by hand. The three non-domain examples exercise every mechanism the port will need except range partitions.
- **SHACL validation of my own shapes.** No SHACL engine in this environment, so `shapes/structural.ttl` and `shapes/constraints.ttl` are syntactically checked (they parse) but have not been executed against the fixtures. The six defect fixtures are exercised through the compiler, which enforces the same laws independently — but compiler agreement is not shape validation, and the shapes should be run before anyone relies on them.

### 3.5 Compiler limitations worth knowing

- The Turtle reader accepts a restricted subset and refuses blank-node and collection syntax with an explicit message. It is sufficient for contract declarations, concept schemes, and carrier instance graphs, all of which are blank-node free. It is **not** sufficient for reading arbitrary source ontologies — an upper ontology with OWL restrictions will not parse. Swapping in rdflib behind the same `Graph` interface is the obvious fix and is about a day's work; I avoided the dependency because the container has neither rdflib nor network access, and a compiler I could actually run and test seemed worth more than one I could only write.
- `ClassExtentPopulation` with `TransitiveSubClasses` computes the closure over asserted `rdfs:subClassOf` only. Under a reasoner the extent would be larger. The profile's `srf:entailmentRegime` is recorded but the compiler does not act on it — it always reads asserted triples. For `srf:NoEntailment` profiles this is correct; for others it is a gap, and the honest statement is that the compiler currently implements the no-entailment profile only.
- Blank-node labels in emitted modules are deterministic and derived from the term they belong to (`_:RoleAssignment_job-family_Sales_def_l0`). This makes regeneration byte-identical and diffs stable, at the cost of labels that are visible in the output. If that offends, an inline `[ ]` serialiser is straightforward, but then the canonicalisation contract needs a blank-node normalisation pass.

---

## 4. Findings 15.1–15.5

Recording status as you left them, so nothing is lost:

| # | Finding | Status |
|---|---|---|
| 15.1 | `elg:boundScheme` does not exist | Fixed as option (c) — `elg:constrainedByContract`. The L9 replacement's new shape reads it and cannot be installed until it lands. |
| 15.2 | `elg:HierarchicalClosureRule` unscoped | Full L9 replacement text supplied at `docs/amendments/eligibility-L9-replacement.md`, including the rule's removal and its static replacement. |
| 15.3 | `ins:` vs `ino:` properties | Dropped — insure-o is going, `ins:` carries no domain properties, CSO scopes peril via `hasPerilScope` on `TermApplication`. |
| 15.4 | `fnd:GovernanceState` individuals undeclared | Being added to Foundation as individuals. The examples and fixtures here assume `fnd:Active` exists. |
| 15.5 | `bhv:targetsAllowance` README⇄spec drift | Hand remediation. Note that `tools/lattice/literate_extract.py --check` would have caught it, and would catch the next one. |
