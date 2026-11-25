<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A23: MORK compiler family completion policy

**Status:** Accepted
**Date:** 2026-09-18
**Supersedes:** none
**Related:** ADR-A19 (staged compiler architecture), ADR-A24 (Eligibility executable strategy)
**Unit:** [`surface-mork-unified-projection`](../../developer/plans/surface-mork-unified-projection-plan.md) (epic)
**Source plan:** the Surface-MORK Unified Projection Program plan

## Context

The MORK enhancements analysis documents the gap directly: MORK's vocabulary already models `ShapeMapping`, `RuleMapping`, and `QueryTemplate` as generative mappings with parameter bindings and targeting specs, but only `tools/mork/src/mork2rml.py` exists, and it explicitly skips `ShapeMapping` and `RuleMapping` because it targets RML alone. SPARQL and native-IR compilers do not exist at all. The vocabulary is not the blocker. The compiler family is.

## Decision

**RML, SPARQL, SHACL, SWRL, and native IR are first-class compiler targets**, each built on the staged core from ADR-A19. `tools/mork/src/mork2rml.py`'s skip of `ShapeMapping` and `RuleMapping` is closed by adding the SHACL and SWRL compilers those mapping kinds already describe, not by narrowing what the vocabulary claims to support.

## Consequences

- Four compiler modules are added: MORK-to-SPARQL, MORK-to-SHACL, MORK-to-SWRL, MORK-to-native-IR, alongside the existing MORK-to-RML.
- No vocabulary change is required — `mork:GenerativeMapping`'s subclasses already cover all five targets, per the MORK enhancements analysis's own account.
- Each target needs its own fixture corpus and provenance population, because "vocabulary support" without a compiler reading it, as the MORK enhancements analysis's status table records for SPARQL and SWRL today, does not count as complete.
- Eligibility's executable strategy (ADR-A24) is the first consumer that needs the SPARQL, SHACL, and SWRL targets in combination, and its delivery order constrains which of these four is built first.

## Addendum (2026-09-18): implemented, minus native

**No native-IR compiler.** Neither the delivery plan nor any other document in this repository defines what a native artefact would be, so none was built and none is planned pending an actual definition. This ADR's "five targets" is reduced to four in practice: RML (`tools/mork/src/mork2rml.py`, pre-existing), SPARQL, SHACL, and SWRL (`tools/mork_compilers/`, new).

SPARQL, SHACL, and SWRL are implemented for `elg:IntervalCondition` only, via the shared IR in `tools/mork_compilers/eligibility_ir.py`, per ADR-A24. Full details, including what was deliberately left out (profile-level aggregate artefacts, runtime result tracking, and the "Executable Projection Contract" domain-binding layer the MORK enhancements analysis also proposes), are in `ontology/mork/docs/eligibility-executable-compiler.md`. Not executed: no Python interpreter or SPARQL/SHACL/SWRL engine was available when this was written.

## Addendum (2026-10-30, Proposed with ADR-A148): XSLT and JOLT

ADR-A148 proposes XSLT and JOLT as targets for a mapping over an XML or JSON source, compiled from a logical plan read by `tools/mork_rdf`'s reader. It takes effect when ADR-A148 is accepted.

## Addendum (2026-11-23): mork_rdf compiles derivation projections

**Status of this addendum:** Accepted by the maintainer on 2026-11-24.

ADR-A18's addendum of the same date lowers a derivation projection into a mapping scheme whose root takes the source node as its identity and whose assertion has a value expression. Nothing compiles that scheme yet, and by the policy above a vocabulary no compiler reads does not count as complete.

1. **`mork_rdf` compiles a lowered derivation.** The compiler of mapping schemes over an RDF source reads the root and its assertion and writes one CONSTRUCT query. The assertion writes the result property on the source node. The expression compiles to SPARQL arithmetic in a `BIND`, each reference bound by the path it reads, and a rounding, a choice and a quotient compile to `ROUND`, `IF` and division.
2. **A carrier missing an operand writes nothing, and a check reports it.** A value that is undefined, such as a quotient by zero, writes nothing in the same way. A derived property is never half written.
3. **No new vocabulary.** The terms are those ADR-A18's addendum names. A scheme over an RDF source is compiled to SPARQL by `mork_rdf`, and the other kinds keep the compilers this decision lists.

**Consequences.** The compiled query of a derivation is the same for the same scheme, and a sample of the carrier class run through it gives the derived values. Until the compiler exists, a lowered derivation is checked by MORK's shapes and compiled by nothing.

