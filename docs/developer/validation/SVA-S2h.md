<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-S2h, join projections

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-S2h, built on 2026-11-24 in autonomous mode, from the [projection backend sketch](../sketches/projection-backend.md) as the maintainer answered SVA-Q36 to SVA-Q41 on 2026-11-24, all as leaned, and followed up the same day on the maintainer's seven answers on joins, which the sections below record.

## Invariant

A join projection states the relation it writes on its result-target role binding, a statement that pairs evidence bindings of the contract's own carrier with bindings of a second carrier, that says how many instances of the second one a value may name and how many links an instance may have, and lowers deterministically into a mapping scheme `mork_rdf` compiles with a case of its own. The join writes the link from the instance to the instance it names and copies nothing. An instance contributes whole or not at all, since the guard on the join datum is tested on the instance, and the guard holds the instance's required evidence and never the matched node's beyond the key. A value that names several writes no link for that value under at most one, and is reported with each match. An instance whose values together find several writes no link under at most one link, and is reported with each. An instance that holds the values and finds none writes no link and is reported, as a warning on required evidence and as information on candidate evidence. An instance that lacks the values on candidate evidence says nothing. Each pair compares its values as it says. A join datum carries a mapping review finding. A lookup is unchanged and still reads reference data only.

## What changed

- **Surface**, from its README: `srf:JoinStatement`, `srf:JoinPair` and `srf:JoinCardinality` with the individuals `srf:AtMostOne` and `srf:AnyNumber`, and the properties `srf:joinedAs`, `srf:joinsOn`, `srf:joinLeft`, `srf:joinRight`, `srf:joinMatches` and `srf:joinLinks`. Laws `srf:P14` to `srf:P17` with 12 shapes of their own, and `srf:P1` states that a join reads its scope from its link. The example is `order-customer-join-projection.ttl`. The release note says P14 may invalidate a join that states no relation.
- **MORK**, from its README: `mork:JoinCondition` and `mork:JoinCardinality` with `mork:AtMostOneMatch` and `mork:AnyNumberOfMatches`, and the properties `mork:joinsOn`, `mork:parentRef`, `mork:ownRef`, `mork:joinCardinality`, `mork:linkCardinality`, `mork:reportsUnmatched` and `mork:unmatchedSeverity`, with three shapes. A condition states its own `mork:lookupComparison` and `mork:lookupDatatype`, which have no domain, so no term is added for them. MCN gains a code for each new term, since its coverage test requires one for every term.
- **The lowering**, `lowering.py`, `model.py` and `naming.py`: a join lowers into a scheme with a source-node root and a join datum that iterates the second carrier, takes the node it finds as its identity, states each equality with its own comparison, both counts, whether it reports an unmatched instance and as what, and is guarded by the required evidence of the instance. `srf:producesMapping` is written as for a derivation. Only an expansion keeps the bare mapping.
- **`mork_rdf`**, from its README section 7.10: a join case (`Kind.JOIN`, one construct for the link, joined on a variable the two patterns share), four run-time checks `InstanceExcluded`, `JoinUnmatched`, `JoinAmbiguous` and `JoinManyMatches`, four compile-time findings `JoinIncomplete`, `JoinWrites`, `JoinComparisonUnknown` and `JoinLexical`, and a `MappingReview` warning on every join datum. A compiled check carries the severity its rows are reported with. The lookup's code is untouched.
- **The addenda** to ADR-A18 and ADR-A23 for this kind, Proposed, beside the earlier ones, say what is built, the follow-up included. The sketch's section 2.3 shows the contract, the scheme and the query as built.

## The follow-up of 2026-11-24

The maintainer answered seven points on joins. Each is built as follows.

1. **Candidate evidence with no match.** An instance that holds the compared values and finds no match is reported by `JoinUnmatched` as information, through `mork:unmatchedSeverity mork:InfoFinding`. An instance that lacks the values stays silent. Required evidence is unchanged, a warning. The lowering always writes `mork:reportsUnmatched true`.
2. **The guard's limit** is stated in the Surface README's join section, `mork_rdf`'s README section 7.10, the MORK README's join text and ADR-A18's join addendum. Nothing is built for it.
3. **A datatype per pair.** The pair's datatype is its right binding's, the second carrier's, and the instance's value is cast to it. A left binding that states a datatype has a right one (`srf:P17`), so a pair may cast one side and the pairs of a statement may differ. Each `mork:JoinCondition` carries its `mork:lookupComparison` and `mork:lookupDatatype`, and a condition that states none reads the datum's, then a lookup's default.
4. **The default.** `srf:joinMatches` may be omitted and then means `srf:AtMostOne`, stated in its definition. The shape no longer requires it, and MORK's still does for `mork:joinCardinality`. The lowering writes it always.
5. **Two rules.** `srf:joinMatches` and `mork:joinCardinality` count per value. `srf:joinLinks` and `mork:linkCardinality` limit the links of an instance, any number where omitted, and the lowering writes it always. Under at most one link an instance whose values together find several writes no link and `JoinManyMatches` names each match.
6. **The addenda** are updated and their status stays Proposed.
7. **The sketch's section 2.3**, this pack and the release notes of Surface and MORK are updated.

