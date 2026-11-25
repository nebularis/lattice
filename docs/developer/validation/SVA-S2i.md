<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-S2i, expansion projections

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-S2i, built on 2026-11-25 in autonomous mode, from the [projection backend sketch](../sketches/projection-backend.md) as the maintainer answered SVA-Q42 to SVA-Q49 on 2026-11-24 and 2026-11-25. The same session first removed the join condition's comparison fallback, which the maintainer decided on 2026-11-24 and which the section after the invariant records.

## Invariant

An expansion projection states the members it restates on its result-target role binding, a statement that names one evidence binding of the contract's own carrier and states its members as exactly one of a named source, a list's members or a property's transitive closure, and a SHACL property path from the instance. It lowers deterministically into a mapping scheme `mork_rdf` compiles with its existing cases and no mapping kind of its own. Each member is restated as one statement on the instance, the property the result-target binding binds, and nothing is minted. An instance contributes whole or not at all, since the guard on the assertion holds the instance's required evidence. An instance without the required property is excluded and reported. An instance the guard admits whose path reaches no member writes nothing and is reported as information. The contract states no bound on the number of statements, and the compilation records an engineering review as a finding that names the path. A path the contract states and the named source it equals lower to the same scheme.

## The removed fallback, Part A

The maintainer decided on 2026-11-24 that a `mork:JoinCondition` no longer falls back to its datum's comparison. A condition states its comparison and datatype, or states none, which means a term comparison and is never inherited. The datum-level `mork:lookupComparison` and `mork:lookupDatatype` are removed from a join datum in MORK's README, `mork_rdf`'s reader and compiler read none from the datum, and `mork:JoinDatumShape` refuses a join datum that states either. The compiler also refuses one by name, `JoinDatumComparison`. The lowering already wrote each comparison on the condition and none on the datum. `customer-mapping.ttl` and `test_join.py` relied on the fallback, and the fixture now states no comparison on its condition, which tests the default, and `test_join.py` states each comparison on a condition. The README of `mork_rdf`, the sketch's section 2.3, the join addenda of ADR-A18 and ADR-A23 and the pack of SVA-S2h say so. A condition that states a datatype and no comparison reads the datatype nowhere, since it is a term comparison. That is documented and not refused.

## What changed

- **Surface**, from its README: `srf:ExpansionStatement` and `srf:ExpansionSource` with the individuals `srf:ListMembers` and `srf:TransitiveClosure`, and the properties `srf:expandedAs`, `srf:expandsFrom`, `srf:expansionSource` and `srf:membersPath`. Laws `srf:P18` to `srf:P20` with 12 shapes of their own, and `srf:P1` states that an expansion reads its scope from the property it writes. The examples are `bundle-items-expansion-projection.ttl`, a list's members, and `category-ancestors-expansion-projection.ttl`, a transitive closure on candidate evidence. The release note says P18 may invalidate an expansion that states no statement.
- **MORK** gains no term. A shape refuses a join datum that states a comparison or a datatype, which is the removal above.
- **The lowering**, `lowering.py`, `model.py` and a new module `shaclpath.py`: an expansion lowers into a scheme with a source-node root and one assertion of the result property whose `mork:dataRef` is the path, guarded by the required evidence of the instance. `shaclpath.py` reads a SHACL path into a tree, refuses the forms an expansion does not state, and writes the path as the text `mork:dataRef` reads. `srf:producesMapping` is written as for a derivation. No kind keeps the bare mapping any longer, except a kind the layer does not declare.
- **`mork_rdf`**, from its README section 7.11: an assertion with a `mork:dataRef` directly beneath a source-node datum is an expansion. It compiles with the existing assertion case. It gains a check `CollectionEmpty`, information, emits `InstanceExcluded` for the guard on such an assertion, and records an `EngineeringReview` warning that names the path. No mapping kind is added.
- **The addenda** to ADR-A18 and ADR-A23 for this kind are Proposed, beside the earlier ones. The sketch's section 2.4 shows the contract, the scheme and the query as built.

### Names chosen