## Addendum (2026-11-24): mork_rdf compiles graph construction projections

**Status of this addendum:** Accepted by the maintainer on 2026-11-24.

ADR-A18's addendum of the same date lowers a graph construction projection into a mapping scheme with a source-node root, a guarded contextual datum that mints the constructed node, and an assertion for each value. By the policy above a vocabulary no compiler reads does not count as complete.

1. **`mork_rdf` compiles a lowered construction with its existing cases.** The root, the contextual datum with its guard and identity, and the assertions are compiled as they are for any scheme, and no mapping kind is added. A guard sits on the datum's frame, which every query beneath inherits, so an instance contributes whole or not at all.
2. **Two checks report what the cases leave unsaid.** One names each instance the datum's guard excludes for want of a required value, with the value it lacks. One names a node whose identity is read from the source and whose instances give a property different values, with the node and each value. A keyed datum beneath a source-node datum also carries a `MappingReview` warning.
3. **No new vocabulary.** The terms are those ADR-A18's addendum names.

**Consequences.** The compiled queries of a construction are the same for the same scheme, and a sample of the carrier class run through them gives the nodes, the links and the values, with the excluded instances and the disagreements reported. Until a reader of the findings acts on `MappingReview`, the review ADR-A41 asks for is a finding and no more.

## Addendum (2026-11-24): mork_rdf compiles join projections

**Status of this addendum:** Accepted by the maintainer on 2026-11-24.

ADR-A18's second addendum of the same date lowers a join projection into a mapping scheme whose second datum takes a node of the second carrier's class from the source by equality of values. A lookup cannot compile it, since a lookup reads reference data only so that source data cannot add codes to it (`mork_rdf` MR-10), and the policy above does not count a vocabulary no compiler reads as complete.

1. **MORK gains a join datum.** A datum that states `mork:joinsOn` takes the node of the class it iterates whose values equal its parent's. A `mork:JoinCondition` states each equality by a path from the parent and a path from the node found, and its own `mork:lookupComparison` and `mork:lookupDatatype` as a lookup states them, so a key may mix datatypes. A condition that states no comparison means a term comparison. A join datum states neither property, a shape refuses one that does, and no comparison is read from the datum or from a lookup's default (decided 2026-11-24). The datum states `mork:joinCardinality`, `mork:AtMostOneMatch` or `mork:AnyNumberOfMatches`, and `mork:reportsUnmatched`, and may state `mork:linkCardinality` and `mork:unmatchedSeverity`. It takes `mork:SourceNodeIdentity` and writes the link by an R-Box match and nothing else. Shapes refuse a join datum that leaves out a part.
2. **`mork_rdf` compiles it as a case of its own.** The datum's frame matches an instance of its class and the equality, a term or cast comparison sharing one variable between the two patterns so an engine can serve it from an index. A guard on the datum is tested on the parent, so it holds the parent's required values and never the node found's beyond the key it was matched on. Under at most one the construct is limited, for each value of a parent, to the values whose matches number one, so two codes that each name one node give two links. Under at most one link it is also limited to the parents whose values together find one node. Each limit is a sub-select that names the node it counts apart from the outer query's variables.
3. **Three checks and a review report what the case leaves unsaid.** `InstanceExcluded` names each parent the guard excludes, `JoinUnmatched` a parent that holds the compared values and finds no node, where the datum says so, as a warning or, where the datum says so, as information, `JoinAmbiguous` each match of a value that finds several under at most one, and `JoinManyMatches` each match of a parent whose values together find several under at most one link. A join datum carries a `MappingReview` warning, which ADR-A41 asks of a join.
4. **A lookup is unchanged.** It reads reference data only, and a join reads the source.

**Consequences.** The compiled query of a join is the same for the same scheme, and a sample of the carrier and second classes run through it gives the links, with the excluded, unmatched and ambiguous instances reported. Until a reader of the findings acts on `MappingReview`, the review ADR-A41 asks for is a finding and no more. A source can add nodes to a join where it cannot add codes to a lookup, which is why a join to curated reference data stays a lookup.

## Addendum (2026-11-25): mork_rdf compiles expansion projections

**Status of this addendum:** Accepted by the maintainer on 2026-11-25.

ADR-A18's addendum of the same date lowers an expansion projection into a mapping scheme whose root takes the source node as its identity and whose one assertion beneath it reads a path that reaches the members. The root and the assertion are cases `mork_rdf` already compiles, and the policy above does not count a vocabulary no compiler reads as complete.

