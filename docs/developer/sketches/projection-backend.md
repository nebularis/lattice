<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Sketch: a projection backend, from a Surface projection contract to queries a step runs

**Unit:** `studio-visual-authoring` (SVA), slice SVA-S2d, raised on 2026-11-23 when the maintainer chose that projections are built in this unit, design first
**Status:** sketch. SVA-Q24 to SVA-Q56 answered by the maintainer between 2026-11-23 and 2026-11-25. Derivations, graph constructions, joins, expansions and a node for each member are built
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

**The studio compiles and runs it.** The surface compile job lowers each projection and compiles its scheme with `mork_rdf`, beside the promotions' maintenance, and records the engineering review ADR-A41 asks of a derivation as a finding the author sees, `DerivationReview` (named so on 2026-11-25, with `ExpansionReview` for an expansion and `MappingReview` for a join and a keyed construction). A step's projection part runs the compiled scheme over the world before and after with `mork_rdf`'s driver, which is the Python worker's under ADR-A154's addendum.

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

As `mork_rdf` writes it (SVA-S2f, built 2026-11-24), the prefixed names above stand for the full IRIs it writes, and it casts the product to the expression's result datatype. Beside it come one check for each operand the expression reads, naming a carrier that lacks it, and one naming a carrier whose expression is undefined, as a quotient by zero is. It also records `DerivationReview`, a warning on the assertion that names the property it writes, which is where ADR-A41's engineering review of a derivation is recorded as a finding (added 2026-11-25).

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

### 2.3 Join, the case and where it stops (SVA-S2h, 2026-11-24)

A join projection combines evidence from more than one carrier, which is the one thing Surface's README says of it. In its simplest generic form each instance of a carrier names, by a value, an instance of a second carrier, and the projection relates the two. For example, each `ex:Order` with an `ex:customerCode` is related to the `ex:Customer` whose `ex:code` is that value.

What exists, read on 2026-11-24:

| What the join needs | What the contract has |
|---|---|
| the second carrier | `srf:bindsCarrier` on an evidence binding. The lowering reads it today as a dependency on another contract whose own carrier is that class, which is a different meaning from naming the class a join reaches |
| the property of each carrier that relates them, and that the relation is equality | nothing. An evidence binding names the property it reads, and no term pairs one on the contract's carrier with one on the second carrier |
| what is written | the result-target binding's property, which a derivation reads as the value's property and a construction as the link |
| what an instance with no match writes, and what one with several matches writes | nothing. P2 asks a join for at least one evidence binding and says no more |
| the review | ADR-A41, which asks a join for a mapping review and, as its addendum says, records it as a finding |

What `mork_rdf` compiles today fits part of the output. A root datum iterating the first carrier, a source-node identity (SVA-S2e), a guard on required evidence and the reports of an excluded instance and an ambiguous identity (SVA-S2g) all carry over. The mapping review finding is SVA-S2g's `MappingReview`, raised for a join where it is raised for a keyed construction. A lookup (Case 6, the `mork_rdf` README section 7.3) is already a join of one kind. It writes, on the instance, the R-Box property with the reference node whose stated property equals the source value as its value, compares by cast, reports `LookupUnresolved` where none matches and `LookupAmbiguous` where several do, and asserts each. What a lookup does not do is read the second carrier from the source graph. It reads only the reference graph, so source data cannot add codes to a lookup (README section 13). A datum that stands for an instance of a second class of the world, reached from the first instance by equality of two values and not by a path, had no case, since a source-node identity takes the node a datum iterates and a contextual datum is glued to its parent by a property and mints its own node. The sketch left open whether the join is a lookup over reference data, a new term, or a lookup widened (SVA-Q40), and the maintainer chose a new term and left the lookup as it is.

So the case paused until SVA-Q36 to SVA-Q41 in section 3 were answered, and the contract, the scheme and the query as built follow the example below.

**The example, as answered on 2026-11-24.** An order names its customer by a code, and a customer has a code and a region. No personal value is spelled into an identifier, since a code is a code a customer is known by and a join links existing nodes and mints none. Each order is linked to the customer whose code it names. The contract states what relates the two carriers and that the result is a link, and a code names at most one customer unless it says otherwise, so an order with no customer or with a code that several customers hold writes no link for that code and is reported. Where the placeholders of the first draft stood, the terms are `srf:JoinStatement` for the statement, `srf:joinsOn` with `srf:joinLeft` and `srf:joinRight` for each pair of bindings that must be equal (several pairs for a composite key), `srf:joinMatches` with the individuals `srf:AtMostOne` and `srf:AnyNumber`, and `srf:joinLinks`.

What the three answers about missing and repeated matches come to, for a join that writes only a link:

| The instance | On required evidence | On candidate evidence |
|---|---|---|
| lacks a value of its own carrier the join compares | excluded, writes nothing, reported by `InstanceExcluded` with the value | writes no link and says nothing |
| holds the values and no instance of the second carrier has them | writes no link and is reported by `JoinUnmatched` as a warning, with the value | writes no link and is reported by `JoinUnmatched` as information, with the value |
| holds a value that several instances have | under at most one writes no link for that value and is reported by `JoinAmbiguous` with each match, under any number writes a link for each | the same |

The choice for candidate evidence is where a join differs from a keyed construction. A join writes the link and nothing else, so what a candidate-evidence binding finds is the link. An instance that holds the values and finds none has nothing to write, and it is told to the reviewer as information and not as a warning. An instance that lacks the values stays silent. The first answer of the maintainer was silence in both cases, and it was changed on 2026-11-24 to this.

**As built (SVA-S2h, 2026-11-24).** The example is `ontology/surface/examples/order-customer-join-projection.ttl`. A contract states the relation on the result-target binding with `srf:joinedAs`. The statement is a `srf:JoinStatement` with a `srf:joinsOn` for each pair, and may state `srf:joinMatches` and `srf:joinLinks`. Each pair is a `srf:joinLeft` binding that reads the contract's own carrier and a `srf:joinRight` binding that reads a second carrier, which it names with `srf:bindsCarrier`. Laws `srf:P14` to `srf:P17` and a shape for each part check it, and `srf:P1` says that a link an authored vocabulary declares reaches the authored signature.

The two counts are separate rules, each a closed choice. `srf:joinMatches` says how many instances of the second carrier one value may name, `srf:AtMostOne` or `srf:AnyNumber`, counted for each value, so an order with two codes that each name one customer has two links. A statement that omits it means `srf:AtMostOne`, which the term's definition says. `srf:joinLinks` says how many links one instance may have, and a statement that omits it means `srf:AnyNumber`. Under `srf:AtMostOne` an instance whose values together find several writes no link and is reported with each match. The lowering writes both into MORK whether the contract states them or not, so the compiled form leaves neither implicit.

