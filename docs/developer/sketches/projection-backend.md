<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Sketch: a projection backend, from a Surface projection contract to queries a step runs

**Unit:** `studio-visual-authoring` (SVA), slice SVA-S2d, raised on 2026-11-23 when the maintainer chose that projections are built in this unit, design first
**Status:** sketch. SVA-Q24 to SVA-Q30 answered by the maintainer on 2026-11-23. SVA-Q31 to SVA-Q34, raised by SVA-S2g on 2026-11-24, are open. Nothing is built for graph construction
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

A graph construction projection writes new structure that no single read path reaches, which is the one thing Surface's README says of it. In its simplest generic form it reads a few properties of each instance of a carrier and writes a new node of another class, linked from the instance, carrying those values. For example, each `src:Order` with `src:buyerName` and `src:buyerEmail` gives one `tgt:Party` with `tgt:name` and `tgt:email`, reached from the order by `tgt:placedBy`.

What `mork_rdf` compiles today fits the output. A root datum iterating `src:Order`, with a contextual datum beneath it that mints and types the party and is glued to the order by an R-Box match, and an assertion beneath that for each value, is its existing datum, contextual datum and assertion cases (section 5.1 of its README), with no new case. Nothing in the contract states that structure, and the contract cannot state it with what Surface has:

| What the output needs | What the contract has |
|---|---|
| the class of the constructed node | `srf:bindsCarrier`, which says the class a role's evidence is drawn from, not a class written |
| the link from the instance to the constructed node | the result-target binding's property, if it is taken to mean the link |
| a property for each constructed value | a second result-target binding, which `srf:P3` forbids |
| which evidence goes on which constructed property | nothing, since an evidence binding names the property it reads only |
| the identity of the constructed node | nothing. `mork_rdf`'s default is a hash of the source node's IRI, which is a rule, not a statement of the contract |

So the contract, the scheme and the query are not written here. A scheme can be written by hand, but writing the lowering would settle the questions below by implementation, and the sketch's rule for this section is to pause. SVA-S2g builds nothing until SVA-Q31 to SVA-Q34 in section 3 are answered.

## 3. Questions

**SVA-Q24. Where is a derivation's operation stated?** (a) In the contract, an expression on the result-target binding over the evidence bindings. (b) In MORK alone, added by hand to the lowered mapping. (c) As an approved template the backend policy names, a reviewed query fragment with its parameters bound by the roles. (b) breaks ADR-A18's deterministic lowering and leaves the contract without its meaning. (c) uses `srf:approvedTemplate`, which exists, but holds query text where the contract states meaning. Leaning (a). **Answered 2026-11-23, (a).**

**SVA-Q25. What operations does the expression vocabulary hold?** (a) The four arithmetic operations and a typed literal. (b) As (a), with rounding to a stated scale and a conditional choice of two values. (c) A general expression language. Leaning (a), with (b) when a contract needs it, since every operation added is one the laws and every backend must carry. **Answered 2026-11-23, (b).**

**SVA-Q26. How does MORK carry a value expression?** (a) New numeric expression classes beside the string ones, typed, compiled to SPARQL arithmetic. (b) The string expressions widened to any value. (a) keeps the string algebra a monoid and lets a typed operand be checked. Leaning (a). **Answered 2026-11-23, (a).**

**SVA-Q27. How does a derived value land on the carrier?** (a) A new identity rule, the source node itself, with no datum minted or typed. (b) A datum minted per carrier and linked to it. (b) changes what the contract states, a property of the carrier. Leaning (a). **Answered 2026-11-23, (a).**

**SVA-Q28. Which projection kinds does this unit build?** (a) Derivation, with ARR as the reference corpus ADR-A41 names. (b) Derivation and graph construction. (c) All four. A join needs a mapping review and an expansion an engineering one (ADR-A41), and each is a compiled case of its own. The maintainer asked that every behaviour the sketch names is built in this unit, and section 9 of the unit's sketch names projections without kinds. Leaning (a) now and the others as slices once (a) has run, each with its own example. **Answered 2026-11-23, (c).**

**SVA-Q29. Where does a step's projection part run?** (a) As a second run the surface pane sends, answered by the Python worker with `mork_rdf`'s driver, beside the surface step the Java run worker answers. (b) In the Java run worker, as plain CONSTRUCT queries on Jena, where a compiled projection needs none of the driver's rules. (c) The whole surface step in the Python worker. (a) keeps one worker to a run and the run protocol unchanged, and each part names its engine. (b) is a second runtime for MORK's compiled form, which the addendum of 2026-11-20 decided against. (c) moves the writer's maintenance, which is Java, out of the worker that runs it. Leaning (a). **Answered 2026-11-23, (a).**

**SVA-Q30. Which decisions change?** Leaning: an addendum to ADR-A18 (a derivation's expression is carried across by the lowering, and a lowered projection is a scheme with a source-node root), an addendum to ADR-A23 (`mork_rdf` compiles derivation projections), and minor versions of the Surface and MORK modules for their new terms, each released by `mise run version:bump` at the merge. **Answered 2026-11-23, as leaned.**

**SVA-Q31. How does a graph construction contract state what it writes?** (a) With the existing role kinds, taking the result-target binding as the link, `srf:bindsCarrier` on it as the constructed class, and allowing several result-target bindings for this kind, each a constructed property, paired with an evidence binding. This relaxes `srf:P3` and gives roles a second meaning. (b) With a new role kind for the constructed node and a new property pairing an evidence binding with the property it is written as. (c) With a construction statement on the contract, as `srf:derivedAs` is for a derivation (SVA-Q24 (a)), a small closed vocabulary: a constructed node with its class, its identity and its properties, each a role binding written as a stated property, and the link from the instance. Leaning (c), since the contract states and the compiler executes, and (a) and (b) leave roles meaning different things by kind. It adds Surface terms, laws and shapes.

**SVA-Q32. What is the identity of a constructed node?** (a) The contract states it as a key of one or more evidence bindings, so two instances with the same key give one node, which MORK's template identity compiles. (b) The hash of the source node's IRI, one constructed node per instance, which `mork_rdf` does by default and the contract leaves unstated. (c) The minting policy of the Surface profile (`LocalNameFromValue`, `DigestLocalName`), versioned with the profile. A key makes the projection merge instances, which is a different meaning from (b), and a join or an aggregation if the key spans carriers. Leaning (a), with (b) as the case where the contract states that each instance gets its own node, so the choice is never implicit.

**SVA-Q33. What does a constructed node do with missing evidence?** (a) A node is written only where every required-evidence binding has a value, and candidate-evidence bindings write what they find, as a derivation writes nothing for a carrier missing an operand, with a check naming the instance. (b) A node is written with whatever values exist. Leaning (a), since it gives the two evidence role kinds a meaning that holds across kinds.

**SVA-Q34. Which decisions change?** Leaning, as for SVA-Q30: an addendum to ADR-A18 that replaces item 4 for this kind (a graph construction lowers into a scheme whose constructed node is a contextual datum), an addendum to ADR-A23, new laws in the Surface register beside P6 to P9, and minor versions of the Surface and, if (c) of SVA-Q31 needs a term, the MORK module, each released by `mise run version:bump` at the merge. The amendment to ADR-A18 is the maintainer's to decide.

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