### Names chosen

`mork:linkCardinality` and `srf:joinLinks` name the second rule. The index held no name for it (`exists linkCardinality`, `joinLinks`, `joinLinkLimit` and `linksPer` found nothing, `find` answered with `joinCardinality` and the individuals only). `mork:unmatchedSeverity` names how an unmatched instance is reported and reuses `mork:FindingSeverity` with `mork:WarningFinding` and `mork:InfoFinding`. `JoinManyMatches` names the new check. The two rules share `srf:JoinCardinality` and its two individuals in Surface, and `mork:JoinCardinality` and its two individuals in MORK, whose names read as a count of nodes found, which fits a value and a parent alike.

## Choices the sketch did not settle

1. **An unmatched instance on candidate evidence is reported as information.** The join writes the link and nothing else, so what a candidate-evidence binding finds is the link, and an instance with no match has nothing to write. First built silent, it is reported as information where it holds the compared values since the follow-up (item 1 above).
2. **A join is on one evidence kind.** The two bindings of a pair, and every pair of a statement, are all required or all candidate evidence (`srf:P17`), so the statement has one answer to what a missing match means. A mixed statement is refused.
3. **The guard is the parent's.** A guard on a join datum is tested on the instance and not on the node found, since it says which instances join. It holds the required-evidence bindings of the contract's own carrier and none of the second carrier's, which read other instances. This is the one place a guard's focus is the parent's.
4. **The comparison is the lookup's, stated by the lowering for each pair.** A join condition reads `mork:lookupComparison` and `mork:lookupDatatype`, which MORK defines for a lookup, so no comparison term is added. The lowering states a term comparison where the right binding states no datatype and a cast to the datatype where it does, on the pair's own condition.
5. **The cardinality and `mork:reportsUnmatched` are stated in MORK, never defaulted there.** A MORK shape requires both, so a join datum leaves neither implicit. The contract may omit the match count, and the lowering then writes its default. `mork:linkCardinality` and `mork:unmatchedSeverity` are optional in MORK with defaults the term definitions state, any number and a warning, so a mapping written before them means what it meant, and the lowering writes both always.
6. **The count is per value.** An instance with two values at a compared path that each name one customer has two links. It was first counted per instance, which contradicted the addendum's own words, and is fixed.
7. **The right binding keeps `srf:bindsCarrier`.** The lowering still reads it as a dependency edge on another contract in the batch whose carrier is that class. For a join the edge is also true, since the join reads that class, and the edge is written only when a contract of that carrier is in the batch.
8. **An existing test scenario changed kind.** The lowering dependency scenario used a join projection with no statement, which `srf:P14` now refuses, so it uses an expansion, which still keeps the bare mapping. No other existing test changed.
9. **A subquery names the customer it counts apart from the outer query.** The limits and the two checks count matches in a subquery. As first written it shared the outer query's variables, and the first run gave the order with two customers a link to both on rdflib, since a variable the outer query has bound is bound inside a subquery there too (TSD-79). Since counting is per value the subquery also projects the parent's compared values and repeats the outer query's patterns on them, so it shares only what it projects and counts the matches in a variable of its own.
10. **A left binding that states a datatype needs a right one.** The cast goes to the second carrier's type, so a left datatype with no right datatype has no target. It is refused by `srf:P17` and its shape. A right datatype alone is allowed, and casts the instance's value.

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
| S2h-T13 | a join on candidate evidence, with an order that has a code no customer holds and one with no code / run on both engines / the first reported as information with its code, the second silent, and the severity of the finding a run returns is info where a required join gives a warning | L1 | | |
| S2h-T14 | an order with two codes that each name one customer, and one whose second code two customers hold / run on both engines / two links for the first, and for the second a link for the single code and none for the shared code, which names each customer | L1 | per-instance counting, as first built | the order with two codes had no link |
| S2h-T15 | the same orders under at most one link / run on both engines / no link for either, and `JoinManyMatches` names each customer the order's values find, while an order that finds one customer in all keeps its link | L1 | | |
| S2h-T16 | any number of matches for a value with at most one link, and any number for both / run on both engines / the first links only the order that finds one, the second links every match and reports neither | L1 | | |
| S2h-T17 | a contract and a mapping that omit the link count and the match count / lowered and compiled / the scheme states `mork:AtMostOneMatch` and `mork:AnyNumberOfMatches`, and the compiled queries equal those of a contract that states them | L1 | | |
| S2h-T18 | a composite key of a string pair and an integer pair, each condition stating its own comparison, and the same with the datum stating the cast and one condition overriding it / run on both engines / the string joins as the same term and the number is cast, and the unmatched value is reported with both values | L1 | | |
| S2h-T19 | a string the order holds against an integer the customer holds, with the datatype on the right binding alone and on both bindings / lowered, compiled and run on both engines / joined where the cast makes them one term, and not joined as the same term | L1 | | |
| S2h-T20 | a cast with no datatype on one condition of two / compiled / that condition alone is lexical, with an info finding that names its path | L1 | | |
| S2h-T21 | a link cardinality or an unmatched severity that is not one of the two, one stated twice, one on a datum with no condition, a condition comparison that is none of the three and a datatype stated twice / validated and compiled / each refused by MORK's shapes, and the compiler refuses an unknown link cardinality or severity by name | L1 | | |
| S2h-T22 | a left binding that states a datatype with no right one, a count the choice does not name, a count stated twice, and a statement that states neither count / read and validated / the first three refused by `srf:P15` or `srf:P17` and their shapes, and the last accepted with its defaults | L1 | | |
| S2h-T23 | the sub-select of each count / compiled / it projects the parent and the compared values, or the parent alone, and counts a variable no outer pattern names | L1 | the subquery sharing the outer variables | rdflib linked to both customers |