The contract, as in the example:

```turtle
ex:oc-code a srf:ProjectionRoleBinding ; srf:roleKind srf:RequiredEvidenceRole ; srf:bindsProperty ex:customerCode .
ex:oc-match a srf:ProjectionRoleBinding ; srf:roleKind srf:RequiredEvidenceRole ; srf:bindsCarrier ex:Customer ; srf:bindsProperty ex:code .
ex:oc-link a srf:ProjectionRoleBinding ; srf:roleKind srf:ResultTargetRole ; srf:bindsProperty ex:placedFor ; srf:joinedAs ex:oc-join .
ex:oc-join a srf:JoinStatement ;
    srf:joinsOn [ srf:joinLeft ex:oc-code ; srf:joinRight ex:oc-match ] ;
    srf:joinMatches srf:AtMostOne .
```

Lowered, abridged, with each node's name shortened to its place in the scheme. The root is a source-node datum over the order, and the datum beneath it iterates the customer class through its own concept, takes the node it finds as its identity, and is glued to the order by the inverse match. The guard holds the order's required evidence and not the customer's, and is tested on the order. MORK gains `mork:JoinCondition`, `mork:joinsOn`, `mork:parentRef`, `mork:ownRef`, `mork:joinCardinality`, `mork:linkCardinality`, `mork:reportsUnmatched`, `mork:unmatchedSeverity` and two individuals, and each condition reads `mork:lookupComparison` and `mork:lookupDatatype` as a lookup does:

```turtle
exec:scheme_root a mork:DataMapping, mork:Datum ; mork:mappingScheme exec:scheme ; mork:mappingFor exec:scheme_carrier ;
    mork:identityRule mork:SourceNodeIdentity ; mork:compositeNarrowerMapping exec:scheme_node .
exec:scheme_node a mork:DataMapping, mork:Datum ; mork:mappingScheme exec:scheme ; mork:broaderApplicative exec:scheme_root ;
    mork:mappingFor exec:scheme_second ; mork:identityRule mork:SourceNodeIdentity ; mork:inverseRBoxMatch ex:placedFor ;
    mork:appliesWhen exec:scheme_guard ; mork:joinsOn exec:scheme_condition_0 ;
    mork:joinCardinality mork:AtMostOneMatch ; mork:linkCardinality mork:AnyNumberOfMatches ;
    mork:reportsUnmatched true ; mork:unmatchedSeverity mork:WarningFinding .
exec:scheme_second a mork:DataConcept ; mork:representedAs ex:Customer .
exec:scheme_condition_0 a mork:JoinCondition ; mork:parentRef "<.../customerCode>" ; mork:ownRef "<.../code>" ;
    mork:lookupComparison mork:TermComparison .
exec:scheme_guard a sh:NodeShape ; sh:property exec:scheme_guard_0 .
exec:scheme_guard_0 sh:path ex:customerCode ; sh:minCount 1 .
```

Compiled, the query that writes the link, with the prefixed names standing for the full IRIs `mork_rdf` writes. The customer is a variable beside the order, and the two codes meet in one variable, so an engine can serve the join from an index. The subquery counts the matches of each code again, naming the customer it counts with a variable of its own and sharing only the order and the code it projects, since a variable the outer query has bound and the subquery does not project is bound inside a subquery on rdflib too (TSD-79), and keeps the codes with exactly one:

```sparql
BASE <https://example.org/lattice/surface/order-customer/out/>
CONSTRUCT { ?f1 ex:placedFor ?f2 . }
WHERE {
  ?f1 rdf:type ex:Order .
  ?f1 ex:customerCode ?v3 .
  FILTER (EXISTS { ?f1 ex:customerCode ?any4 . })
  ?f2 rdf:type ex:Customer .
  ?f2 ex:code ?v3 .
  { SELECT ?f1 ?v3 WHERE { ?f1 ex:customerCode ?v3 . FILTER (EXISTS { ?f1 ex:customerCode ?any6 . }) ?f5 rdf:type ex:Customer . ?f5 ex:code ?v3 . } GROUP BY ?f1 ?v3 HAVING (COUNT(DISTINCT ?f5) = 1) }
}
```

Under `srf:joinLinks srf:AtMostOne` a second subquery, grouped by the order alone, keeps the orders whose codes together find exactly one customer.

The checks are queries of their own and are not shown. `InstanceExcluded` names each order the guard excludes with the value it lacks. `JoinUnmatched` names each order that holds the code and finds no customer, with the code, as a warning on required evidence and as information on candidate evidence, and is emitted only where the datum says it reports. `JoinAmbiguous` names each customer of a code that finds several, and is emitted only under at most one. `JoinManyMatches` names each customer of an order whose codes together find several, and is emitted only under at most one link. The datum also carries a `MappingReview` warning, which is where ADR-A41's review of a join is recorded as a finding in this slice. The compiler raises it for every join, whatever its evidence and count, and the studio's review requirement, which today reads only the projection kind, does not yet act on it (the same open point as for a keyed construction).

**Choices the answers did not settle.** Each pair compares its two values as a lookup compares them. The lowering states a term comparison on the pair's condition where its right binding states no datatype, and a cast of the order's value to the datatype where it states one, which the contract's `srf:bindsDatatype` gives, so the comparison is never SPARQL's value equality (TSD-64). A term or cast comparison shares one variable between the two patterns and a lexical one is a filter, which is the cost the lookup already documents. Each pair states its own, so a key may compare a string pair and an integer pair, and a pair may cast one side, as a string `"42"` the order holds against the integer `42` the customer holds. A left binding that states a datatype has a right one to cast it to. A guard on the datum is tested on the order and not on the customer, which is the one place a guard's focus is the parent's. It holds the order's required evidence and never the customer's beyond the key, so a required value of the second carrier other than the key goes unchecked, and nothing is built for it.

A condition that states no comparison means a term comparison. The datum states neither `mork:lookupComparison` nor `mork:lookupDatatype`, a shape refuses a datum that does and the compiler refuses it by name (`JoinDatumComparison`), so nothing is inherited from the datum or from a lookup's default (decided by the maintainer on 2026-11-24, after the first build read the datum's as a fallback).

What the example gives, over three orders where two name one customer and one names a code no customer holds, is two links, and the third order reported with its code. A code that two customers hold, under at most one, gives no link for that code and a report naming each customer. Under any number it gives a link for each. An order with two codes that each name one customer has two links, and under at most one link it has none and the report names both customers.

### 2.4 Expansion, the case and where it stops (SVA-S2i, 2026-11-25)

