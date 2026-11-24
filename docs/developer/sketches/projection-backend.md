<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Sketch: a projection backend, from a Surface projection contract to queries a step runs

**Unit:** `studio-visual-authoring` (SVA), slice SVA-S2d, raised on 2026-11-23 when the maintainer chose that projections are built in this unit, design first
**Status:** sketch. SVA-Q24 to SVA-Q30 answered by the maintainer on 2026-11-23. SVA-Q31 to SVA-Q35, raised by SVA-S2g on 2026-11-24, answered by the maintainer on 2026-11-24. No question is open. SVA-S2g built the graph construction case on 2026-11-24
**Plan:** [studio-visual-authoring.md](../plans/studio-visual-authoring.md), slices SVA-S2d and SVA-S2c
**Builds on:** ADR-A16, ADR-A17, ADR-A18, ADR-A19, ADR-A20, ADR-A23 and ADR-A41 (all Accepted), ADR-A154 with its addendum of 2026-11-20, and `tools/mork_rdf`

## 1. The scene

A Surface projection contract states a derived result on a carrier from evidence the carrier holds, for example the SaaS example's annual recurring revenue on each subscription from its monthly price and its billing periods a year (`ontology/surface/examples/saas-subscription-arr-projection.ttl`). ADR-A18 lowers a projection into MORK mapping nodes and never emits an executable artefact for it, and ADR-A19 and ADR-A23 leave compiling those nodes to a MORK backend. ADR-A41 lowers through a graph-reference job into a staging namespace, with an engineering review for a derivation.

What exists, read on 2026-11-23:

| Piece | Today |
|---|---|
| the contract | one projection kind of four (graph construction, derivation, join, expansion), role bindings of six kinds, each `srf:ProjectionRoleBinding` holding a role, a property and a carrier, and a backend policy. Nothing states the operation a derivation performs: that ARR is the product of its two inputs is written nowhere |
| the lowering | `lower_projection` writes one bare `mork:DataMapping` with a targeting spec and parameter bindings naming each role's property, and a note that no backend has compiled it. No scheme, concept, path mapping or expression |
| MORK's expressions | a monoid over strings, literal, reference, concatenation, interpolation and lookup, compiled to `STR`, `CONCAT` and `ENCODE_FOR_URI` for names and IRIs. No arithmetic |
| `mork_rdf` | compiles a scheme over an RDF source to CONSTRUCT queries, case by case. Its nearest case to a derivation is an assertion under a root over the carrier class, with two gaps: one reference gives one value, and no identity rule writes onto the source node itself, since a datum is always minted and typed |
| the studio | no worker lowers or compiles a projection, the surface compile job reads promotions and indexes alone, and the facility sample declares no projection |

A naming hazard: in MORK, `mork:ProjectionMapping` is a generative mapping that produces lookup classes, the older sense of a promotion. A Surface projection is not one, so the design never types its lowered node with that class.

## 2. The design

**The contract states the operation.** A derivation projection gains an expression over its role bindings, in a small closed vocabulary of typed operations, for example `srf:Product` of the two required-evidence roles, written on the result-target binding. The contract states and the compiler executes (the modelling rules), so the operation is in the contract, where its law can be checked, and never in a backend's text. ADR-A18's lowering stays deterministic, since it only carries the expression across.

**MORK gains value expressions.** Beside its string expressions, MORK gains numeric expressions over references: sum, difference, product, quotient, a literal of a stated datatype, rounding to a stated scale, and a choice of two values on a comparison (SVA-Q25 (b), taken now to get ahead of the contracts that will need them), typed so a mixed or untyped operand is refused. A lowered derivation is a `mork:DataMapping` in a scheme of its own, with a root iterating the carrier class, a reference for each evidence role, and an assertion of the result property whose value is the expression.

**`mork_rdf` writes onto the focus node.** A new identity rule, the source node itself, lets an assertion write the result property on the carrier without minting or typing a datum. The expression compiles to SPARQL arithmetic in a `BIND`, its operands each bound by a reference's path, and a carrier missing an operand writes nothing, which a check reports.

