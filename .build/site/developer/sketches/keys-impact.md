<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Keys: impact on Persistence, Surface and the Foundation cascade

**Unit:** [`computable-contract-substrate`](../plans/computable-contract-substrate.md), slice F1
phase 0. **Status:** analysis for the F1 gate, 2026-10-03. G2 and G3 answered, G1 revised (§6).
**Reads with:** [ADR-A114](../../architecture/decisions/ADR-A114-external-and-natural-keys.md)
(Proposed), the [Persistence README](../../../ontology/persistence/README.md), the
[Surface README](../../../ontology/surface/README.md), the
[identity minting specification](../../architecture/identity-minting-specification.md).

---

## 1. Summary

ADR-A114 needs **no change to Persistence's compiler, Surface's ontology or Surface's compiler**.
Persistence needs one new optional document, `persistent-foundation`. Keys need one modelling
convention Persistence imposes: one key class per scheme, defined by an OWL restriction on the
scheme. The cascade is larger than the ADR
says, and takes Instrument's next version from C6.

| # | Subsystem | Finding | Change | Where |
|---|---|---|---|---|
| P1 | Persistence | a uniqueness constraint on `fnd:naturalKey` works as the compiler stands. Its key component is the key node's IRI, and the mandatory normalisation pipeline is applied to that IRI, harmlessly | none. Record the reasoning | F1, docs |
| P2 | Persistence | identity and privacy profiles target classes, so minting key IRIs differently per scheme needs one key class per scheme | a key class per scheme, `C ≡ ∃fnd:keyScheme.{S}`, required by shapes in `persistent-foundation` | F1, gate question G1 |
| P3 | Persistence | each scheme's key minting is an existing identity profile, with a uniqueness constraint on `fnd:keyValue` that also guarantees one key node per value | examples and shapes in `persistent-foundation` | F1 |
| P4 | Persistence | all three violation policies apply to natural keys. Merge records `dal:mergeRelation`, never `owl:sameAs`, as ADR-A114 requires | none | F1, docs |
| P5 | Persistence | a sensitive scheme's keys take a surrogate with a keyed claim and a privacy profile other than public on their key class, and a personal-data scheme's a `dal:PersonalData` one | shapes in `persistent-foundation` | F1 |
| P6 | Persistence | `persistent-foundation` is Persistence's first document importing a layer | new document, catalog entry, README section | F1 |
| P7 | Persistence | the compiler could derive the natural-key uniqueness constraint from `dal:PersistenceKeyed` on its own | none now | follow-up FU-F1b |
| S1 | Surface | an index over keys adds nothing: the key node is already the lookup symbol, and a key space is not an enumerable population | none | F1, docs |
| S2 | Surface | a promotion contract can restate an identity's natural key on each version, onto `fnd:externalKey`, never onto `fnd:naturalKey` | example only | F1 |
| S3 | Surface | the same restatement could instead be a Foundation property chain, for adopters without Surface | none, or one axiom | gate question G2 |
| S4 | Surface | the cascade moves Surface to 0.6.0: the compiler's ontology constant changes, and surfaces generated before F1 must be regenerated | one constant | F1 |
| C1 | cascade | 15 documents pin `foundation/0.3.0` directly and 9 more transitively, so 25 documents bump, not 17 | ADR-A114 corrected | F1 |
| C2 | cascade | Instrument takes 0.8.0 in the cascade, the version C6 had planned | C6 to C9 shift by one MINOR | gate question G3 |
| C3 | cascade | MORK's teaching pack pins a hash of its ontology, which the re-pin changes | `build:mtp`, lock committed | F1 |
| C4 | cascade | eleven test modules and one compiler constant name a cascaded version | updated with the cascade | F1 |

## 2. Persistence

### P1. Uniqueness on `fnd:naturalKey`

A `dal:UniquenessConstraint` names its key properties (`dal:keyProperty`), a normalisation pipeline,
an optional scope and claim schemes. The compiler (`recipes.py`, `resolver.py`) reads only the
property IRIs, and the generated guarded write (`key-claim-write.mustache`) takes a claim IRI the
caller computes as an HMAC over the tuple-encoded normalised key components. Nothing assumes a key
value is a literal: for `fnd:naturalKey` the component is the key node's IRI as a string.

