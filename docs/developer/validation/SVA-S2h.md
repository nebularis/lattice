<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-S2h, join projections

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-S2h, built on 2026-11-24 in autonomous mode, from the [projection backend sketch](../sketches/projection-backend.md) as the maintainer answered SVA-Q36 to SVA-Q41 on 2026-11-24, all as leaned.

## Invariant

A join projection states the relation it writes on its result-target role binding, a statement that pairs evidence bindings of the contract's own carrier with bindings of a second carrier, that says how many instances of the second one a value may name, and lowers deterministically into a mapping scheme `mork_rdf` compiles with a case of its own. The join writes the link from the instance to the instance it names and copies nothing. An instance contributes whole or not at all, since the guard on the join datum is tested on the instance. Under at most one an instance that names several writes no link and is reported with each, and on required evidence an instance that holds the values and finds none writes no link and is reported. A join datum carries a mapping review finding. A lookup is unchanged and still reads reference data only.

## What changed

- **Surface**, from its README: `srf:JoinStatement`, `srf:JoinPair` and `srf:JoinCardinality` with the individuals `srf:AtMostOne` and `srf:AnyNumber`, and the properties `srf:joinedAs`, `srf:joinsOn`, `srf:joinLeft`, `srf:joinRight` and `srf:joinMatches`. Laws `srf:P14` to `srf:P17` with 14 shapes, and `srf:P1` states that a join reads its scope from its link. The example is `order-customer-join-projection.ttl`. The release note says P14 may invalidate a join that states no relation.
- **MORK**, from its README: `mork:JoinCondition` and `mork:JoinCardinality` with `mork:AtMostOneMatch` and `mork:AnyNumberOfMatches`, and the properties `mork:joinsOn`, `mork:parentRef`, `mork:ownRef`, `mork:joinCardinality` and `mork:reportsUnmatched`, with three shapes. MCN gains a code for each term, since its coverage test requires one for every term.
- **The lowering**, `lowering.py`, `model.py` and `naming.py`: a join lowers into a scheme with a source-node root and a join datum that iterates the second carrier, takes the node it finds as its identity, states each equality, its cardinality and whether it reports an unmatched instance, and is guarded by the required evidence of the instance. `srf:producesMapping` is written as for a derivation. Only an expansion keeps the bare mapping.
- **`mork_rdf`**, from its README section 7.10: a join case (`Kind.JOIN`, one construct for the link, joined on a variable the two patterns share), three run-time checks `InstanceExcluded`, `JoinUnmatched` and `JoinAmbiguous`, four compile-time findings `JoinIncomplete`, `JoinWrites`, `JoinComparisonUnknown` and `JoinLexical`, and a `MappingReview` warning on every join datum. The lookup's code is untouched.
- **The addenda** to ADR-A18 and ADR-A23 for this kind, Proposed, beside the earlier ones. The sketch's section 2.3 shows the contract, the scheme and the query as built.

## Choices the sketch did not settle

1. **An unmatched instance on candidate evidence is silent.** The join writes the link and nothing else, so what a candidate-evidence binding finds is the link, and an instance with no match has nothing to write. The answer to SVA-Q38 says an unmatched instance writes what it finds on candidate evidence, and the sketch's wording does not say whether it is reported. It is not, and `mork:reportsUnmatched false` states that.
2. **A join is on one evidence kind.** The two bindings of a pair, and every pair of a statement, are all required or all candidate evidence (`srf:P17`), so the statement has one answer to what a missing match means. A mixed statement is refused.
3. **The guard is the parent's.** A guard on a join datum is tested on the instance and not on the node found, since it says which instances join. It holds the required-evidence bindings of the contract's own carrier and none of the second carrier's, which read other instances. This is the one place a guard's focus is the parent's.
4. **The comparison is the lookup's, stated by the lowering.** The join datum reads `mork:lookupComparison` and `mork:lookupDatatype`, which MORK defines for a lookup, so no comparison term is added. The lowering states a term comparison where the bindings state no datatype and a cast to the datatype where they do. A pair states one datatype or none, and so do the pairs of one statement (`srf:P17`), since MORK states the comparison once for a datum. A join on values of several datatypes is not yet stated.
5. **The cardinality and `mork:reportsUnmatched` are stated, never defaulted.** A shape requires both, so a MORK join datum leaves neither implicit, as the contract leaves neither implicit.
6. **The count is per instance.** An instance with two values at a compared path that name two customers is ambiguous under at most one.
7. **The right binding keeps `srf:bindsCarrier`.** The lowering still reads it as a dependency edge on another contract in the batch whose carrier is that class. For a join the edge is also true, since the join reads that class, and the edge is written only when a contract of that carrier is in the batch.
8. **An existing test scenario changed kind.** The lowering dependency scenario used a join projection with no statement, which `srf:P14` now refuses, so it uses an expansion, which still keeps the bare mapping. No other existing test changed.
9. **A subquery's variables are its own.** The limit of at most one and `JoinAmbiguous` count matches in a subquery. As first written it shared the outer query's variables, and the first run gave the order with two customers a link to both on rdflib, since a variable the outer query has bound is bound inside a subquery there too.