**The studio compiles and runs it.** The surface compile job lowers each projection and compiles its scheme with `mork_rdf`, beside the promotions' maintenance, and records the engineering review ADR-A41 asks of a derivation as a finding the author sees. A step's projection part runs the compiled scheme over the world before and after with `mork_rdf`'s driver, which is the Python worker's under ADR-A154's addendum.

### 2.1 Worked example, ARR

The contract, abridged, with the new expression:

```turtle
ex:subscription-arr-projection a srf:ProjectionContract ;
    srf:projectionKind srf:DerivationProjection ;
    srf:hasRoleBinding ex:arr-price, ex:arr-periods, ex:arr-result .
ex:arr-result srf:roleKind srf:ResultTargetRole ; srf:bindsProperty saas:annualRecurringRevenue ;
    srf:derivedAs [ a srf:Product ; srf:operand ex:arr-price, ex:arr-periods ] .
```

Lowered, in MORK, abridged:

```turtle
exec:arr-scheme a mork:MappingScheme .
exec:arr-root a mork:Datum ; mork:mappingScheme exec:arr-scheme ; mork:mappingFor exec:SubscriptionConcept ;
    mork:identity mork:SourceNode .
exec:arr-value a mork:DataMapping ; mork:mappingScheme exec:arr-scheme ; mork:exactRBoxMatch saas:annualRecurringRevenue ;
    mork:value [ a mork:ProductExpression ; mork:operand [ mork:dataRef "saas:hasMonthlyPrice" ] , [ mork:dataRef "saas:hasBillingPeriodsPerYear" ] ] .
```

Compiled, one query:

```sparql
BASE <https://example.org/out/>
CONSTRUCT { ?f1 saas:annualRecurringRevenue ?value4 . }
WHERE {
  ?f1 rdf:type saas:Subscription .
  ?f1 saas:hasMonthlyPrice ?v2 .
  ?f1 saas:hasBillingPeriodsPerYear ?v3 .
  BIND (xsd:decimal(?v2 * ?v3) AS ?value4)
}
```

As `mork_rdf` writes it (SVA-S2f, built 2026-11-24), the prefixed names above stand for the full IRIs it writes, and it casts the product to the expression's result datatype. Beside it come one check for each operand the expression reads, naming a carrier that lacks it, and one naming a carrier whose expression is undefined, as a quotient by zero is.

### 2.2 Graph construction, the case and where it stops (SVA-S2g, 2026-11-24)

A graph construction projection writes new structure that no single read path reaches, which is the one thing Surface's README says of it. In its simplest generic form it reads a few properties of each instance of a carrier and writes a new node of another class, linked from the instance, carrying those values. For example, as first written and since replaced, each `src:Order` with `src:buyerName` and `src:buyerEmail` gives one `tgt:Party` with `tgt:name` and `tgt:email`, reached from the order by `tgt:placedBy`.

What `mork_rdf` compiles today fits the output. A root datum iterating `src:Order`, with a contextual datum beneath it that mints and types the party and is glued to the order by an R-Box match, and an assertion beneath that for each value, is its existing datum, contextual datum and assertion cases (section 5.1 of its README), with no new case. Nothing in the contract states that structure, and the contract cannot state it with what Surface has:

| What the output needs | What the contract has |
|---|---|
| the class of the constructed node | `srf:bindsCarrier`, which says the class a role's evidence is drawn from, not a class written |
| the link from the instance to the constructed node | the result-target binding's property, if it is taken to mean the link |
| a property for each constructed value | a second result-target binding, which `srf:P3` forbids |
| which evidence goes on which constructed property | nothing, since an evidence binding names the property it reads only |
| the identity of the constructed node | nothing. `mork_rdf`'s default is a hash of the source node's IRI, which is a rule, not a statement of the contract |

So the case paused until SVA-Q31 to SVA-Q35 in section 3 were answered, and the contract, the scheme and the query as built follow the example below.