1. **`mork_rdf` compiles it with its existing cases.** An assertion with a `mork:dataRef` directly beneath a source-node datum writes the property on the node itself, one statement for each node the path reaches, and no mapping kind is added. A path is SPARQL's property path, so a list's members and a transitive closure need no construct of their own. A guard on the assertion is tested on the node it asserts on.
2. **A check and a finding report what the case leaves unsaid.** `CollectionEmpty` names each node the guard admits that holds the property the path starts from and whose path reaches no member, with the path, as information, and a node that lacks the property is silent, so on candidate evidence only an empty collection is reported, as a join reports only an instance that holds its values. `ClosureCycle` names each node that reaches itself through a closure the path walks, `*` or `+`, with the closure, as a warning. `InstanceExcluded` names each node the guard excludes, with the value it lacks, as it does for a construction and a join. The compiler records `ExpansionReview`, a warning on the assertion that names the path and says the number of statements for one node depends on the data, which ADR-A41 asks of an expansion.
3. **No new vocabulary.** MORK gains no term, and the terms are those ADR-A18's addendum names.

**Consequences.** The compiled query of an expansion is the same for the same scheme, and a sample of the carrier class run through it gives the statements, with the excluded nodes and the empty collections reported. Until a reader of the findings acts on `ExpansionReview`, the review ADR-A41 asks for is a finding and no more. The finding is raised for every assertion of that shape, since the compiler sees the scheme and not the contract. A cycle in a relation a closure follows makes a node its own ancestor, which SPARQL's path semantics allow, and `ClosureCycle` reports each node that reaches itself. A list expansion takes the same check over the list's cells, which costs one more walk of each list.

## Addendum (2026-11-25): mork_rdf compiles a node for each member

**Status of this addendum:** Accepted by the maintainer on 2026-11-25.

ADR-A18's addendum of the same date lowers an expansion that states a construction into a scheme whose contextual datum states the expansion's path. The datum, its guard, its identity and its assertions are cases `mork_rdf` compiles, except that none of them can read one member of the collection for the identity, the link and each value together, and the policy above does not count a vocabulary no compiler reads as complete.

1. **One term binds the member once.** A contextual datum beneath a source-node root that states `mork:memberRef` is made for each node the path reaches, and binds it as a variable of its own frame, which its identity, its link to the root's node and every query beneath it inherit. A `mork:MemberExpression` in an identity template is the member, spelled and encoded. An assertion that states `mork:dataMember true` writes the member itself, except that a blank member that has a stable name is written as the name's value and never as a blank node. A datum with no template has one node for each focus node and member, and `mork:MemberIdentity` makes the member the datum's node, so nothing is minted. A node is spelled by its IRI and a literal by its lexical form and, where the datatype is not `xsd:string`, its datatype after two carets. `mork:memberName` spells a property's value in place of the member.
2. **A check reports what the case leaves out.** `MemberUnnamed` names the focus node and each member that has no name to spell, a blank node where no name is stated or a member without the named value, as a warning, and the focus node's other members are written. `MemberNotIri` names the focus node and each member that is a literal or a blank node where the member is the node, as a warning. A blank node is, in a run, a skolem IRI (ADR-A147), so a node is blank where either it is a blank node or its IRI begins with the skolem prefix. The datum takes `InstanceExcluded`, `CollectionEmpty` and `ClosureCycle` as an expansion does, and `IdentityAmbiguous` groups by the focus node and the member.
3. **The findings are the two the parts already carry.** The datum records `ExpansionReview`, a warning that names the path, and `MappingReview` where its identity reads the member without the focus node, or the member is the node, since each merges the focus nodes that share a member. A node for each focus node and member takes the first alone.
4. **MORK gains five terms.** `mork:MemberExpression`, `mork:MemberIdentity`, `mork:memberRef`, `mork:memberName` and `mork:dataMember`, with shapes for a datum made for each member and for where a member name and `mork:dataMember` may be stated. The shape that states the rules of `mork:SourceNodeIdentity` now states them for that identity alone. `mork:MemberIdentity` is the second individual of `mork:IdentityRule`.

**Consequences.** The compiled queries of a node for each member are the same for the same scheme, and a sample of the carrier class run through them gives the nodes, the links and the values, with the excluded instances, the empty collections and the members without a name reported. The identity spells the member, so a member without stable text is a hazard that the contract decides with `srf:memberName` or a key that leaves the member out. Until a reader of the findings acts on them, the reviews ADR-A41 asks for are findings and no more.