The compiler requires one of the three pipelines, so the IRI is normalised before the claim is
computed. `NfkcTrimCasefold` would fold its case. That is harmless for minted key IRIs: two key IRIs
of one scheme can differ only in case if their values do, and their values are normalised by the
same pipeline before minting, while hash digests use a single-case alphabet (base32) or lowercase
hex. Two distinct key nodes never fold to one claim. An exact pipeline (no case or compatibility
mapping) would be the cleaner fit for IRI-valued keys, and is a change to the minting specification,
out of F1's scope. Recorded as follow-up FU-F1a in the CCS plan, owned by `identity-minting`.

The CompositePropertyBoundary check (`validator.py`) requires a key property to be reachable within
the boundary shape. A natural key on a persistent identity is one step from it, so a boundary shape
naming `fnd:naturalKey` satisfies it.

### P2. One key class per scheme

ADR-A114 decision 6 mints key IRIs per scheme: derived hash for one, natural key for another, a
surrogate with a keyed claim for a sensitive scheme. Persistence resolves every profile for a **target**,
and a target is a class, optionally with a graph deployment (`scopes.py`, `Target`). A
`dal:ShapeScope` is resolved once, at compile time, against classes, not per instance. So all
`fnd:Key` instances get one identity profile unless the schemes' keys are told apart by class or by
graph:

| Option | How | Cost |
|---|---|---|
| **(a) a key class per scheme** | `ex:UmrKey ⊑ fnd:Key`, asserted on every UMR key, targeted by a `dal:ClassScope` | the scheme's declarer declares the class, and the writer asserts it. No compiler change |
| (b) a graph family per scheme | keys of each scheme written into their own graphs, targeted by `dal:GraphPatternScope` | ties a modelling distinction to storage layout |
| (c) a target keyed on a value | the compiler learns targets of `(class, keyScheme)` | a compiler change for one use |

**Recommended: (a).** It also gives P5's privacy profile its target.

**How the class is tied to its scheme (revised at the gate).** The first draft linked a key class to
its scheme with a Persistence property, `dal:keyClassFor`. An OWL axiom does the same job with no new
term, and means something to adopters without Persistence:

```turtle-example
ex:UmrKey a owl:Class ;
    rdfs:subClassOf fnd:Key ;
    owl:equivalentClass [ a owl:Restriction ;
        owl:onProperty fnd:keyScheme ; owl:hasValue ex:umr ] .
```

A scheme stays a plain individual of `fnd:KeyScheme`, an OWL class, not a SKOS concept. Its key class
is a second IRI defined from it, so no punning is needed. Punning the scheme's IRI as its own key
class was considered and rejected: OWL 2 DL treats a punned class and individual as unrelated, so a
reasoner could derive neither the class from `fnd:keyScheme` nor the scheme from `rdf:type`. The `dal:`
configuration does pun, by design (`dal:targetClass` and `dal:coversClass` are object properties
whose values are classes, LATTICE's convention for naming another layer's terms without importing
it), and is read as RDF by the compiler and by SHACL, never by a DL reasoner. A `dal:ClassScope` on
`ex:UmrKey` is that ordinary case.

Enforcement is by SHACL in `persistent-foundation`, run on the adopter's ontology, configuration and
data, since the compiler matches asserted types and never reasons:

| Shape | Checks | Graph |
|---|---|---|
| scheme has a class | every `fnd:KeyScheme` has exactly one class of the restriction's form. These shapes run only where an adopter uses `persistent-foundation` | ontology |
| class has a profile | every such class is the `dal:targetClass` of a `dal:ClassScope` with an identity profile, and for a sensitive scheme, the P5 profiles | configuration |
| key is typed | every `fnd:Key` whose scheme has a key class is asserted a member of it, and of no other scheme's | data |

