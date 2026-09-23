<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Persistence Ontology — the Data Access Layer (`dal:`)

Literate specification for the persistence profile substrate.

## 1. Purpose and scope

LATTICE ships ontologies, libraries, and control-plane infrastructure the way a framework does, not the way a single application does. An adopter builds their own applied ontology on the substrate layers and decides, per class or per deployment, whether a population of individuals is an aggregate, what its containment boundary is, whether it needs compare-and-set, what ordering grain it needs, and what receipt model it needs. The patterns guide answers *what the options are and their consequences*. This ontology answers *how one adopter selects among them*, and the `tools/persistence` compiler turns that selection into generated SPARQL.

This ontology targets classes, graphs, and shapes **by IRI reference only**. It imports nothing from Foundation, Vocabulary, Quantification, Party, Eligibility, Instrument, or Behaviour, and none of them import it back. It has no place in the seven-layer dependency table in [ontology-architecture.md](../../docs/architecture/ontology-architecture.md#the-seven-lattice-layers): it sits alongside Surface and MORK as a cross-cutting substrate.

## 2. Namespace

```turtle
@prefix dal: <https://www.nebularis.org/neuro-semantic/lattice/persistence#> .
```

The directory is named `persistence` because the compiler, and any future housekeeping or runtime component, all belong to that subsystem. The ontology inside it is named for what it is: a **Data Access Layer** configuration vocabulary, hence `dal:`.

## 3. Independently scopable dimensions

| Dimension | Class | Values |
|---|---|---|
| Aggregate boundary | `dal:AggregateBoundaryProfile` | `dal:NamedGraphBoundary`, `dal:CompositePropertyBoundary`, `dal:NoBoundary` |
| First-write policy | `dal:AggregateBoundaryProfile` | `dal:PreCreatedRow`, `dal:AbsentRow` |
| Concurrency | `dal:ConcurrencyProfile` | `dal:ProvidedConcurrency`, `dal:Optimistic`, `dal:AppendOnly`, `dal:LockingConcurrency` (marker only) |
| Deadlock policy | `dal:ConcurrencyProfile` | `dal:EngineDetectAndRetry`, `dal:SortedAcquisition`, `dal:PartitionedWriter` |
| HTTP conditional form | `dal:ConcurrencyProfile` | `dal:StrongEtag`/`dal:WeakEtag`, `dal:SingleRepresentation`/`dal:TaggedRepresentation` |
| Ordering grain | `dal:OrderingProfile` | `dal:CommitGrain`, `dal:EventGrain` |
| Global-read strategy | `dal:OrderingProfile` | `dal:WatermarkedRead`, `dal:LagWindowRead` (with `dal:lagWindowMillis`), `dal:DenseFeedRead`, `dal:NoGlobalRead` |
| Contiguity check | `dal:OrderingProfile` | `dal:BlockingContiguityCheck`, `dal:AdvisoryContiguityCheck` |
| Receipt model | `dal:ReceiptProfile` | `dal:ReceiptOnly`, `dal:PatchLog`, `dal:SnapshotPerRevision` |
| Retention mode | `dal:ReceiptProfile` | `dal:PrefixOnlyRetention`, `dal:BucketAnyRetention`, plus `dal:asOfFloorSource` |
| Meta topology | `dal:MetaTopologyProfile` | `dal:SharedSharded`, `dal:PerAggregate`, plus `dal:txnShards`/`dal:logShards`/`dal:keyShards`/`dal:registryGraph` |
| Uniqueness | `dal:UniquenessConstraint` | many-valued: a target may carry zero, one, or several distinct keyed constraints; each may carry a `dal:mergeRelation` and a `dal:claimScheme` |
| Identity minting | `dal:IdentityProfile` | one `dal:IdentityStrategy` per `dal:ResourceRole`, each role resolved as its own dimension `identity:<Role>`, the winning profile node as a unit — see §9 |
| Epoch authority | `dal:EpochProfile` | `dal:ExternalHighWaterMark`, `dal:RestoreControlledEpoch`, `dal:WriterStartRefusal`, `dal:StoreLocalEpoch` (warned) |
| Privacy and erasure | `dal:PrivacyProfile` | `dal:PersonalData`/`dal:InternalData`/`dal:PublicData`, `dal:PerSubjectGraphDrop`/`dal:CryptoShred`/`dal:NoErasure` |

A composite `dal:DataAccessProfile` is sugar declaring several dimensions at one scope; it decomposes into the same per-dimension model, never a special case of its own.

Every row above resolves on its own, including the extension properties that share a class with another row (`dal:firstWrite`, `dal:etagForm`, `dal:lagWindowMillis`, `dal:txnShards` and the rest). A property declared on a lower-priority node than the node that wins a neighbouring row is still resolved. A node typed with a specific profile class must carry that class's primary value (for example `dal:concurrencyProfile` on a `dal:ConcurrencyProfile`), so an extension property declared on its own goes on a `dal:DataAccessProfile` node. The compiled profile records each resolved value, with `dal:resolvedLiteral` for literal-valued properties.

## 4. Five scope kinds, ranked by whether they need reasoning

| Scope kind | Matches | Needs reasoning |
|---|---|---|
| `dal:GraphPatternScope` | graphs whose IRI starts with `dal:graphPrefix`, for classes named by `dal:coversClass` | no |
| `dal:NamespaceScope` | resources whose own IRI starts with `dal:iriPrefix` | no |
| `dal:ClassScope` | asserted `rdf:type`, optionally the asserted `rdfs:subClassOf*` closure | no |
| `dal:ShapeScope` | resources conforming to a named `sh:NodeShape`, resolved once at compile time | no |
| `dal:EquivalentClassScope` | resources reachable through `owl:equivalentClass`/`owl:intersectionOf` | **yes** |

Resolution runs per target, per dimension: the highest `dal:priority` wins, ties are broken non-reasoning-over-reasoning, and any remaining tie is a compile-time refusal, never a silent pick. Full algorithm: sketch [§3.4](../../docs/developer/sketches/persistence-profile-substrate.md#34-precedence-and-resolution-algorithm).

## 5. Worked example 1: a minimal single-class profile

```turtle
ex:LoanApplicationClass a dal:ClassScope ;
    dal:targetClass ex:LoanApplication ;
    dal:priority "20"^^xsd:integer .

ex:LoanApplicationStrongProfile a dal:DataAccessProfile ;
    dal:appliesTo           ex:LoanApplicationClass ;
    dal:strategy            dal:NamedGraphBoundary ;
    dal:graphIriTemplate    "urn:g:loan-application/{id}" ;
    dal:concurrencyProfile  dal:Optimistic ;
    dal:minConcurrencyLevel dal:Linearizable ;
    dal:orderingGrain       dal:EventGrain ;
    dal:receiptModel        dal:PatchLog ;
    dal:metaTopology        dal:SharedSharded ;
    dal:metaShards          "64"^^xsd:long ;
    dal:uniqueness          ex:LoanApplicationNumberPerBranch .
```

Full fixture: [`examples/baseline-single-class.ttl`](examples/baseline-single-class.ttl). Compiling this (`python -m persistence compile spec/persistence.ttl examples/baseline-single-class.ttl --out /tmp/compiled.ttl`) produces a `dal:CompiledProfile` with nine generated operations (create-if-absent, cas-replace, tombstone-delete, key-claim write and retire, and the gap-scan, fork-detection, revision-multi-txn and txn-multi-revision audits), each pointing at a named template with reified parameter bindings, never embedded SPARQL text.

## 6. Worked example 2: a shared substrate class, two deployments

Two applied ontologies, lending and credit, both deploy the shared substrate class `beh:Behaviour`, each into their own graph family:

```turtle
ex:LendingBehaviourGraphs a dal:GraphPatternScope ;
    dal:graphPrefix "urn:g:lending/behaviour/" ;
    dal:coversClass beh:Behaviour ;
    dal:priority "10"^^xsd:integer .

ex:LendingBehaviourProfile a dal:DataAccessProfile ;
    dal:appliesTo ex:LendingBehaviourGraphs ;
    dal:concurrencyProfile dal:Optimistic ;
    dal:receiptModel dal:PatchLog .

ex:CreditBehaviourGraphs a dal:GraphPatternScope ;
    dal:graphPrefix "urn:g:credit/behaviour/" ;
    dal:coversClass beh:Behaviour ;
    dal:priority "10"^^xsd:integer .

ex:CreditBehaviourProfile a dal:DataAccessProfile ;
    dal:appliesTo ex:CreditBehaviourGraphs ;
    dal:concurrencyProfile dal:ProvidedConcurrency ;
    dal:receiptModel dal:ReceiptOnly .
```

Full fixture, including the bare-class fallback and a reasoning-dependent `dal:EquivalentClassScope` override: [`examples/lending-credit-shared-class.ttl`](examples/lending-credit-shared-class.ttl). **`beh:Behaviour` itself carries no profile.** Authority belongs to whichever applied ontology deploys it, expressed by scoping to that deployment's graph pattern via `dal:coversClass`, which structurally outranks a bare class-level scope (ADR-A78 point 5). The compiler discovers **three** separate targets for `beh:Behaviour` here — lending's deployment, credit's deployment, and the unscoped fallback — because a class alone cannot distinguish two deployments that differ only in which graph they write to; see `persistence.scopes.Target`'s docstring in `tools/persistence` for the reasoning.

A `dal:DataAccessProfile` whose only scope is a bare `dal:ClassScope` targeting a class outside its own namespace triggers `dal:SharedClassProfileWarningShape`, a SHACL warning (not a hard rejection: a deliberate global override is legitimate, escaped via `dal:acknowledgedSharedClassOverride`).

## 7. Worked example 3: a composite-property aggregate, declared via SHACL

`dal:CompositePropertyBoundary` has exactly one authoring surface: `dal:boundaryShape`, an `sh:NodeShape`. An earlier design considered letting an applied ontology assert a domain property as `rdfs:subPropertyOf dal:isCompositeOf`; it was rejected (ADR-A78 point 4) because that carries real OWL entailment consequences for the domain ontology and creates exactly the import dependency this ontology otherwise avoids. A SHACL shape says the same thing by referencing the domain property **by IRI**, and is walked once, at compile time, by `tools/persistence`; no target backend is ever asked to execute SHACL to determine where a write's boundary lies.

```turtle
ex:OrderAggregateShape a sh:NodeShape ;
    sh:targetClass ex:Order ;
    sh:property [ sh:path ex:lineItem ; sh:node ex:LineItemShape ; sh:minCount 1 ] .

ex:LineItemShape a sh:NodeShape ;
    sh:property [ sh:path ex:sku ; sh:datatype xsd:string ] .

ex:OrderBoundaryProfile a dal:AggregateBoundaryProfile ;
    dal:appliesTo         ex:OrderClass ;
    dal:strategy          dal:CompositePropertyBoundary ;
    dal:boundaryShape     ex:OrderAggregateShape ;
    dal:maxTraversalDepth "8"^^xsd:integer .
```

Full fixture: [`examples/composite-property-boundary-shacl.ttl`](examples/composite-property-boundary-shacl.ttl). `ex:lineItem` and (transitively) `ex:sku` are in the aggregate's closure; `ex:customer`, deliberately absent from the shape, is not. The same shape doubles as ordinary SHACL validation for anyone who already maintains it for that purpose (`sh:datatype`, `sh:minCount`, and so on are untouched by the boundary walk, which interprets only `sh:property`/`sh:node`).

## 8. `dal:CapabilitySpec`: an optional, adopter-declared, unverified self-check

The compiler builds no store SPI and consults no live backend anywhere. It always computes an unconditional `dal:CapabilityRequirement` per target from the resolved profile alone. An adopter may **optionally** supply a `dal:CapabilitySpec` — self-authored, never derived from a live SPI or a TCK run — to self-check that requirement against their own stated understanding of their environment:

```turtle
ex:MyFusekiEnvironment a dal:CapabilitySpec ;
    dal:appliesToTarget           ex:LoanApplication ;
    dal:providesCas               "LINEARIZABLE" ;
    dal:providesReasoning         false ;
    dal:providesCommitValidation  "NONE" .
```

Compiling without a spec never drops a candidate scope or downgrades a strategy: the compiler behaves as if the maximum any backend could provide is available, and simply records what the resolution actually depended on. See sketch [§3.6](../../docs/developer/sketches/persistence-profile-substrate.md#36-reasoning-dependency-and-capability-self-checks) for the full design and the rationale for why this compiler cannot and does not verify a spec's accuracy against anything real.

## 9. Worked example 4: identity, epoch and privacy configuration

LATTICE does not pick an epoch authority, an erasure mechanism, or an identity-minting pattern for an adopter (ADR-A82, [iri-identity-patterns.md](../../docs/architecture/iri-identity-patterns.md)). It documents the options and their consequences, and this vocabulary is where an adopter's choice becomes explicit, so the compiler and any runtime component that needs to know — for example, whether to guard a write against a dataset-level epoch, or whether a graph is safe to drop for erasure — can read it instead of assuming a default.

```turtle
ex:ClaimantEntity a dal:ClassScope ;
    dal:targetClass ex:Claimant ;
    dal:priority "20"^^xsd:integer .

ex:ClaimantIdentity a dal:IdentityProfile ;
    dal:appliesTo          ex:ClaimantEntity ;
    dal:resourceRole       dal:EntityRole ;
    dal:identityStrategy   dal:SurrogateClaimedIdentity ;      # mutable, sensitive key (an email)
    dal:namingAuthority    "adopter" .

ex:ClaimantEmailUnique a dal:UniquenessConstraint ;           # the key the claimed surrogate is minted from;
    dal:constraintId        "claimant-email-unique" ;          # without it the compiler refuses the identity profile
    dal:appliesTo            ex:ClaimantEntity ;
    dal:keyProperty          ( ex:email ) ;
    dal:scopeProperty        ex:tenant ;
    dal:normalizePipeline    dal:NfkcTrimCasefold ;
    dal:onViolation          dal:Reject .

ex:ClaimantEvents a dal:IdentityProfile ;                      # a second role for the same class
    dal:appliesTo                     ex:ClaimantEntity ;
    dal:resourceRole                  dal:EventOccurrenceRole ;
    dal:identityStrategy              dal:DerivedHashIdentity ;
    dal:eventIdentityStrategy         dal:PositionDerivedEvent ;
    dal:occurrenceNamespaceDerivation dal:HashedTargetDerivation ;
    dal:uniquenessWitnessRequired     true ;
    dal:digestScheme                  ex:ClaimantEventDigest .     # SHA-256, 128 bits, base32

ex:ClaimantEpoch a dal:EpochProfile ;
    dal:appliesTo          ex:ClaimantEntity ;
    dal:epochAuthority     dal:ExternalHighWaterMark ;
    dal:epochCoordinatorBinding "postgres://coord/epoch_watermark" ;
    dal:epochGuardScope    dal:DatasetLevelGuard ;
    dal:erasureRegisterBinding  "postgres://coord/erasure_register" ;
    dal:erasureReplayOnRestore  true .

ex:ClaimantPrivacy a dal:PrivacyProfile ;
    dal:appliesTo          ex:ClaimantEntity ;
    dal:privacyClass       dal:PersonalData ;
    dal:erasureStrategy    dal:PerSubjectGraphDrop ;
    dal:erasurePrecedence  dal:ErasureWins .

ex:ClaimantReceipts a dal:DataAccessProfile ;
    dal:appliesTo          ex:ClaimantEntity ;
    dal:receiptModel       dal:ReceiptOnly ;          # required, given personal data + graph-drop erasure below
    dal:perSubjectScoped   true .
```

`dal:PersonalDataReceiptCompatibilityShape` (`shapes/constraints.ttl`) rejects this same scope if `dal:receiptModel` were `dal:PatchLog` or `dal:SnapshotPerRevision` without `dal:perSubjectScoped true` or `dal:erasureStrategy dal:CryptoShred` — not because the framework prefers `dal:ReceiptOnly`, but because the other two models keep a second, immutable copy of the payload that a per-subject graph drop cannot reach. An adopter who genuinely needs replay over personal data selects `dal:CryptoShred` instead and specifies key custody and an as-of failure policy for shredded revisions.

The compiler resolves the two identity roles independently, `identity:EntityRole` and `identity:EventOccurrenceRole` (`persistence-compiler-iri-sync` Slice 3). The privacy profile is validated by SHACL and is resolved by the compiler from Slice 4.

Full fixture: [`examples/identity-epoch-privacy-profile.ttl`](examples/identity-epoch-privacy-profile.ttl), with two Slice 3 negative fixtures, [`examples/invalid-claimed-identity-without-key.ttl`](examples/invalid-claimed-identity-without-key.ttl) and [`examples/invalid-position-event-without-derivation.ttl`](examples/invalid-position-event-without-derivation.ttl). Slice 1 authored two epoch-only fixtures: [`examples/epoch-dataset-level-guard.ttl`](examples/epoch-dataset-level-guard.ttl) and [`examples/warning-epoch-unsafe-restore.ttl`](examples/warning-epoch-unsafe-restore.ttl). [`examples/append-stream-dataset-guard.ttl`](examples/append-stream-dataset-guard.ttl) covers an append-only stream under the dataset-level guard. Slice 2 added [`examples/extension-properties.ttl`](examples/extension-properties.ttl), every extension property declared on its own profile node, and [`examples/invalid-lagwindow-missing.ttl`](examples/invalid-lagwindow-missing.ttl), refused by `dal:LagWindowRequiredShape` and by the compiler.

## 10. Repository layout

```
ontology/persistence/
  spec/persistence.ttl       the vocabulary
  shapes/constraints.ttl     SHACL shapes validating dal: instance data (§3.9)
  examples/                  worked examples 1-3 above, plus one negative
                             fixture per cross-axis check (see the guide's
                             §3.5 table), SHACL-level fixtures, and the
                             epoch, append-stream and extension-property
                             fixtures of persistence-compiler-iri-sync
  docs/                      the precedence algorithm and boundary-strategy
                             design, for a reader who has not read the sketch
```

The compiler that consumes this ontology lives in `tools/persistence`, per the repository's `ontology/` (semantic assets) versus `tools/` (executable reference implementations) split.

## 11. Appendix

### Cross References

| Document/Link | Details |
|---|---|
| [rdf-sparql-patterns-guide.md](../../docs/architecture/rdf-sparql-patterns-guide.md) | RDF persistence patterns |
| [persistence-profile-substrate.md](../../docs/developer/sketches/persistence-profile-substrate.md) | Original design sketch |
| [iri-identity-patterns.md](../../docs/architecture/iri-identity-patterns.md) | identity patterns a future profile dimension will configure |
| [ADR-A78](../../docs/architecture/decisions/ADR-A78-persistence-profile-substrate-and-aggregate-boundaries.md), [ADR-A79](../../docs/architecture/decisions/ADR-A79-persistence-compiler-toolchain.md), [ADR-A80](../../docs/architecture/decisions/ADR-A80-housekeeping-component-boundary.md), and [ADR-A82](../../docs/architecture/decisions/ADR-A82-framework-neutral-identity-pattern-selection.md) | Governing Decisions |