The index held none of the placeholders (`exists ExpansionStatement`, `expandedAs`, `expandsFrom`, `expansionSource`, `expansionPath`, `ListMembers`, `TransitiveClosure`, `ExpansionSource`, `CollectionEmpty`, `EngineeringReview` and `membersPath` found nothing), so the sketch's placeholders stand. `srf:membersPath` names a path the contract states itself, since the sketch's placeholders had no term for it. `CollectionEmpty` and `EngineeringReview` name the new check and the new finding. The finding is not called `MappingReview`, which is the merge's finding for a join and a keyed construction.

## Choices the sketch did not settle

1. **A path the contract states is a term of its own, `srf:membersPath`, beside the named sources.** The answer says an expansion states its members as a SHACL path and that a list's members and a closure are two named conveniences the lowering writes as paths. It names no property for the path itself. A statement states exactly one of the named source and the path (`srf:P20`), so the path is the selection and no separate switch is needed.
2. **The path reads the property of the evidence binding.** A path that does not name the property the statement expands from is refused (`srf:P20`), so the evidence binding is never decoration and a required binding's guard tests the property the path starts from. A path that reads other properties as well is allowed.
3. **An expansion on candidate evidence is not guarded, and an instance that lacks the property is reported as an empty collection.** A join on candidate evidence says nothing for an instance that lacks the values. The answers say that a missing property is reported as an excluded instance is, which a required binding gives, and an empty collection as information. For candidate evidence they say nothing, and the compiler cannot tell a missing property from an empty collection without reading the path's first step, which an alternative or an inverse does not have. The report is `CollectionEmpty` as information for both.
4. **The compiler raises the engineering review for every assertion with a `mork:dataRef` directly beneath a source-node datum.** It sees a scheme and not the contract, so it cannot tell an expansion from a plain restatement, and a marker in MORK would be a term the answers did not ask for. A hand-written scheme of that shape takes the finding as well.
5. **The finding is a warning.** It follows `MappingReview`. The answers say the finding records that the number of statements depends on the data and names the source, and not a severity.
6. **`sh:zeroOrOnePath` is not a form an expansion states.** The answers list six forms. A path that is at most one node for each instance is no collection.
7. **A guard on the assertion, not on a datum.** A source-node root has no datum beneath it that writes a node, so the guard sits on the assertion that writes the statements, tested on the instance it asserts on.
8. **An existing scenario and two tests changed.** The lowering dependency scenario used an expansion with no statement, which `srf:P18` now refuses, so it states one, and the helper that finds a contract's mapping follows `srf:producesMapping` where it exists. The two tests of the bare mapping use a projection of a kind the layer does not declare, which is the one thing that still lowers to a bare mapping. No other existing test changed beyond Part A's.

## Tests