The third shape matters beyond Persistence's targeting. OWL makes no unique-name assumption, and
`fnd:keyScheme` is functional, so a key asserted `ex:UmrKey` while carrying `fnd:keyScheme ex:lei`
would lead a reasoner to infer `ex:umr owl:sameAs ex:lei`, a silent merge of two schemes. The shape
reports it instead. Foundation's examples also declare their schemes `owl:AllDifferent`, which turns
the same mistake into an inconsistency for reasoner users.

`fnd:Key` stays usable without a key class by an adopter who does not use Persistence.

### P3. Minting a scheme's keys

Each key class takes an existing `dal:IdentityProfile`:

| Scheme | Strategy | Needs |
|---|---|---|
| UMR, company number (case-insensitive, public) | `dal:DerivedHashIdentity` or `dal:NaturalKeyIdentity` | a `dal:keyConstraint`: a uniqueness constraint on `( fnd:keyValue )` for the key class, scoped by tenant, with the scheme's normalisation as `dal:normalizePipeline` |
| a national ID (sensitive) | `dal:SurrogateClaimedIdentity` | the same constraint with a `dal:ClaimScheme` (HMAC under a tenant key) |

The key constraint does double duty: it is what the recipe mints from, and it guarantees at write
time that one value of one scheme is one key node. `fnd:keyNormalisation` (a string) and
`dal:normalizePipeline` (an individual) must name the same pipeline: a shape in
`persistent-foundation` compares the scheme's string with the pipeline's local name.

### P4. Violations

The guarded write prevents a second claim on one natural key. The reconciler for slipped duplicates
follows `dal:onViolation`: `Reject` audits, `Quarantine` copies the owners for review, `Merge` records
`dal:mergeRelation` from each non-canonical owner to the canonical one and is documented as never
`owl:sameAs`. That is exactly the behaviour ADR-A114 decision 8 assigns to `dal:PersistenceKeyed`.
`persistent-foundation`'s default constraint uses `Reject`.

### P5. Sensitive schemes

For a scheme with `fnd:sensitiveDataScheme true`, `persistent-foundation`'s shapes require its key
class to have a `dal:SurrogateClaimedIdentity` profile (ADR-A51, ADR-A114 decision 6) and a
`dal:PrivacyProfile` whose class is not `dal:PublicData`. Sensitive is wider than personal, so a
second, optional flag says which sensitive schemes hold personal data: for
`fnd:personalDataScheme true` (which Foundation's shapes allow only with
`fnd:sensitiveDataScheme true`), the privacy profile must be `dal:PersonalData`. Persistence's
existing rules then apply: no `dal:NoErasure`, and a replay-capable receipt model only with per-subject
scoping or crypto-shredding. Erasing a person removes their key node and its value. A `fnd:naturalKey` triple pointing at it is
removed with the subject's graph under `dal:PerSubjectGraphDrop`, or left dangling where it lives
outside it, which the privacy profile's scope decides.

### P6. `persistent-foundation`

| Item | Choice |
|---|---|
| file | `ontology/persistence/spec/persistent-foundation.ttl`, shapes in `ontology/persistence/shapes/persistent-foundation.ttl`, both authored files beside `persistence.ttl` |
| version IRI | `…/lattice/persistent-foundation/0.1.0`, its own release row and tag |
| imports | `foundation/0.4.0` only. The `dal:` configuration ontology still imports no layer (Persistence README §1, updated to say so) |
| holds | `dal:PersistenceKeyed ⊑ fnd:NaturallyKeyed`, the default natural-key uniqueness constraint (as a template an adopter scopes), the P2 and P5 shapes |
| import guard | Persistence is outside the layer order. The guard's checks do not apply, as for Surface and MORK |

### P7. A compiler follow-up

The compiler could generate the natural-key uniqueness constraint for every class that is
`dal:PersistenceKeyed`, so an adopter declares the mixin and nothing else. Today the adopter scopes
the default constraint to their class. Worth doing once a deployment has several keyed classes. Not
needed for F1. Recorded as follow-up FU-F1b in the CCS plan.

## 3. Surface

### S1. No index