## Tests

| ID | Given / When / Then | Level | The break tried | The failure it gave |
|---|---|---|---|---|
| S2h-T1 | the example, a join on candidate evidence, under any number, with a datatype and on two values / lowered / a scheme MORK's shapes accept | L1 | | |
| S2h-T2 | the example and the two-pair join, repeated and in five orders of their triples / lowered / the same graph | L1 | | |
| S2h-T3 | the example / compiled / the query of the sketch pinned modulo whitespace, one construct, the three checks and one `MappingReview` | L1 | | |
| S2h-T4 | three orders and two customers on Oxigraph and rdflib / run / two links to the first customer, the third order reported with its code | L1 | | |
| S2h-T5 | a code two customers hold / run on both engines / under at most one no link and each customer named, under any number a link to each | L1 | the limit removed from the construct. Separately, the subquery sharing the outer variables, as first written | five tests fail. On rdflib the order with two customers links to both |
| S2h-T6 | an order with the code and without another required value, beside a customer that matches / run on both engines under each count / no link and the exclusion reported | L1 | the guard removed from the join frame | three tests fail |
| S2h-T7 | an order with no code on required and on candidate evidence / run on both engines / reported and excluded on required, silent on candidate | L1 | | |
| S2h-T8 | a join on two values, an integer and a string code under a cast, a term and a lexical comparison / run on both engines / each as the README says, the two values reported joined by a slash | L1 | | |
| S2h-T9 | a customer in the reference data and then in the source / run / a link only for the source's | L1 | | |
| S2h-T10 | a join datum that leaves out its cardinality, its report flag, its identity rule, its R-Box match, its class, a path of a condition, or has a mapping beneath it / compiled / refused by name and written nothing, and refused by MORK's shapes | L1 | | |
| S2h-T11 | a model and a shape for each law's breach, such as no statement, a statement on a derivation or another binding, no pair, no count, a side that is not evidence, a left that names a second carrier, a right that names none or two, mixed evidence kinds, and datatypes that differ / read and validated / each refused by its law and its shape | L1 | | |
| S2h-T12 | the lowered example, in three orders of its triples / compiled / the same text | L1 | | |

## Checks run

| Command | Result |
|---|---|
| `mise run check:python-root` | 247 passed, 56 of them new, and the phase 8 conformance passed |
| `mise run check:mork` | 464 passed |
| `mise run check:mork-rdf` | 231 passed, 34 of them new |
| `mise run check:mork-compilers` | 195 passed |
| `mise run check:ontology-catalog` | 1319 passed, consistent, the 2 known defects |
| `literate_extract --check` for Surface and MORK | 4 and 3 artefacts consistent |
| `mise run check:identifiers`, `check:published-decisions`, `check:owl-profile` | passed |

`check:mork` rewrote `ontology/mork/mtp/data/pins.lock.json`, which was restored, so its pins wait for `mise run build:mtp` at the merge. No version was bumped, so Surface and MORK wait for `mise run version:bump` at the merge, with the earlier slices' changes.

## Left open

- Whether the studio's review requirement acts on `MappingReview` or on the contract. It reads only the projection kind today, so a join needs that policy to read the finding or the contract before SVA-S2c acts on it, as a keyed construction does.
- A join on values of several datatypes, which needs a comparison for each condition where MORK states one for a datum.
- Whether `srf:AtMostOne` is true of the second carrier's data is not checked against that carrier's own declaration. The report of `JoinAmbiguous` is how a contract that is wrong about it is found.
- A decimal and an integer that are equal as values are different terms, so a term comparison does not join them and a cast to one datatype does.
- One engine difference is not yet a finding in the triple-stores domain. Variables an outer query has bound are bound inside a subquery on rdflib, which the limit of at most one avoids with variables of its own. Oxigraph and rdflib agree on every case the tests cover.

## Placement

T0. Surface, MORK, `mork_rdf` and the order and customer example are open substrate, and the example is generic.