An expansion projection restates one relation as several, which is the one thing Surface's README says of it (`srf:ExpansionProjection`, "mapping intent that restates one relation as several"). ADR-A41 asks it an engineering review, as it asks a derivation, and names no other rule. That sentence admitted three readings, and the maintainer chose two of them on 2026-11-24 and 2026-11-25 (SVA-Q42, SVA-Q43, SVA-Q49). An expansion restates a collection, an RDF list or a repeated property, as one statement for each member, or a hierarchy, a node reached by a transitive relation, as one statement for each ancestor. A SHACL property path from the instance selects the members in both, and a subgraph obtained by SHACL evaluation is not a source.

What existed, read on 2026-11-24:

| What the expansion needs | What the contract had |
|---|---|
| what is expanded and what it is expanded into | nothing. The term had a one-line comment and no law, no shape and no example, and the lowering gave it the bare mapping, which ADR-A18's addendum of 2026-11-24 left for an expansion alone |
| the written relation or relations | the result-target binding's property, which a derivation reads as the value's property, a construction as the link and a join as the link |
| how many statements one instance may give | nothing, and this is what the engineering review of ADR-A41 weighs |
| what an empty or missing source writes | nothing, as SVA-Q33 and SVA-Q38 settle for a missing required value and a missing match, and an empty collection had no answer there |

What `mork_rdf` compiles fits the output with no mapping kind of its own. A root datum over the carrier with a source-node identity and an assertion beneath it that writes on that node is a case it already compiled, and a path that reaches the members of an RDF list, `src:items/rdf:rest*/rdf:first`, is a reference an assertion reads (the `mork_rdf` README, section 4.2), so one reference gives one value for each member and the CONSTRUCT writes a set. What it did not do was report an empty source, so it gains one check, and record the engineering review, so it gains one finding.

**The example, as answered.** A bundle holds a list of items, and each member of the list is restated as a `contains` link from the bundle, so the one relation, the list, becomes several, one statement for each member. No value spelled into an identifier is involved, since each item is an existing node and the expansion mints none. A second example, of a transitive closure, restates each category's ancestors, reached by a broader relation, as a `hasAncestor` statement on the category. The terms were placeholders in the first draft, and `exists` found none of them, so they stand as `srf:ExpansionStatement`, `srf:expandedAs`, `srf:expandsFrom`, `srf:expansionSource` with the individuals `srf:ListMembers` and `srf:TransitiveClosure`, and `srf:membersPath` for a path the contract states itself.

**As built (SVA-S2i, 2026-11-25).** The examples are `ontology/surface/examples/bundle-items-expansion-projection.ttl` and `category-ancestors-expansion-projection.ttl`. A contract states the expansion on the result-target binding with `srf:expandedAs`. The statement is a `srf:ExpansionStatement` that names one `srf:expandsFrom` evidence binding of the contract's own carrier and states its members as exactly one of a named source and a `srf:membersPath`. A path is a SHACL property path of the forms `sh:path` takes, a property, a sequence, an alternative, an inverse, zero or more and one or more, and must read the property of the binding it expands from and never the property the result-target binding writes. Laws `srf:P18` to `srf:P21` and a shape for each part check it, and `srf:P1` says that an expansion reads its scope from the property it writes. The lowering writes each named source as its path and keeps the path a contract states.

The contract, as in the first example:

```turtle
ex:bd-items a srf:ProjectionRoleBinding ; srf:roleKind srf:RequiredEvidenceRole ; srf:bindsProperty ex:items .
ex:bd-contains a srf:ProjectionRoleBinding ; srf:roleKind srf:ResultTargetRole ; srf:bindsProperty ex:contains ;
    srf:expandedAs ex:bd-expansion .
ex:bd-expansion a srf:ExpansionStatement ; srf:expandsFrom ex:bd-items ; srf:expansionSource srf:ListMembers .
```

The same members stated as a path, which lowers to the same scheme, and the closure of the second example:

```turtle
ex:bd-expansion a srf:ExpansionStatement ; srf:expandsFrom ex:bd-items ;
    srf:membersPath ( ex:items [ sh:zeroOrMorePath rdf:rest ] rdf:first ) .
ex:ca-expansion a srf:ExpansionStatement ; srf:expandsFrom ex:ca-broader ; srf:expansionSource srf:TransitiveClosure .
```

Lowered, abridged, with each node's name shortened to its place in the scheme. The root is a source-node datum over the bundle, and one assertion beneath it writes the property on the bundle with the path as its reference. The guard names every required-evidence binding of the bundle, so a bundle without a list contributes nothing, and an expansion on candidate evidence has none. No datum is minted and nothing is typed:

```turtle
exec:scheme_root a mork:DataMapping, mork:Datum ; mork:mappingScheme exec:scheme ; mork:mappingFor exec:scheme_carrier ;
    mork:identityRule mork:SourceNodeIdentity ; mork:compositeNarrowerMapping exec:scheme_assertion .
exec:scheme_assertion a mork:DataMapping ; mork:mappingScheme exec:scheme ; mork:exactRBoxMatch ex:contains ;
    mork:dataRef "<.../items>/<rdf:rest>*/<rdf:first>" ; mork:appliesWhen exec:scheme_guard .
exec:scheme_guard a sh:NodeShape ; sh:property exec:scheme_guard_0 .
exec:scheme_guard_0 sh:path ex:items ; sh:minCount 1 .
```

Compiled, the query that writes each member, with the prefixed names standing for the full IRIs `mork_rdf` writes. The closure compiles to one pattern, `?f1 ex:broader+ ?v2`, with no guard on candidate evidence:

```sparql
BASE <https://example.org/lattice/surface/bundle-items/out/>
CONSTRUCT { ?f1 ex:contains ?v3 . }
WHERE {
  ?f1 rdf:type ex:Bundle .
  FILTER (EXISTS { ?f1 ex:items ?any2 . })
  ?f1 ex:items/(rdf:rest*)/rdf:first ?v3 .
}
```

The checks are queries of their own and are not shown. `InstanceExcluded` names each bundle the guard excludes with the required value it lacks, as for a construction and a join. `CollectionEmpty` is new, emitted for an assertion that writes on the source node with a path, and names each bundle the guard admits that holds the property the path starts from and whose path reaches no member, with the path, as information, so an instance that lacks the property is silent. `ClosureCycle` is new as well, emitted where the path walks a closure, and names each node that reaches itself through it, with the closure, as a warning. A list's members walk `rdf:rest*`, so a list that loops back is reported by one of its cells. The compiler also records `ExpansionReview`, a warning on the assertion that names the path and says the number of statements for one node depends on the data, which is where ADR-A41's engineering review of an expansion is recorded as a finding in this slice. `MappingReview` is the merge's finding and an expansion does not carry it. The studio's review requirement reads only the projection kind today and does not yet act on either finding (the same open point as for a keyed construction and a join).