Surface's per-value index forms (`NominalClass`, `MembershipAssertion`, `ClosureRelation`) mint a
symbol per value and need an enumerable population (a scheme contract, a class extent, an enumerated
set). A key space is neither enumerable nor bounded: every UMR ever issued. And the retrieval an index
would provide already exists: the key node is a symbol, so "everything carrying this key" is one
triple pattern, `?x fnd:externalKey key:umr-B0123ABC20261234`. Making keys object-valued nodes is what
makes an index unnecessary.

### S2. Promotion onto versions

A versioned thing carries its keys on its identity, so finding a version by key is one hop more
than finding an actor. A `srf:PromotionContract` removes the hop:

```turtle-example
ex:version-keys a srf:PromotionContract ;
    srf:contractKey "version-keys" ;
    srf:carrier ex:Agreement ;                       # any fnd:Version class
    srf:hasPathStep ex:step-0 , ex:step-1 ;
    srf:promotesTo fnd:externalKey ;                 # authored, locating
    srf:sourceFidelity srf:ExactSource ;
    srf:realisationMode srf:Materialised ;
    srf:targetNamespace <https://example.org/generated/> ;
    srf:surfaceProfile ex:default-profile .

ex:step-0 srf:stepIndex 0 ; srf:stepProperty fnd:hasIdentity ; srf:stepDirection srf:Forward .
ex:step-1 srf:stepIndex 1 ; srf:stepProperty fnd:naturalKey  ; srf:stepDirection srf:Forward .
```

It promotes onto `fnd:externalKey`, an authored property, so its signature scope is the source's,
which Surface allows for an exact, materialised promotion. **It must never promote onto
`fnd:naturalKey`:** every version would then hold its identity's natural key, the versions would
become `fnd:NaturallyKeyed` by the property's domain, and Foundation's uniqueness shape would report
them as different things sharing one key. A promotion onto a generated property is equally valid,
where an adopter wants promoted keys visibly apart from authored ones.

### S3. Or a property chain in Foundation

The same restatement can be one OWL axiom in Foundation:
`fnd:externalKey owl:propertyChainAxiom ( fnd:hasIdentity fnd:externalKey )`. Every version then
carries, to a reasoner, each key of its identity, natural ones included through
`fnd:naturalKey ⊑ fnd:externalKey`. It is valid OWL 2 DL (`fnd:externalKey` is not used where a simple
property is required). It gives meaning to adopters without Surface, as `fnd:MergedOnNaturalKey`
does for natural keys, and costs nothing at runtime, where no reasoner runs (ADR-A83). Gate question
G2.

### S4. The cascade's effect on Surface

The cascade takes `surface` and `surface-vocab` from 0.5.0 to 0.6.0. The Surface compiler names the
ontology version it imports into every generated artefact (`tools/surface/src/surface/namespaces.py`,
`SURFACE_ONTOLOGY`), so the constant moves to 0.6.0 in the same change. A surface generated before
F1 imports `surface/0.5.0`, which the catalog no longer maps, and is regenerated. No committed
generated surface or golden file names 0.5.0.

## 4. The cascade

ADR-A86: a document whose only change is an import update takes the bump level of the imported
change. Foundation's change is additive, so every document in its import closure takes a MINOR.

| Document | From | To | Pins Foundation |
|---|---|---|---|
| foundation | 0.3.0 | 0.4.0 | (the change) |
| foundation-vocab | 0.3.0 | 0.4.0 | directly |
| vocabulary | 0.3.0 | 0.4.0 | directly |
| quantification | 0.5.0 | 0.6.0 | directly |
| party | 0.5.0 | 0.6.0 | directly |
| party-vocab | 0.5.0 | 0.6.0 | through party |
| eligibility | 0.7.0 | 0.8.0 | directly |
| eligibility-vocab | 0.8.0 | 0.9.0 | through eligibility |
| wording | 0.3.0 | 0.4.0 | directly |
| wording-vocab | 0.3.0 | 0.4.0 | through wording |
| behaviour | 0.10.0 | 0.11.0 | directly |
| behaviour-runtime | 0.10.0 | 0.11.0 | through behaviour |
| behaviour-vocab | 0.10.0 | 0.11.0 | through behaviour |
| instrument | 0.7.0 | 0.8.0 | directly |
| instrument-vocab | 0.7.0 | 0.8.0 | through instrument |
| surface | 0.5.0 | 0.6.0 | directly |
| surface-vocab | 0.5.0 | 0.6.0 | through surface |
| MORK (`…/ontologies/Mork`) | 0.4.0 | 0.5.0 | directly |
| applied classification | 0.1.0 | 0.2.0 | directly |
| applied classification-vocab | 0.1.0 | 0.2.0 | through classification |
| insurance common | 0.1.0 | 0.2.0 | directly |
| insurance common-vocab | 0.1.0 | 0.2.0 | through common |
| insurance peril | 0.1.0 | 0.2.0 | directly |
| insurance peril-vocab | 0.1.0 | 0.2.0 | directly |
| applied capacity execution | 0.10.0 | 0.11.0 | directly |