## Checks run

| Command | Result |
|---|---|
| `mise run check:python-root` | 258 tests, OK, and the phase 8 conformance passed. The follow-up added 11 to the 247 of the first build |
| `mise run check:mork` | 464 passed, and the MCN codes for the two new properties are in `mcn_codebook.py` and `mork-compact-notation.md` |
| `mise run check:mork-rdf` | 260 passed, 29 more than the 231 of the first build |
| `mise run check:mork-compilers` | 195 passed, 39 subtests |
| `mise run check:ontology-catalog` | 1319 passed, consistent, the 2 known defects |
| `literate_extract --check` for Surface and MORK | 4 and 3 artefacts consistent |
| `mise run check:identifiers` | passed, 2371 identifiers, 0 unresolved |
| `mise run check:published-decisions`, `check:owl-profile` | passed |

`check:mork` rewrote `ontology/mork/mtp/data/pins.lock.json`, which was restored, so its pins wait for `mise run build:mtp` at the merge. No version was bumped, so Surface and MORK wait for `mise run version:bump` at the merge, with the earlier slices' changes.

## Left open

- Whether the studio's review requirement acts on `MappingReview` or on the contract. It reads only the projection kind today, so a join needs that policy to read the finding or the contract before SVA-S2c acts on it, as a keyed construction does.
- Whether `srf:AtMostOne` is true of the second carrier's data is not checked against that carrier's own declaration. The report of `JoinAmbiguous` is how a contract that is wrong about it is found.
- The guard holds the instance's required evidence and never the matched node's beyond the key, so a required value of the second carrier other than the key goes unchecked. It is documented and nothing is built.
- A pair can cast the instance's value and never the second carrier's, so a pair that needs the second side cast cannot be stated. A left datatype with no right datatype is refused for that reason, and the reading of "a pair may cast one side" as the left side is to confirm.
- Under at most one link and at most one match, an instance with a shared code is reported twice, by `JoinAmbiguous` for the value and by `JoinManyMatches` for the instance, each naming each match.
- A decimal and an integer that are equal as values are different terms, so a term comparison does not join them and a cast to one datatype does.
- One engine difference is not yet a finding in the triple-stores domain. Variables an outer query has bound are bound inside a subquery on rdflib, which the limit of at most one avoids with variables of its own. Oxigraph and rdflib agree on every case the tests cover.

## Placement

T0. Surface, MORK, `mork_rdf` and the order and customer example are open substrate, and the example is generic.