**The example, as answered on 2026-11-24.** A party minted from a buyer's email spells a personal value into an identifier, which the identity patterns warn against, so the example is an order giving a supplier keyed by a supplier code, with the supplier's name as candidate evidence. Placeholder names, for SVA-S2g to ground:

```turtle
ex:os-code a srf:ProjectionRoleBinding ; srf:roleKind srf:RequiredEvidenceRole ; srf:bindsProperty src:supplierCode .
ex:os-name a srf:ProjectionRoleBinding ; srf:roleKind srf:CandidateEvidenceRole ; srf:bindsProperty src:supplierName .
ex:os-link a srf:ProjectionRoleBinding ; srf:roleKind srf:ResultTargetRole ; srf:bindsProperty tgt:suppliedBy ;
    srf:constructedAs ex:os-node .
ex:os-node a srf:ConstructedNode ; srf:constructedClass tgt:Supplier ;
    srf:nodeIdentity srf:ByKey ; srf:keyBinding ex:os-code ;
    srf:writes [ srf:writesProperty tgt:code ; srf:fromBinding ex:os-code ] ,
               [ srf:writesProperty tgt:name ; srf:fromBinding ex:os-name ] .
```

What a key costs, by arithmetic on 100,000 orders with 20,000 distinct codes and two written values: 20,000 nodes and 160,000 triples where a node for each order gives 100,000 and 400,000, and withdrawing one order removes one link and reads the node's other links, about four, where a node for each order removes four triples and reads nothing.

**As built (SVA-S2g, 2026-11-24).** The example is `ontology/surface/examples/order-supplier-construction-projection.ttl`, with the placeholder names kept and the order's own classes and properties in one namespace. A contract states the construction on the result-target binding with `srf:constructedAs`, and the constructed node is a `srf:ConstructedNode` with `srf:constructedClass`, `srf:nodeIdentity` (`srf:PerInstance` or `srf:ByKey`), a `srf:keyBinding` for each part of a key, and a `srf:writes` for each value, a `srf:WrittenValue` that gives `srf:writesProperty` and `srf:fromBinding`. Laws `srf:P10` to `srf:P13` and a shape for each part check it, and `srf:P1` says that a node typed with a class an authored vocabulary declares reaches the authored signature.

The contract, as in the example:

```turtle
ex:os-link a srf:ProjectionRoleBinding ; srf:roleKind srf:ResultTargetRole ; srf:bindsProperty ex:suppliedBy ;
    srf:constructedAs ex:os-node .
ex:os-node a srf:ConstructedNode ; srf:constructedClass ex:Supplier ;
    srf:nodeIdentity srf:ByKey ; srf:keyBinding ex:os-code ;
    srf:writes [ srf:writesProperty ex:code ; srf:fromBinding ex:os-code ] ,
               [ srf:writesProperty ex:name ; srf:fromBinding ex:os-name ] .
```

Lowered, abridged, with each node's name shortened to its place in the scheme. The guard names every required-evidence binding, the candidate name is not in it, and the identity is the contract's key, the class and the key's values:

```turtle
exec:scheme_root a mork:DataMapping, mork:Datum ; mork:mappingScheme exec:scheme ; mork:mappingFor exec:scheme_carrier ;
    mork:identityRule mork:SourceNodeIdentity ; mork:compositeNarrowerMapping exec:scheme_node .
exec:scheme_node a mork:DataMapping ; mork:mappingScheme exec:scheme ; mork:broaderApplicative exec:scheme_root ;
    mork:exactTBoxMatch ex:Supplier ; mork:inverseRBoxMatch ex:suppliedBy ;
    mork:appliesWhen exec:scheme_guard ; mork:identityTemplateMapping exec:scheme_identity_0 ;
    mork:compositeNarrowerMapping exec:scheme_write_0 , exec:scheme_write_1 .
exec:scheme_guard a sh:NodeShape ; sh:property exec:scheme_guard_0 .
exec:scheme_guard_0 sh:path ex:supplierCode ; sh:minCount 1 .
exec:scheme_identity_0 a mork:ConcatExpression ; mork:concatLeft exec:scheme_identity_part_0 ; mork:concatRight exec:scheme_identity_part_1 .
exec:scheme_identity_part_0 a mork:LiteralExpression ; mork:dataInline "order-supplier/Supplier/" .
exec:scheme_identity_part_1 a mork:RefExpression ; mork:dataRef "<https://example.org/lattice/surface/order-supplier#supplierCode>" .
exec:scheme_write_0 a mork:DataMapping ; mork:exactRBoxMatch ex:code ; mork:dataRef "<.../supplierCode>" .
exec:scheme_write_1 a mork:DataMapping ; mork:exactRBoxMatch ex:name ; mork:dataRef "<.../supplierName>" .
```