Twenty-five documents, each with a release row and a tag. MORK's governance example
(`ontology/mork/examples/Governance/GovernanceAndVersioning.ttl`) pins `foundation/0.3.0` without a
version of its own: it re-pins with no tag. Shapes and projections import nothing and are unchanged.

**C2. Instrument's version.** The cascade gives Instrument 0.8.0, which C6 had planned for its
rewrite. Options: C6 takes 0.9.0 and C7a to C9 each shift by one MINOR (0.10.0 to 0.13.0), or the
cascade leaves Instrument's re-pin to C6, which is not possible, since Instrument's closure must
resolve once `foundation/0.3.0` leaves the catalog. **Recommended:** shift C6 to C9 by one, in the
plan and ADR-A104's Consequences.

**C3. MORK's teaching pack.** `ontology/mork/mtp/data/pins.lock.json` pins a hash of the MORK
ontology, which the re-pin changes. `mise run build:mtp` regenerates the lock, and `check:mtp`
verifies it, in the same change.

**C4. Version names in code and tests.** `tools/import_guard.py`, `tools/surface/.../namespaces.py`
(S4), and the test modules `test_applied_shared_contracts.py`, `test_behaviour_nested.py`,
`test_behaviour_records.py`, `test_behaviour_split.py`, `test_import_guard.py`,
`test_ontology_releases.py`, `test_peril_vocabulary.py` and `test_wording.py` name cascaded versions,
and update with it. A test that only names a version to find a document keeps its assertions.

**C5. Branches.** Every branch that would edit a document in the table waits for F1 to merge. On
2026-10-03 the AIR branches `air/2.2-characteristics`, `air/3.3-readings-swrl-owl` and
`air/4.1-exposure-core` have no commits and start from the merged `main`.

## 5. What F1 then contains

1. Foundation 0.4.0 with ADR-A114's terms and shapes, and a README section on keys.
2. `persistent-foundation` 0.1.0 (P2, P3, P5, P6), with its example and a Persistence README section
   recommending it.
3. Surface's example promotion contract (S2), and the compiler constant (S4).
4. The cascade (C1 to C5).
5. ADR-A114 corrected: 25 documents, not 17. Under G3, ADR-A104 and the plan's version numbers for
   C6 to C9.

Follow-up, not F1: an exact normalisation pipeline (P1, FU-F1a) and the derived constraint (P7,
FU-F1b), each when a deployment needs it. Both are in the CCS plan's F1 follow-ups table.

## 6. Questions for the gate

- **G1 (P2).** One key class per scheme, linked by `dal:keyClassFor`. Recommended. **Revised at the
  gate:** linked instead by an OWL restriction on the scheme, with the shapes of P2. Awaiting
  confirmation.
- **G2 (S3).** Add `fnd:externalKey owl:propertyChainAxiom ( fnd:hasIdentity fnd:externalKey )` to
  Foundation, so versions locate by their identity's keys for reasoners, with Surface's promotion for
  everyone else. Recommended: yes, for the same reason `fnd:MergedOnNaturalKey` exists.
  **Accepted** 2026-10-03.
- **G3 (C2).** C6 takes Instrument 0.9.0, and C7a to C9 shift by one MINOR. Recommended.
  **Accepted** 2026-10-03.
- **The gate itself:** accept this analysis and ADR-A114.