What the first example gives, over four bundles, is a statement for each of the three members of the first, one for the second, nothing for the third, whose list is empty and which is reported as information, and nothing for the fourth, which has no list and is excluded and reported. The second, over a chain of three categories, gives two statements for the narrowest and one for the middle category, and the broadest holds no broader relation, so it is silent. Where a relation loops, such as a first category that is broader than the third, each of the three is reported as a node that reaches itself.

**Choices the answers did not settle, and what the maintainer decided on 2026-11-25.** An expansion on candidate evidence is not guarded. The first build reported a node that lacks the property as an empty collection, where a join on candidate evidence says nothing for a node that lacks the values, and the maintainer changed it to match the join. A node on candidate evidence that lacks the property is silent, and `CollectionEmpty` reports only a node that holds it and reaches no member, such as an empty list. A closure over a relation that has a cycle makes a node its own ancestor, which SPARQL's path semantics allow. The maintainer decided that a run reports it, with `ClosureCycle`, and that a law refuses an expansion that feeds on its own output. `srf:P21` says an expansion's members never read the property its result-target binding writes, and the model check and a shape refuse it. The compiler still raises the review for every assertion that carries a path directly beneath a source-node datum, whatever the path, since it sees no contract, so a hand-written scheme of that shape takes it as well. A members path that is one property reaches the same statements as a plain assertion, and the contract states it as an expansion all the same. A path that reads another property beside the evidence's, such as one that continues through a second relation, is allowed. The compiler cannot tell the property a path starts from by name, so it reads the path's first step, which is an alternative's parts, an inverse's property or a sequence's first part.

### 2.5 A node for each member, the case and where it stops (SVA-S2j, 2026-11-25)

SVA-Q44 answered that an expansion writes a statement on the instance and mints nothing, and that "a node for each member, expansion combined with graph construction, is planned as a slice of its own". In its simplest generic form each instance holds a collection, and each member of it becomes a node of another class, linked from the instance, carrying what the member and the instance give. For example, each `ex:Bundle` holds a list of `ex:items`, and each member of the list becomes one `ex:Line`, linked from the bundle by `ex:hasLine`, writing the member as `ex:ofItem` and the bundle's `ex:bundleCode` as `ex:bundleCode`. No value spelled into an identifier is involved where the member is an existing node and the bundle code is a code and not a personal value.

What the contract had, and what the case needed, as the maintainer's answers of 2026-11-25 (SVA-Q50 to SVA-Q56) settled it:

| What the case needs | What the contract had | As answered |
|---|---|---|
| the members of the collection, and a node for each | an expansion statement (`srf:P18` to `srf:P21`) and a constructed node (`srf:P10` to `srf:P13`), each on the result-target binding, each stated by a kind of its own | both on the one binding, `srf:expandedAs` and `srf:constructedAs`, the contract an expansion, and `srf:P10` and `srf:P18` relaxed (SVA-Q50 (b)) |
| what "for each" means | `srf:PerInstance` and `srf:ByKey` | the contract states it. `srf:PerInstance` is one node for each instance and member and `srf:ByKey` one for each value of the key, and a list that repeats a member gives one node (SVA-Q51 (c)) |
| a key that reads the member | key bindings, required evidence of the instance (`srf:P13`) | the instance's bindings and the member, `srf:keyMember`, the member at most one part and at least one part in all (SVA-Q52 (b)) |
| a value written from the member | `srf:fromBinding`, an evidence binding of the instance | `srf:fromMember` beside it, and a value of the member's own properties is never copied, a join from the node to it models it where it is wanted (SVA-Q53 (a)) |
| the member that is already an IRI | nothing | a closed choice in the identity, a node minted for each member or the member itself the node, `srf:MemberNode` (SVA-Q54 (c)) |
| a member with no stable text | nothing | a property of the members the contract names, `srf:memberName`, spelled in place of the member, and `MemberUnnamed` for a member that lacks it or is a blank node where none is named (SVA-Q55 (a)) |

What `mork_rdf` compiled before fits most of the output. A source-node root over the bundle, a contextual datum beneath it that mints and types the line and is glued to the bundle by an inverse R-Box match, a guard on the instance's required evidence and an assertion beneath the datum for each written value are the cases of sections 2.2 and 2.4. What no case did was take the member as a variable the datum's identity and its assertions share. A reference reads one value for each solution, so an identity and a value that each read the list would pair every member with every other, and the query that writes the node must bind the same member in the identity, the link and the value. That is the one new MORK term, `mork:memberRef`, which binds the member once. The terms that read the member, and the individual that makes it the node, come with it (below).

**As built (SVA-S2j, 2026-11-25).** The example is `ontology/surface/examples/bundle-line-construction-projection.ttl`, keyed by the bundle's code and the member. A contract states the expansion and the construction on the result-target binding, with `srf:expandedAs` and `srf:constructedAs`, and the contract's kind is an expansion. The node states `srf:nodeIdentity` as `srf:PerInstance`, `srf:ByKey` or the new `srf:MemberNode`, `srf:keyMember true` where the member is a part of the key, `srf:memberName` for a stable name, and each written value states `srf:fromMember true` or `srf:fromBinding`. New laws `srf:P22` to `srf:P25` and a shape for each part check it, `srf:P10`, `srf:P11`, `srf:P12` and `srf:P18` are relaxed to say what the pairing allows, and `srf:P1` reads the scope of the class of the node.

The contract, as in the example:

```turtle
ex:bl-code a srf:ProjectionRoleBinding ; srf:roleKind srf:RequiredEvidenceRole ; srf:bindsProperty ex:bundleCode .
ex:bl-items a srf:ProjectionRoleBinding ; srf:roleKind srf:RequiredEvidenceRole ; srf:bindsProperty ex:items .
ex:bl-link a srf:ProjectionRoleBinding ; srf:roleKind srf:ResultTargetRole ; srf:bindsProperty ex:hasLine ;
    srf:expandedAs ex:bl-expansion ; srf:constructedAs ex:bl-node .
ex:bl-expansion a srf:ExpansionStatement ; srf:expandsFrom ex:bl-items ; srf:expansionSource srf:ListMembers .
ex:bl-node a srf:ConstructedNode ; srf:constructedClass ex:Line ;
    srf:nodeIdentity srf:ByKey ; srf:keyBinding ex:bl-code ; srf:keyMember true ;
    srf:writes [ srf:writesProperty ex:ofItem ; srf:fromMember true ] ,
               [ srf:writesProperty ex:bundleCode ; srf:fromBinding ex:bl-code ] .
```

Lowered, abridged, with each node's name shortened to its place in the scheme. The scheme is a graph construction's, with the datum stating the expansion's path as `mork:memberRef`. MORK gains `mork:memberRef`, `mork:MemberExpression`, `mork:dataMember`, `mork:memberName` and the individual `mork:MemberIdentity`. A key reads the member through `mork:MemberExpression`, the last part of its template, a value written from the member is an assertion with `mork:dataMember true`, and the guard names every required-evidence binding:

```turtle
exec:scheme_root a mork:DataMapping, mork:Datum ; mork:mappingScheme exec:scheme ; mork:mappingFor exec:scheme_carrier ;
    mork:identityRule mork:SourceNodeIdentity ; mork:compositeNarrowerMapping exec:scheme_node .
exec:scheme_node a mork:DataMapping ; mork:mappingScheme exec:scheme ; mork:broaderApplicative exec:scheme_root ;
    mork:exactTBoxMatch ex:Line ; mork:inverseRBoxMatch ex:hasLine ;
    mork:memberRef "<.../items>/<rdf:rest>*/<rdf:first>" ;
    mork:appliesWhen exec:scheme_guard ; mork:identityTemplateMapping exec:scheme_identity_0 ;
    mork:compositeNarrowerMapping exec:scheme_write_0 , exec:scheme_write_1 .
exec:scheme_identity_0 a mork:ConcatExpression ; mork:concatLeft exec:scheme_identity_part_0 ; mork:concatRight exec:scheme_identity_1 .
exec:scheme_identity_part_0 a mork:LiteralExpression ; mork:dataInline "bundle-line/Line/" .
exec:scheme_identity_1 a mork:ConcatExpression ; mork:concatLeft exec:scheme_identity_part_1 ; mork:concatRight exec:scheme_identity_2 .
exec:scheme_identity_part_1 a mork:RefExpression ; mork:dataRef "<.../bundleCode>" .
exec:scheme_identity_2 a mork:ConcatExpression ; mork:concatLeft exec:scheme_identity_part_2 ; mork:concatRight exec:scheme_identity_part_3 .
exec:scheme_identity_part_2 a mork:LiteralExpression ; mork:dataInline "/" .
exec:scheme_identity_part_3 a mork:MemberExpression .
exec:scheme_write_0 a mork:DataMapping ; mork:exactRBoxMatch ex:bundleCode ; mork:dataRef "<.../bundleCode>" .
exec:scheme_write_1 a mork:DataMapping ; mork:exactRBoxMatch ex:ofItem ; mork:dataMember true .
```

A node for each instance and member states no template and `mork:conceptName`, and MORK's default is the hash of the instance and then the member. The member as the node states `mork:identityRule mork:MemberIdentity` and no template, name or member name. A stable name is `mork:memberName` on the datum.

Compiled, the query that writes the node and the link, with the prefixed names standing for the full IRIs `mork_rdf` writes. The member is bound once, the pattern after it leaves a blank member out, and the spelling is bound once as well, so the identity reads it. A blank node reaches the query as itself or, in a run, as a skolem IRI, and the filter reads both. The query for each value repeats the guard and the identity, whole, and adds the value's own pattern, and the one for the member writes `?t6 ex:ofItem ?m4`:

```sparql
BASE <https://example.org/lattice/surface/bundle-line/out/>
CONSTRUCT { ?t6 rdf:type ex:Line . ?f1 ex:hasLine ?t6 . }
WHERE {
  ?f1 rdf:type ex:Bundle .
  FILTER (((EXISTS { ?f1 ex:bundleCode ?any2 . })) && ((EXISTS { ?f1 ex:items ?any3 . })))
  ?f1 ex:items/(rdf:rest*)/rdf:first ?m4 .
  FILTER (!(isBlank(?m4) || STRSTARTS(STR(?m4), "urn:mork-rdf:skolem:v1:")))
  BIND (IF(isLiteral(?m4) && DATATYPE(?m4) != xsd:string, CONCAT(STR(?m4), "^^", STR(DATATYPE(?m4))), STR(?m4)) AS ?s5)
  ?f1 ex:bundleCode ?v7 .
  BIND (IRI(CONCAT("bundle-line/Line/", CONCAT(ENCODE_FOR_URI(STR(?v7)), CONCAT("/", ENCODE_FOR_URI(?s5))))) AS ?t6)
}
```

**The checks.** The datum takes `InstanceExcluded` for each bundle the guard excludes, as a construction does, and `CollectionEmpty` and `ClosureCycle` for its path, as an expansion does. `MemberUnnamed` is new. It names each bundle and each member that has no name to spell, a blank node where no `srf:memberName` is stated or a member without the named value, as a warning, and the other members are written. `MemberNotIri` is new as well, for the member as the node, and names each literal or blank member, which is left out. `IdentityAmbiguous` groups by the bundle and the member. `ValueDisagrees` is read for a node whose identity reads the member without the bundle, so two bundles that hold one member and give it different codes are reported.

**The findings.** The datum records `ExpansionReview`, a warning that names the path, since the number of nodes for one bundle depends on the data. It records `MappingReview` where its identity reads the member without the focus node, or the member is the node, since each merges the bundles that share a member. A key of the bundle's code and the member takes both, since the bundles that share the code and the member share the node, and a node for each bundle and member takes the first alone. The studio's review requirement reads only the projection kind today, and does not yet act on either (the same open point as for a keyed construction, a join and an expansion).

**Choices the answers did not settle.** A literal member is spelled with its lexical form and, where its datatype is not `xsd:string`, the datatype after two carets, so the integer 7 and the string "7" are two names and a code stays plain. The answer said "lexical form with its datatype, as a key part does elsewhere", and a key part in `mork_rdf` spells the lexical form alone, so the built rule adds the datatype for a member and for a name where it matters and leaves a string unchanged. A language tag is not spelled. A stable name is spelled in the same way. The five MORK terms are more than the one the answer to SVA-Q56 names. `mork:memberRef` is that one, and the term that reads the member in an identity (`mork:MemberExpression`), the one that writes it (`mork:dataMember`), the property that names it (`mork:memberName`) and the identity that makes it the node (`mork:MemberIdentity`) follow from SVA-Q53 to SVA-Q55. The member as the node takes `MappingReview`, which SVA-Q56 does not say, since it merges the bundles that share a member and writes on a node the source names. A blank node is blank where it is a blank node or a skolem IRI, since the run names a source's blank nodes by the skolem rule, and the skolem prefix is the one `mork_rdf` writes. A member that is a blank node and has a stable name is written as the name's value where a node's value is written from it with `srf:fromMember`, and never copied as a blank node (the maintainer decided on 2026-11-25). A blank member without a stable name stays reported and skipped. A check reports a member without the named value even where the member is a literal, which can hold no property.