Compiled, the query that writes the node and the link, with the prefixed names standing for the full IRIs `mork_rdf` writes. The query for each value repeats the guard and the identity, whole, and adds the value's own pattern:

```sparql
BASE <https://example.org/lattice/surface/order-supplier/out/>
CONSTRUCT { ?t3 rdf:type ex:Supplier . ?f1 ex:suppliedBy ?t3 . }
WHERE {
  ?f1 rdf:type ex:Order .
  FILTER (EXISTS { ?f1 ex:supplierCode ?any2 . })
  ?f1 ex:supplierCode ?v4 .
  BIND (IRI(CONCAT("order-supplier/Supplier/", ENCODE_FOR_URI(STR(?v4)))) AS ?t3)
}
```

**The guard held.** The first thing the case had to show was that a guard sits right on a contextual node beneath a source-node root, so an instance contributes whole or not at all (SVA-Q33). It does, on Oxigraph and on rdflib. An order that holds the key and lacks another required value writes no link, no type and no value of its own, even where another order has made the node, and without the guard the same order links to the node and nothing is reported. `mork_rdf`'s existing cases report neither that exclusion nor a keyed node whose instances disagree, so it gains two checks and no mapping kind. `InstanceExcluded` names each excluded instance and the required value it lacks, and `ValueDisagrees` names a keyed node and each value its instances give a property. A keyed construction also compiles with a `MappingReview` warning, which is where SVA-Q35 (a) is recorded as a finding in this slice, and a construction for each instance compiles with none. Whether the studio's review requirement, which today reads only the projection kind, acts on it is for the slice that compiles projections in the studio.

What the example gives, over three orders where two name one supplier, is two supplier nodes and three links, each node typed and carrying its code, and the name on the first.

## 3. Questions

**SVA-Q24. Where is a derivation's operation stated?** (a) In the contract, an expression on the result-target binding over the evidence bindings. (b) In MORK alone, added by hand to the lowered mapping. (c) As an approved template the backend policy names, a reviewed query fragment with its parameters bound by the roles. (b) breaks ADR-A18's deterministic lowering and leaves the contract without its meaning. (c) uses `srf:approvedTemplate`, which exists, but holds query text where the contract states meaning. Leaning (a). **Answered 2026-11-23, (a).**

**SVA-Q25. What operations does the expression vocabulary hold?** (a) The four arithmetic operations and a typed literal. (b) As (a), with rounding to a stated scale and a conditional choice of two values. (c) A general expression language. Leaning (a), with (b) when a contract needs it, since every operation added is one the laws and every backend must carry. **Answered 2026-11-23, (b).**

**SVA-Q26. How does MORK carry a value expression?** (a) New numeric expression classes beside the string ones, typed, compiled to SPARQL arithmetic. (b) The string expressions widened to any value. (a) keeps the string algebra a monoid and lets a typed operand be checked. Leaning (a). **Answered 2026-11-23, (a).**

**SVA-Q27. How does a derived value land on the carrier?** (a) A new identity rule, the source node itself, with no datum minted or typed. (b) A datum minted per carrier and linked to it. (b) changes what the contract states, a property of the carrier. Leaning (a). **Answered 2026-11-23, (a).**

