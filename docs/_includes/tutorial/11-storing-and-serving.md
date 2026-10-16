<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

## 11. Storing and serving it
{: #storage}

Everything so far describes what the facility *is*. A system also has to write it to a store while
other writers are busy, keep keys unique, keep history, erase personal data on request, and answer
common questions fast. Two parts of LATTICE that sit beside the layer stack handle this. Persistence
decides how data is written. Surface decides how it is served.

### Why a graph store needs help

A relational database gives you three things you barely notice until they are gone: a `UNIQUE`
index, a row that two writers collide on, and an `UPDATE` that reports how many rows it touched. A
SPARQL store gives none of them. A graph is a set of triples, so two writers who both insert the same
"version 42" triple do not collide. They merge silently, and the record can end up both "paid" and
"cancelled". An update endpoint replies with success whether it changed ten thousand triples or none.

None of this is a defect of any one store. It follows from set semantics. The Persistence README's
section on
[why persistence in RDF is hard](https://github.com/nebularis/lattice/blob/main/ontology/persistence/README.md)
walks through it, and the
[RDF and SPARQL patterns guide](https://github.com/nebularis/lattice/blob/main/docs/architecture/rdf-sparql-patterns-guide.md)
documents each remedy and what it costs.

### Persistence: choose the patterns, generate the SPARQL

Persistence (`dal:`, for data access layer) does not make storage decisions for you. It records the
ones you make, per class and per deployment, along a set of dimensions:

- the **aggregate boundary**, what changes together as one unit
- **concurrency**, optimistic compare-and-set, append-only, locking, or left to the store
- **ordering**, the grain at which changes are sequenced
- **receipts and history**, how much of each change is kept
- **uniqueness** of natural keys, enforced at write time as chapter 4 promised
- **identity minting**, how IRIs are generated
- **privacy and erasure** for personal data

A compiler (`tools/persistence`) reads your choices and emits portable SPARQL 1.1 operations and
identity-minting recipes, with audits that detect gaps and forks after the fact. It is a design-time
tool. It generates SPARQL and does not run a store.

The example below is the worked conflict from Persistence's design. Two applied ontologies, lending
and credit, both store instances of one shared Behaviour class, each in its own family of named
graphs, and each wants different guarantees.

<!-- source: ontology/persistence/examples/lending-credit-shared-class.ttl -->
```turtle
ex:LendingBehaviourGraphs a dal:GraphPatternScope ;
    dal:graphPrefix "urn:g:lending/behaviour/" ;
    dal:coversClass beh:Behaviour ;
    dal:priority "10"^^xsd:integer .

ex:LendingBehaviourProfile a dal:DataAccessProfile ;
    dal:appliesTo           ex:LendingBehaviourGraphs ;
    dal:concurrencyProfile  dal:Optimistic ;
    dal:receiptModel        dal:PatchLog .

# 2. credit's own deployment, scoped the same way, disjoint graph prefix.
ex:CreditBehaviourGraphs a dal:GraphPatternScope ;
    dal:graphPrefix "urn:g:credit/behaviour/" ;
    dal:coversClass beh:Behaviour ;
    dal:priority "10"^^xsd:integer .

ex:CreditBehaviourProfile a dal:DataAccessProfile ;
    dal:appliesTo           ex:CreditBehaviourGraphs ;
    dal:concurrencyProfile  dal:ProvidedConcurrency ;
    dal:receiptModel        dal:ReceiptOnly .
```

Read each pair as a **scope**, where the rule applies, and a **profile**, what applies there.
Lending's graphs get optimistic concurrency and a log of every patch. Credit's rely on the store's
own concurrency and keep only receipts. The file adds a low-priority fallback for the class anywhere
else, and a higher-priority override for high-value instances wherever they are stored. When scopes
overlap, priority and the kind of scope decide which profile wins, and the compiler refuses an
ambiguous tie rather than picking one.

The relational counterpart is the set of decisions a DBA makes per table or per schema, such as
isolation level, audit triggers, partitioning and retention, written as data that a compiler turns
into code. Two features stand out.

- **Your ontology never knows.** Persistence refers to classes and graphs by IRI and imports no layer.
  A storage decision can be added, changed or removed without touching the model.
- **It is optional.** An adopter who only reads LATTICE data, or uses a store with its own
  guarantees, can ignore it.

[Source on GitHub](https://github.com/nebularis/lattice/blob/main/ontology/persistence/examples/lending-credit-shared-class.ttl).

### Surface: restating values where questions need them

Graph questions often follow long paths. A subscription's currency, in Surface's example, is
reachable only through its plan and the plan's pricing, three hops per subscription. A dimensional
modeller would denormalise the currency onto the fact. Surface declares that restatement, called a
**promotion**, as a governed contract.

<!-- source: ontology/surface/examples/saas-subscription-currency.ttl -->
```turtle
ex:subscription-currency-promotion a srf:PromotionContract ;
    fnd:hasIdentity ex:subscription-currency-identity ;
    fnd:hasGovernanceState fnd:Active ;
    srf:contractKey "subscription-currency" ;
    srf:carrier ex:Subscription ;
    srf:hasPathStep ex:currency-step-0 , ex:currency-step-1 , ex:currency-step-2 ;
    srf:targetNamespace "https://example.org/lattice/surface/saas/exec#"^^xsd:anyURI ;
    srf:realisationMode srf:Materialised ;
    srf:surfaceProfile ex:profile-v1 ;
    srf:promotesTo <https://example.org/lattice/surface/saas/exec#subscriptionCurrency> ;
    srf:sourceFidelity srf:ExactSource .
```

- **`srf:carrier`** is the class that receives the restated value, here the subscription.
- **The path steps** are the three hops, plan, pricing, currency, declared in order.
- **`srf:promotesTo`** names the new direct property.
- **`srf:realisationMode`** says whether the compiler writes the triples (`srf:Materialised`), emits
  only definitions that a reasoner would apply (`srf:DefinitionOnly`), or both.
- **`srf:sourceFidelity`** records how faithful the restated value is. `srf:ExactSource` means it is
  the source value itself, reached by traversal alone, rather than a computed or crosswalked value.

The output is a **derived artefact**, like chapter 5's bound meaning. It is never the source of
truth, it can be rebuilt at any time, and the profile records the generator version and settings
that built it, so a stale restatement can be found. Surface also builds **indexes**, symbols for
looking things up by value. For mappings too complex for a single path, it hands the job to MORK's
compilers. Chapter 4's keys depend on Surface too. A version can carry its identity's keys directly,
for consumers without a reasoner, through a Surface promotion.
[Source on GitHub](https://github.com/nebularis/lattice/blob/main/ontology/surface/examples/saas-subscription-currency.ttl).