**The join that writes a member's property.** A value of the member's own properties is never copied by the construction (SVA-Q53). The test `test_a_join_from_the_constructed_nodes_writes_a_members_own_property_where_it_is_wanted` shows the join SVA-S2h built over the constructed nodes. A contract whose carrier is `ex:Line` joins the line's `ex:ofItem` to the `ex:recordOf` of the `ex:ItemRecord` that describes the item, and writes the link `ex:describedBy`, so a read path from a line reaches the record's `ex:description` and nothing is copied. Run over the constructed lines and the records, it gives a link for each line whose item has a record, and the record's description is reached through it.

What the example gives, over four bundles, is a line for each of the three items of the first bundle, one for the single item of the second, nothing for the third, whose list is empty and which is reported as information, and nothing for the fourth, which has no list and is excluded and reported. The same item in two bundles with different codes gives two lines.

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

**SVA-Q36. What relates the joined instances?** (a) The contract states it, a closed condition on the join statement that pairs an evidence binding on the contract's carrier with one on the second carrier, and the relation is equality of the two values, one pair or several for a composite key. (b) The existing terms alone, with the pairing taken from the order of the evidence bindings or from `srf:bindsCarrier` on one of them. (c) A path already in the graph that reaches the second instance, which is a read path and so a promotion, not a join. (b) leaves the meaning implicit, which SVA-Q32 and SVA-Q33 refused for identity and for missing evidence, and it needs `srf:bindsCarrier` to mean both a dependency on another contract (the lowering reads it so today) and the class a join reaches. (c) needs no join. Leaning (a), equality only, with an operator or a range added when a contract needs one. It adds Surface terms, laws and shapes, among them that both bindings bind a property of the datatype the other states and that the second binding names a carrier other than the contract's own. **Answered 2026-11-24, (a).**

**SVA-Q37. What does a join write?** (a) A link from each instance to the matched instance, and nothing copied, the result-target binding's property being the link as it is for a construction. (b) A value read from the matched instance, written on the instance as a derivation writes its value. (c) Both, the link and the values. (a) writes structure the graph can already be read through, so a value from the matched instance reaches the first by a promotion over the link, and nothing goes stale. (b) copies a value and leaves a stale copy where the second carrier changes, and it needs the second carrier's value stated as evidence. (c) is two meanings in one statement. Leaning (a), with values reached through the link by a read path. A join that must write a value would then be a derivation over joined evidence, which is a later case. **Answered 2026-11-24, (a).**

**SVA-Q38. What does an instance with no match write?** (a) Nothing, and a check names the instance, as SVA-Q33 reads for a missing required value, so a join on required evidence is whole or not at all, which a lookup does today with `LookupUnresolved`, reporting the value and writing nothing. (b) The instance's other values and no link, as a candidate-evidence binding writes what it finds. (c) A link to a minted placeholder node. Leaning (a) for a join on required evidence and (b) for one on candidate evidence, so the two evidence role kinds keep the meaning they have in the other kinds. (c) writes a node that no source states. **Answered 2026-11-24, (a) for a join on required evidence and (b) for one on candidate evidence.**

**SVA-Q39. What does an instance with several matches write?** (a) A link for each match, the contract stating no limit, and a check reports an instance with several for the review, which a lookup does today with `LookupAmbiguous`. (b) The contract states how many instances a value names, at most one or any number, a closed choice as SVA-Q32's identity is. Under at most one an instance with several matches writes no link and is reported by name, with each match. Under any number it writes a link for each. (c) One chosen by a stated order, such as the lowest IRI. (a) leaves the cardinality, which is meaning, to a report after the fact. (c) discards a match, which no source asked for. Leaning (b), so the choice is never implicit, with at most one the default a contract is read as when the join is by a key the second carrier's vocabulary states unique. It adds a closed individual pair and a check, `JoinAmbiguous`, beside `InstanceExcluded`. Whether a contract that states at most one is checked against the second carrier's own declaration, where one exists, is part of the question. **Answered 2026-11-24, (b).**

**SVA-Q40. Where do the second carrier's instances come from, and how does MORK carry the join?** (a) MORK's lookup as it is, the second carrier's instances supplied as reference data in the reference graph. No MORK term, case or check is added, `LookupUnresolved` and `LookupAmbiguous` report none and several, and a link is written for each match. It covers a join to reference data and not a join of two classes of the world, since a lookup is built never to read source data, so that source data cannot add codes (the `mork_rdf` README, section 13). (b) A new MORK term states the join condition on a contextual datum that takes the second class's node from the source graph as its identity, so a mapping states a node reached by equality and the compiler writes the two patterns and the comparison. It adds a MORK term and a compiler case with a shape for each, and widens what source data can reach, which a lookup refuses. (c) The lookup widened, a stated option letting its reference nodes be read from the source graph, which adds a term as (b) does and puts both cases in one mapping kind, with the lookup's checks and its comparison. Leaning (b), since the kind's meaning is evidence from more than one carrier of the world, (a) is the special case already compiled, and (c) changes what a lookup promises. It is the maintainer's to decide, since it adds a mapping case. **Answered 2026-11-24, (b), MORK's lookup left as it is.**

**SVA-Q41. Which decisions change?** Leaning, as for SVA-Q34: an addendum to ADR-A18 that replaces item 4 of the addendum of 2026-11-23 for this kind (a join lowers into a scheme whose second datum is guarded and states the condition), an addendum to ADR-A23 (`mork_rdf` compiles join projections, with `JoinAmbiguous` and the `MappingReview` finding ADR-A41 asks for), new laws in the Surface register beside P10 to P13, and minor versions of the Surface and MORK modules for their new terms, each released by `mise run version:bump` at the merge. ADR-A41 needs no addendum, since it already asks a join for a mapping review and its addendum says how it is recorded. The amendments to ADR-A18 and ADR-A23 are the maintainer's to decide. **Answered 2026-11-24, as leaned.**

**SVA-Q42. What does an expansion expand?** The README's sentence, "restates one relation as several", fits three readings. (a) One relation's value restated under several properties, a fan-out of the same value, such as one `ex:owner` also written as `ex:responsibleParty` and `ex:contact`. It is bounded by the contract, never by the data, and reasoning over `rdfs:subPropertyOf` already does most of it. (b) One relation whose value is a collection, an RDF list or a repeated property, restated as one statement for each member. The number of statements depends on the data, which is why an engineering review is asked and not a mapping one. (c) A hierarchy, a value restated for itself and for each of its ancestors or descendants by a closure path, as a category and its parents. It depends on the data too, and a closure is what a property path already writes. Leaning (b), since it is the one reading that no existing mapping kind covers and the one where ADR-A41's engineering review has something to review. It is the maintainer's to decide, since it names what the kind means. **Answered 2026-11-24, (b) and (c), each selectable.** How the contract selects between them is SVA-Q49.