**SVA-Q28. Which projection kinds does this unit build?** (a) Derivation, with ARR as the reference corpus ADR-A41 names. (b) Derivation and graph construction. (c) All four. A join needs a mapping review and an expansion an engineering one (ADR-A41), and each is a compiled case of its own. The maintainer asked that every behaviour the sketch names is built in this unit, and section 9 of the unit's sketch names projections without kinds. Leaning (a) now and the others as slices once (a) has run, each with its own example. **Answered 2026-11-23, (c).**

**SVA-Q29. Where does a step's projection part run?** (a) As a second run the surface pane sends, answered by the Python worker with `mork_rdf`'s driver, beside the surface step the Java run worker answers. (b) In the Java run worker, as plain CONSTRUCT queries on Jena, where a compiled projection needs none of the driver's rules. (c) The whole surface step in the Python worker. (a) keeps one worker to a run and the run protocol unchanged, and each part names its engine. (b) is a second runtime for MORK's compiled form, which the addendum of 2026-11-20 decided against. (c) moves the writer's maintenance, which is Java, out of the worker that runs it. Leaning (a). **Answered 2026-11-23, (a).**

**SVA-Q30. Which decisions change?** Leaning: an addendum to ADR-A18 (a derivation's expression is carried across by the lowering, and a lowered projection is a scheme with a source-node root), an addendum to ADR-A23 (`mork_rdf` compiles derivation projections), and minor versions of the Surface and MORK modules for their new terms, each released by `mise run version:bump` at the merge. **Answered 2026-11-23, as leaned.**

**SVA-Q31. How does a graph construction contract state what it writes?** (a) With the existing role kinds, taking the result-target binding as the link, `srf:bindsCarrier` on it as the constructed class, and allowing several result-target bindings for this kind, each a constructed property, paired with an evidence binding. This relaxes `srf:P3` and gives roles a second meaning. (b) With a new role kind for the constructed node and a new property pairing an evidence binding with the property it is written as. (c) With a construction statement on the contract, as `srf:derivedAs` is for a derivation (SVA-Q24 (a)), a small closed vocabulary: a constructed node with its class, its identity and its properties, each a role binding written as a stated property, and the link from the instance. Leaning (c), since the contract states and the compiler executes, and (a) and (b) leave roles meaning different things by kind. It adds Surface terms, laws and shapes. **Answered 2026-11-24, (c), stated on the result-target binding and not on the contract.** The result-target binding binds the link from the instance and states `srf:constructedAs` a constructed node, so its result is a node where a derivation's is a value, a role keeps one meaning, and P2 and P3 stand. The constructed node states its class, its identity and each property it writes from an evidence binding of the same contract. Only (c) grows to a constructed node that points at another, which the ledger's account definitions derived from an instrument's meaning will need. The link from the instance is mandatory, and under a key it records which instances support a node.

**SVA-Q32. What is the identity of a constructed node?** (a) The contract states it as a key of one or more evidence bindings, so two instances with the same key give one node, which MORK's template identity compiles. (b) The hash of the source node's IRI, one constructed node per instance, which `mork_rdf` does by default and the contract leaves unstated. (c) The minting policy of the Surface profile (`LocalNameFromValue`, `DigestLocalName`), versioned with the profile. A key makes the projection merge instances, which is a different meaning from (b), and a join or an aggregation if the key spans carriers. Leaning (a), with (b) as the case where the contract states that each instance gets its own node, so the choice is never implicit. **Answered 2026-11-24, as two questions.** What makes two constructed nodes the same is meaning, so the contract states a closed choice, a node for each instance or one for each value of a key of required-evidence bindings, never left implicit. How the identifier is spelled is naming, kept as the compiler does it: readable from the key, a hash of the instance's identifier otherwise, with a digest of a key left until a contract needs one, and the contract's key in the identifier, so two contracts never reach one node. A key brings a run-time check that names a node whose instances disagree on a value, a law that a key binding is required evidence, a withdrawal that is no longer local (free in the studio, which recomputes the world, and a read for a production maintainer), and a boundary stated with the feature: a natural key in an identifier is spelled into it, so a key that may be personal or may change is no key, which Surface cannot check.

**SVA-Q33. What does a constructed node do with missing evidence?** (a) A node is written only where every required-evidence binding has a value, and candidate-evidence bindings write what they find, as a derivation writes nothing for a carrier missing an operand, with a check naming the instance. (b) A node is written with whatever values exist. Leaning (a), since it gives the two evidence role kinds a meaning that holds across kinds. **Answered 2026-11-24, (a).** An instance contributes whole or not at all: one that has the key but lacks a required value writes no link and is reported, even where another instance has made the node. `mork_rdf` writes each value with its own query, which is (b), so the compiled case guards the frame every query beneath inherits, and the first thing the case shows is that a guard sits right on a contextual node beneath a source-node root.

**SVA-Q34. Which decisions change?** Leaning, as for SVA-Q30: an addendum to ADR-A18 that replaces item 4 for this kind (a graph construction lowers into a scheme whose constructed node is a contextual datum), an addendum to ADR-A23, new laws in the Surface register beside P6 to P9, and minor versions of the Surface and, if (c) of SVA-Q31 needs a term, the MORK module, each released by `mise run version:bump` at the merge. The amendment to ADR-A18 is the maintainer's to decide. **Answered 2026-11-24, as leaned, with the laws named.** One construction on the result-target binding of a graph construction and no other kind. A constructed node states a class, an identity and at least one written value. Each written value names an evidence binding of the same contract. A key binding is required evidence. A run-time check for a keyed node's disagreement. A sentence on how P1, signature scope, reads for a node typed with an authored class. And an addendum to ADR-A18 and ADR-A23 for this kind.

**SVA-Q35. Does a keyed construction take ADR-A41's mapping review?** ADR-A41 asks a mapping review of a join and names none for graph construction. A construction by key merges instances, as a join relates them. (a) A keyed construction takes the mapping review, recorded as a finding as a join's is, and a construction for each instance takes none. (b) Neither takes one. (c) Both take one. Leaning (a), since the merge is where a reviewer's judgement is needed. **Answered 2026-11-24, (a).** A keyed construction takes ADR-A41's mapping review, recorded as a finding the way a join's will be, and a construction for each instance takes none.

## 4. Slices

Every projection kind is built in this unit (SVA-Q28 (c)). A slice for graph construction, join or expansion starts by adding its case to this sketch, with the contract it lowers, the scheme and the query, and pauses for the maintainer where the case raises a question the answers above do not settle.

| Slice | What | Done when |
|---|---|---|
| SVA-S2e | the expression vocabulary in Surface and MORK (the arithmetic, a typed literal, rounding and a choice on a comparison), with shapes and the laws' checks, the ARR example stating its operation, the lowering carrying a derivation into a scheme with a source-node root, and the addenda to ADR-A18 and ADR-A23 drafted | the ARR contract lowers to a scheme MORK's shapes accept, deterministically |
| SVA-S2f | `mork_rdf` compiles a derivation: value expressions, the source-node identity, and the check for a missing operand | the ARR scheme compiles to the query of section 2.1, and runs to the expected values over a sample |
| SVA-S2g | graph construction projections, from contract to compiled scheme, with an example | an example's projection compiles and runs to its expected graph |
| SVA-S2h | join projections, with the mapping review ADR-A41 asks for recorded as a finding, and an example | an example's join compiles and runs to its expected rows |
| SVA-S2i | expansion projections, with the engineering review recorded as a finding, and an example | an example's expansion compiles and runs to its expected rows |
| SVA-S2c | the surface compile job lowers and compiles projections, the facility sample gains them, and a step's projection part runs as a second run of the Python worker (SVA-Q29) | a step over the sample shows each projection's rows, equal to its compiled scheme run over the world after |

## 5. Placement

T0. Surface's projections, MORK and `mork_rdf` are open substrate, and the ARR example is generic.