| ID | Given / When / Then | Level | The break tried | The failure it gave |
|---|---|---|---|---|
| S2i-T1 | both examples, a stated path and candidate evidence / lowered / a scheme MORK's shapes accept | L1 | | |
| S2i-T2 | both examples and the stated path, repeated and in five orders of their triples / lowered / the same graph, and the stated path gives the graph its named source gives | L1 | | |
| S2i-T3 | the bundle example / compiled / the query of the sketch pinned modulo whitespace, one construct, `InstanceExcluded` and `CollectionEmpty`, and one `EngineeringReview` and no other finding | L1 | | |
| S2i-T4 | four bundles on Oxigraph and rdflib / run / a statement for each member of the first and the second, none for the empty list, reported as information, and none for the bundle with no list, excluded and reported with `items` | L1 | the guard removed from the lowering | five tests fail |
| S2i-T5 | a chain of three categories on Oxigraph and rdflib / run / two statements for the narrowest, one for the middle, and the broadest reported as information with the path | L1 | | |
| S2i-T6 | the same bundles / compiled and run / `CollectionEmpty` is information and `InstanceExcluded` a warning, as compiled and as run | L1 | the empty check without the guard on the assertion | five tests fail, a bundle with no list is also reported as empty |
| S2i-T7 | the bundle example on candidate evidence / compiled and run on both engines / no exclusion, four statements, and the bundle with no list reported as empty with the one with an empty list | L1 | | |
| S2i-T8 | each form of a path, a property, a sequence, an alternative, an inverse, zero or more, one or more and nested forms / read and lowered / written in full IRIs, and a path stated as a list's members equals the named source | L1 | | |
| S2i-T9 | an alternative and an inverse path / lowered, compiled and run on both engines / each member the SPARQL path reaches | L1 | | |
| S2i-T10 | a model and a read for each law's breach, such as no statement, a statement on another binding or kind, a result that binds no property, none or two bindings to expand from, a binding that is no evidence or names a second carrier, both a source and a path or neither, a source the choice does not name, `sh:zeroOrOnePath`, an empty blank node, a one-member sequence, a one-member alternative, a node with two forms, a literal, and a path that does not read the property / read / each refused by its law | L1 | | |
| S2i-T11 | the same breaches / validated / each refused by its shape, and the examples and six variants of the path conform | L1 | `ExpansionPathShape` made to fire on nothing | seven tests fail |
| S2i-T12 | the scheme in three orders of its triples / compiled / the same text | L1 | | |
| S2i-T13 | a list that holds one member twice / run on both engines / one statement | L1 | | |
| S2i-T14 | an assertion beneath a datum that mints its node / compiled / no engineering review and no empty check | L1 | | |
| S2i-T15 | the other kinds / read / no expansion statement, and an expansion statement on a join or a derivation is refused | L1 | | |
| S2i-T16 | a join datum that states a comparison or a datatype, and a join condition that states none / validated, compiled and run on both engines / the first refused by `MorkShape` and by `JoinDatumComparison` and writes nothing, the second compared as the same term (Part A) | L1 | | |

## Checks run

| Command | Result |
|---|---|
| `mise run check:python-root` | 308 tests, OK, and the phase 8 conformance passed. The 50 new tests are Surface's expansion tests, beside the 258 before this slice |
| `mise run check:mork-rdf` | 275 passed, 12 more than the 263 of Part A, all in `test_expansion.py` |
| `mise run check:mork` | 464 passed, with no new MORK term and so no new MCN code |
| `mise run check:mork-compilers` | 195 passed, 39 subtests |
| `mise run check:ontology-catalog` | 1319 passed, consistent, the 2 known defects |
| `literate_extract --check` for Surface and MORK | 4 and 3 artefacts consistent |
| `mise run check:identifiers` | passed, 2380 identifiers, 0 unresolved |
| `mise run check:published-decisions`, `check:owl-profile` | passed (6 and 5 tests) |

`check:mork` rewrote `ontology/mork/mtp/data/pins.lock.json`, which was restored, so its pins wait for `mise run build:mtp` at the merge. No version was bumped, so Surface and MORK wait for `mise run version:bump` at the merge, with the earlier slices' changes.

## Left open

- Whether the studio's review requirement acts on `EngineeringReview` or on the contract. It reads only the projection kind today, so an expansion needs that policy to read the finding or the contract before SVA-S2c acts on it, as a join and a keyed construction do.
- The compiler raises the review for every assertion of that shape, so a hand-written scheme that restates a plain property beneath a source-node datum takes the finding. A marker on the scheme that says it is an expansion would be a MORK term, which the answers did not ask for.
- An expansion on candidate evidence reports a missing property as an empty collection, where a join on candidate evidence stays silent (choice 3).
- A closure over a relation that has a cycle makes a node its own ancestor, which SPARQL's path semantics allow. Nothing reports it.
- A path that reads the result property of its own binding is not refused. The compiled query reads only the source, so a run does not feed itself, and a second run over the world after reads the first's statements.
- A node for each member, which combines an expansion with a graph construction, is a slice of its own after this kind (SVA-Q44).
- The index missed the questions this slice asked about how a source-node assertion compiles and about the SHACL path forms, and answered them from the sketch and the mork_rdf README. `mise run graph:ask -- misses --near` at the handoff lists them.

## Placement

T0. Surface, MORK, `mork_rdf` and the two examples are open substrate, and the examples are generic.