**SVA-Q43. What is the shape of the source collection?** Under (b). (a) An RDF list, read by `src:items/rdf:rest*/rdf:first`, so a source holding a list has one order and no repeats lost. (b) A property repeated on the instance, which needs no expansion, since a plain assertion already writes one statement for each value. (c) A delimited string, split by a stated separator, which needs a new string operation in MORK. Leaning (a), since (b) is the plain mapping already compiled and (c) widens MORK's expressions, which would be its own question. A hierarchy reading under SVA-Q42 (c) would instead name a property to close over. **Answered 2026-11-24.** An RDF list for (b), and the transitive relation itself for (c). A delimited string is left out, since splitting one needs a string operation SPARQL lacks. The maintainer raised a fourth source, a subgraph obtained by SHACL evaluation, which is SVA-Q49.

**SVA-Q44. What does each member become?** (a) A statement on the instance, the result-target binding's property linking the instance to the member where the member is a node, or carrying it where it is a literal, and nothing minted. (b) A node for each member, minted by SVA-Q32's identity (per instance or by key), which makes the expansion a graph construction over a collection. Leaning (a), since (b) is the construction case with a path that gives several values and would be a widening of that kind, not a kind of its own. **Answered 2026-11-24, (a).** A node for each member, expansion combined with graph construction, is planned as a slice of its own after this kind.

**SVA-Q45. What does an empty or missing source write?** (a) Nothing in both cases, with an instance that lacks the property excluded and reported by `InstanceExcluded` on required evidence, and an empty collection reported by a new check, since a collection that holds no member is a source the reviewer should see. (b) As (a) and the empty collection silent, so only a missing property is reported. (c) An empty collection writes a stated marker, such as `rdf:nil`, which states what the source said and is a value some consumers would read as a member. Leaning (a), and the maintainer decides whether the empty collection's report is a warning or information, as SVA-S2h's unmatched report was. **Answered 2026-11-24, (a).** An empty collection is reported as information.

**SVA-Q46. Does the contract bound the expansion, and what does the engineering review record?** (a) The contract states no limit, and the finding on the scheme, a new code since `MappingReview` is the merge's, records that the number of statements for an instance depends on the data and names the source. (b) The contract may state a maximum number of members, `srf:expansionLimit`, an integer, and a source with more is reported and writes the first members in list order. (c) As (b) and a source with more writes nothing for that instance. ADR-A41's engineering review has no code yet, since `MappingReview` is the merge's finding for a join and a keyed construction, so an expansion adds its own, `ExpansionReview` (first named `EngineeringReview`, renamed on 2026-11-25 so the findings are named by the projection kind they review). Leaning (a), the limit being a later slice when a use shows its meaning, since (b) and (c) name an order and a refusal that are modelling choices of their own. **Answered 2026-11-24, (a).** An expansion carries an `EngineeringReview` finding of its own, as ADR-A41 asks.

**SVA-Q47. Which terms does the contract gain?** The case needs a way to state on the result-target binding what is expanded, from which evidence binding and from what source shape. Leaning the shape of SVA-S2g and SVA-S2h, a statement node reached by an `srf:expandedAs` on the result-target binding, with a closed choice of source shape as individuals, and laws beside P10 to P17 that check it is set once, on a result-target binding, names an evidence binding of its own contract and is stated for the kind. The names are placeholders and the term a hierarchy needs, if SVA-Q42 chooses (c), would differ. MORK needs none if (a) of SVA-Q43 and (a) of SVA-Q44 are chosen, since the path and the assertion exist, and gains one check for the empty collection. It is the maintainer's to decide, since it adds terms to two published modules. **Answered 2026-11-24, as leaned.**

**SVA-Q48. Which decisions change?** Leaning, as for SVA-Q34 and SVA-Q41: an addendum to ADR-A18 that replaces the sentence leaving an expansion as a bare mapping (an expansion lowers into a scheme whose assertion reads the collection), an addendum to ADR-A23 (`mork_rdf` compiles expansion projections, with the empty-collection check and the engineering review finding ADR-A41 asks for), new laws in the Surface register after P17, and minor versions of the Surface and MORK modules for their new terms, each released by `mise run version:bump` at the merge. ADR-A41 needs no addendum. The amendments to ADR-A18 and ADR-A23 are the maintainer's to decide. **Answered 2026-11-24, approved.**

**SVA-Q49. How does an expansion state its members, and does a subgraph obtained by SHACL evaluation become a source?** The maintainer asked for list members and a transitive closure, each selectable, and raised a subgraph obtained by SHACL evaluation. That is two things. (d1) The members are the nodes a SHACL property path reaches from the instance. A list's members are `src:items/rdf:rest*/rdf:first` and a closure is `ex:broader+`, so one path covers both and more, in SHACL's own path vocabulary, which compiles to a SPARQL property path with no new engine. (d2) The members are the nodes that conform to a SHACL node shape, which needs a SHACL engine at run time, since a shape may recurse or use SHACL-SPARQL and does not reduce to one query in general. (a) Adopt (d1) as how an expansion states its members, with two named conveniences, a list's members and a property's transitive closure, which the lowering writes as their paths, and put (d2) in the backlog. (b) The closed choice of a list or a closure alone, and both of (d) in the backlog. (c) (d1) and (d2) both now. Leaning (a): the path is the selection, so no separate switch is needed, and (d2) carries cost and determinism questions of its own. **Answered 2026-11-25, (a), with (d2) dropped and not kept in the backlog.** An expansion selects a subgraph from an instance already identified, by a path, and (d2) would select several instances by conformance, which is not what an expansion is.

**SVA-Q50. How do an expansion and a construction share one result-target binding?** (a) One statement names both, a constructed node that states `srf:constructedFrom` an expansion statement, so the node is made for each member of that expansion. (b) Both are stated on the binding, `srf:expandedAs` and `srf:constructedAs`, and the construction is read for each member the expansion reaches. (c) A projection kind of its own, with its own statement. (b) keeps each term's meaning and relaxes `srf:P10` and `srf:P18` to say that a construction and an expansion are stated together only on one binding, and a contract with one projection kind says which kind it is, which the sketch's name for the slice, expansion combined with graph construction, leaves open. (a) states the pairing in one place and adds a term. (c) breaks SVA-Q28 (c), which counts four kinds. Leaning (b) with the contract an expansion projection, so the one new law is that a construction on an expansion's binding is stated with an expansion statement on the same binding. It is the maintainer's to decide, since it changes two published laws. **Answered 2026-11-25, (b).**

**SVA-Q51. What does "for each instance" mean for a node made from a member?** (a) One node for each instance and member, so a member that two instances hold gives two nodes, and `srf:PerInstance` reads as the pair. (b) One node for each member wherever it occurs, so two instances holding one member share one node, which is a merge and is what `srf:ByKey` already states for a key. (c) The contract states it, as SVA-Q32 requires, with `srf:PerInstance` meaning (a) and `srf:ByKey` meaning (b) or (a) according to the key. Leaning (c), since SVA-Q32 refused an implicit identity, and the pair is the one reading of a node for each instance that loses no member. A node for each instance of a list that repeats a member gives one node, since the query writes a set, so a node is a node for each distinct member and not each position. The contract cannot state a node for each position without a numbering that SPARQL's list path does not give. **Answered 2026-11-25, (c).**

**SVA-Q52. What may a key read?** (a) The instance's required-evidence bindings alone, as `srf:P13` states, so no key part reads a member, and a node for each member is `srf:PerInstance` only. (b) The instance's bindings and the member, the member a part of the key stated by a flag on the node, so a key is the bundle's code and the member, or the member alone. (c) The member alone. (b) is the one reading that gives a node for each member wherever it occurs and a node for each instance and member from one pair of terms. (a) cannot merge. (c) loses the instance and gives a node that a second bundle would also write, which is a different meaning from a node for each instance. Leaning (b), with the law that a key states at least one part and that the member is at most one part, and the key spelled into the identifier as before. A key that reads a member of unstable identity is a hazard, see SVA-Q55. **Answered 2026-11-25, (b).**

**SVA-Q53. What does a node write from its member?** (a) The member itself, as the value of a property, a flag `srf:fromMember` on a written value, beside `srf:fromBinding`. (b) A property of the member, read by a path from it, which is evidence from a second carrier and is a join or a lookup of the member and not an expansion. (c) Both. (b) needs the second carrier's properties stated as evidence, as a join states them, and writes what a promotion over the link could read, so it risks the stale copy SVA-Q37 refused. Leaning (a), with the instance's values written as today, and a value of the member's own properties reached by a read path over the link or by a later case. Whether the member is a node or a literal changes what the property's range is, which `srf:P1` must read when a vocabulary declares one. **Answered 2026-11-25, (a).** A value of a member's own properties is written by a join from the constructed node to the member, which must model it where it is wanted, and never copied by the construction.

**SVA-Q54. Is a member that is an IRI the node, or a reason to mint one?** (a) A node is always minted, from the identity SVA-Q51 and SVA-Q52 state, and the member is written as a value, so the IRI is spelled into the minted identifier. (b) A third identity, `srf:MemberNode`, makes the member itself the node, so the construction types the member and writes on it and mints nothing, which is how a source-node identity writes on the instance. It applies only where the members are IRIs, and a literal or blank-node member is a run-time check's report. (c) Both, the contract stating which. (b) enriches a node the source already names, so two instances holding one member write on one node, which is a merge by another route and a write onto the world's own node. (a) is the reading SVA-Q44 gives for a minted node and adds an identifier that is a function of another identifier. Leaning (a), (b) left until a contract needs it, since (b) widens what an expansion may write onto and has its own questions. Under (a) a member that is a literal spelled into an identifier is the personal-value hazard of SVA-Q32, which Surface cannot check. **Answered 2026-11-25, (c).** The contract states which, a node minted for each member or the member itself the node, since some deployments need the member enriched despite the risk of writing onto a node the source names.

**SVA-Q55. What happens to a member that has no stable text?** A list's member may be a blank node, and a blank node has no identifier a key can spell, so a node whose identity reads one gives a different identifier on each run. (a) A check, `MemberUnnamed`, names each instance with a blank-node member, the instance writes nothing for that member, and the rest of its members are written. (b) The instance writes nothing at all, as an instance that lacks a required value does (SVA-Q33). (c) The identity reads a position and not the member, which needs a numbering SPARQL's path does not give. Leaning (a), the member being the unit of the expansion, and the report a warning since a source of blank members would otherwise write nothing and say nothing. It is part of the question whether a member that is a literal is spelled as its lexical form with its datatype, as a key part does elsewhere. **Answered 2026-11-25, (a), with a stable name selectable.** The contract may name a property of the members that is known to be unique for them, and the identity spells that property's value in place of the member, so an unnamed member is the unusual case. A member that lacks the property, or is a blank node where none is named, is reported by `MemberUnnamed` and skipped.

**SVA-Q56. Which decisions change?** Leaning, as for SVA-Q34, SVA-Q41 and SVA-Q48: an addendum to ADR-A18 (a construction that states an expansion lowers into a scheme whose contextual datum is guarded and reads the member), an addendum to ADR-A23 (`mork_rdf` compiles it, with the one term that names the member, the reports the answers above choose, and the `MappingReview` and `ExpansionReview` findings both of its parts already carry), new laws in the Surface register after P20, and minor versions of the Surface and MORK modules for their new terms, each released by `mise run version:bump` at the merge. ADR-A41 needs no addendum. The amendments to ADR-A18 and ADR-A23 are the maintainer's to decide. **Answered 2026-11-25, as leaned.**

## 4. Slices

Every projection kind is built in this unit (SVA-Q28 (c)). A slice for graph construction, join or expansion starts by adding its case to this sketch, with the contract it lowers, the scheme and the query, and pauses for the maintainer where the case raises a question the answers above do not settle.

| Slice | What | Done when |
|---|---|---|
| SVA-S2e | the expression vocabulary in Surface and MORK (the arithmetic, a typed literal, rounding and a choice on a comparison), with shapes and the laws' checks, the ARR example stating its operation, the lowering carrying a derivation into a scheme with a source-node root, and the addenda to ADR-A18 and ADR-A23 drafted | the ARR contract lowers to a scheme MORK's shapes accept, deterministically |
| SVA-S2f | `mork_rdf` compiles a derivation: value expressions, the source-node identity, and the check for a missing operand | the ARR scheme compiles to the query of section 2.1, and runs to the expected values over a sample |
| SVA-S2g | graph construction projections, from contract to compiled scheme, with an example | an example's projection compiles and runs to its expected graph |
| SVA-S2h | join projections, with the mapping review ADR-A41 asks for recorded as a finding, and an example | an example's join compiles and runs to its expected rows |
| SVA-S2i | expansion projections, with the engineering review recorded as a finding, and an example | an example's expansion compiles and runs to its expected rows |
| SVA-S2j | a node constructed for each member of an expansion, with an example. Built 2026-11-25 as section 2.5 shows | an example's expansion constructs a node for each member and runs to its expected graph |
| SVA-S2c | the surface compile job lowers and compiles projections, the facility sample gains them, and a step's projection part runs as a second run of the Python worker (SVA-Q29). Built 2026-11-25 except the pane that sends the second run, which is the surface simulator pane's (SVA-S3) | a step over the sample shows each projection's rows, equal to its compiled scheme run over the world after |

## 5. Placement

T0. Surface's projections, MORK and `mork_rdf` are open substrate, and the ARR example is generic.
