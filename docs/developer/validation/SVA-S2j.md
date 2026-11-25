<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-S2j, a node for each member of an expansion

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-S2j, built on 2026-11-25 in autonomous mode, from the [projection backend sketch](../sketches/projection-backend.md) as the maintainer answered SVA-Q50 to SVA-Q56 on 2026-11-25. The same session first renamed the review findings by the projection kind they review, which the maintainer decided on 2026-11-25, and recorded the derivation's review. That is Part A below, and the slice is Part B.

## Invariant

An expansion projection may state a constructed node on its result-target role binding beside its expansion statement, and the node is made for each member the expansion reaches. The contract states the identity, one node for each instance and member, one for each value of a key whose parts are the instance's required-evidence bindings and the member, or the member itself as the node. It lowers deterministically into a mapping scheme whose contextual datum states the expansion's path as `mork:memberRef`, which `mork_rdf` compiles with the member bound once, so that the identity, the link and each value read the same one. A member that has no name to spell is reported and skipped while the instance's other members are written, and the review findings each part carries are recorded.

## Part A, the review findings named by projection kind

The maintainer decided on 2026-11-25 that the findings are named by the kind they review, since ADR-A41's "engineering review" named who reviews and not what. `EngineeringReview`, raised for an expansion, is `ExpansionReview`. A compiled derivation, which ADR-A41 asks an engineering review of and which recorded none, records `DerivationReview`, a warning on the assertion that names the property it writes. `MappingReview` stays for a join and a keyed construction.

- **`mork_rdf`.** `compile.py` raises the two findings, `run.py` names no finding and is unchanged in Part A, and the README names them in sections 5.1, 7.8, 7.11 and 10.1 and in MR-26 and MR-28.
- **Surface's README** and the **sketch** name `ExpansionReview` and `DerivationReview` where they named the finding. The accepted addenda to ADR-A18 and ADR-A23 name `ExpansionReview` where they named it. ADR-A41 gains a Proposed addendum that records its engineering review as `DerivationReview` for a derivation and `ExpansionReview` for an expansion, and its mapping review as `MappingReview`.
- **The Validation Packs** of SVA-S2e, SVA-S2f and SVA-S2i gain a dated follow-up note.
- **Tests.** The expansion tests of `mork_rdf` and Surface expect `ExpansionReview`. The compile test of the ARR scheme expects the one `DerivationReview` where it expected none, and the test of each operation allows it as the one warning.
- **Not changed.** The workers' review policy (`projection_policy.py`) and the contracts under `contracts/` name `engineering_review` and `mapping_review` as a requirement the studio reads, which is the studio slice's, SVA-S2c, and the Technical Inspector's text.

## What changed

- **Surface**, from its README: `srf:MemberNode`, an individual of `srf:IdentityChoice`, and the properties `srf:keyMember`, `srf:memberName` and `srf:fromMember`. Laws `srf:P22` to `srf:P25`, with 3 new shapes and 4 changed, and `srf:P10`, `srf:P11`, `srf:P12` and `srf:P18` relaxed to say that a construction and an expansion are stated together only on one binding, that a key may be the member and that a written value may be the member. `srf:P1` says the node's class gives the scope. The example is `bundle-line-construction-projection.ttl`.
- **MORK**, from its README: `mork:memberRef`, `mork:memberName`, `mork:dataMember`, `mork:MemberExpression` and `mork:MemberIdentity`, with `mork:MemberDatumShape` and `mork:MemberPlacementShape`, and the shape of the source-node identity now states its rules for that identity alone and allows the second. The MCN codebook and its document gain a code for each (`EM`, `mrf`, `mnm`, `dmb` and `.mem`).
- **The lowering**, `lowering.py` and `model.py`: an expansion that states a construction lowers into the construction's scheme with the path as `mork:memberRef`, a template that ends in a `mork:MemberExpression` where the key states the member, no template for a node for each instance and member, `mork:MemberIdentity` for the member as the node, `mork:memberName` for a stable name and `mork:dataMember` for a value from the member.
- **`mork_rdf`**, from its README section 7.12: a contextual datum that states `mork:memberRef` binds the member once in its own frame. It gains the checks `MemberUnnamed` and `MemberNotIri`, reads `CollectionEmpty` and `ClosureCycle` for its path (the compiler's checks of an expansion moved to one method both cases call), groups `IdentityAmbiguous` by the focus node and the member, and reads `ValueDisagrees` for a node whose identity reads the member. It records `ExpansionReview`, and `MappingReview` where the identity reads the member without the focus node or the member is the node.
- **The addenda** to ADR-A18 and ADR-A23 for this case are Proposed, beside the earlier ones. The sketch's section 2.5 shows the contract, the scheme and the query as built.

### Names chosen

`exists` and `find --kind term` found none of `memberRef`, `memberName`, `dataMember`, `MemberExpression`, `MemberIdentity`, `MemberNode`, `keyMember`, `fromMember`, `MemberUnnamed` and `MemberNotIri`, and `find` for the member of a collection found only `CollectionElement`, a different meaning. `srf:membersPath` is the expansion's own path and is a different term from `mork:memberRef`, which a datum states, and the two are in different namespaces.

## Choices the sketch did not settle

1. **Five MORK terms and not one.** The answer to SVA-Q56 names one term that binds the member once. `mork:memberRef` is that term. The other four follow from SVA-Q53 to SVA-Q55, a term that reads the member in an identity template, one that writes it as a value, the property that names it and the identity that makes it the node.
2. **A literal member is spelled with its lexical form and, where its datatype is not `xsd:string`, the datatype after two carets.** The answer says "as a key part is elsewhere", and a key part in `mork_rdf` spells the lexical form alone. A string stays plain so a stable name such as a code is spelled as it is, and the integer 7 and the string "7" are two names. A language tag is not spelled.
3. **The member as the node takes `MappingReview`.** SVA-Q56 says `MappingReview` where the node is keyed. The member as the node is not a key, and it merges the instances that share a member and writes on a node the source names, so the compiler raises it where the identity reads the member.
4. **A blank node is a blank node or a skolem IRI.** The run names a source's blank nodes by the skolem rule, so a blank member reaches an Oxigraph run as an IRI. The filter reads the skolem prefix `mork_rdf` writes as well as `isBlank`, so the report is the same on both engines.
5. **`MemberNotIri` is the code for the member as the node.** The answer says only that a literal or blank member is reported. A member without the named value is `MemberUnnamed` even where it is a literal.
6. **The datum's checks follow an expansion's and a construction's.** `InstanceExcluded` is the construction's, `CollectionEmpty` and `ClosureCycle` are the expansion's and are emitted over the datum's path. `IdentityAmbiguous` groups by the focus node and the member, since a focus node gives one node for each member. `ValueDisagrees` is read where the identity reads the member without the focus node.
7. **The join that writes a member's property is a test.** It links each line to the record that holds the property (`ex:ItemRecord`, `ex:recordOf`) and not to the member, since a join compares a value and the member's own IRI is not a property value. The test is in Surface's compilation tests, and the README says that a join models it where it is wanted.
8. **Two shapes moved, and one existing test with them.** The shape of the source-node identity said its rules for any identity rule, which a member identity cannot satisfy, so it says them for that identity alone. The shape of a written value no longer requires a binding, since a value may name the member, and a new shape states that a value names exactly one of the two. The test that expects a value with no binding to be refused now expects the new shape. No other existing test changed beyond Part A's.

## Tests

| ID | Given / When / Then | Level | The break tried | The failure it gave |
|---|---|---|---|---|
| S2j-T1 | the example and the five other choices of identity (a node for each instance and member, a key without the member, the member alone, the member as the node, a stable name) / read / each parses with its key, its member flag, its name and its values | L1 | | |
| S2j-T2 | the same six / validated against Surface's shapes and, lowered, against MORK's / each conforms, and the other kinds still conform | L1 | | |
| S2j-T3 | the same, repeated and in five orders of their triples / lowered / the same graph | L1 | | |
| S2j-T4 | the example / lowered / the datum states the path as `mork:memberRef`, the guard names both required values, the template ends in a member expression after the code, and the values are a reference and `mork:dataMember` | L1 | | |
| S2j-T5 | each choice / lowered / no template for a node for each instance and member, a template of the stem and the member for the member alone, `mork:MemberIdentity` and no template, name or member name for the member as the node, and `mork:memberName` for a stable name | L1 | | |
| S2j-T6 | the example / compiled / the query of the sketch pinned modulo whitespace, three constructs, seven checks, and `ExpansionReview` and `MappingReview` and no other finding | L1 | | |
| S2j-T7 | four bundles on Oxigraph and rdflib / run / a line for each member of the first and the second, none for the empty list, reported as information, and none for the bundle with no list, excluded and reported | L1 | | |
| S2j-T8 | a node for each instance and member / compiled and run on both engines / one node for each pair, a member two bundles hold gives two, and `ExpansionReview` alone | L1 | | |
| S2j-T9 | a key of the code alone and a key of the member alone / run on both engines / the first writes every member on the node of the code, and the second shares the node of an item two bundles hold, whose two codes are reported by `ValueDisagrees` | L1 | | |
| S2j-T10 | the member as the node / run on both engines / the items typed, linked and written on and nothing minted, and a literal and a blank member reported by `MemberNotIri` and skipped while the item beside them is written | L1 | | |
| S2j-T11 | a stable name / run on both engines / the name spelled in place of the member, escaped, and a member without it reported by `MemberUnnamed` and skipped while the others are written, and a blank member that holds a name named by it | L1 | | |
| S2j-T12 | a blank member among others, and literal members of two datatypes / run on both engines / the blank member reported and skipped, the others written, and the integer 7 and the string "7" are two nodes | L1 | | |
| S2j-T13 | a join over the constructed lines and the records of their items / compiled and run on both engines / a link for each line whose item has a record, and no property of the member copied | L1 | | |
| S2j-T14 | a model and a read for each law's breach, such as a key of no part, a node for each instance or the member itself that names a key part, the member itself that names a member name, a value that names a binding and the member or neither, a member term on a graph construction, a graph construction that states an expansion, a construction on another kind, and a key member that is false or stated twice / read and validated / each refused by the analyser and by its shape | L1 | | |
| S2j-T15 | the example and the other kinds / the same scheme in three orders of its triples, the same graph on a repeat and with the source's triples permuted on both engines / the same text and the same graph | L1 | | |
| S2j-T16 | `mork_rdf`'s own fixture, `line-mapping.ttl`, and its variants / compiled and run / the same cases as T6 to T12 from the scheme without Surface, and the refusals named, `NoGluingProperty`, `MemberIncomplete` (a root that mints and a member node that names itself), `IdentityRuleUnknown`, `MemberValueIncomplete` and `MemberOutside` | L1 | | |
| S2j-T17 | the compiled scheme of the ARR example and each operation / compiled / `DerivationReview` and no other warning (Part A) | L1 | | |

## Checks run

| Command | Result |
|---|---|
| `mise run check:python-root` | 356 tests, OK, and the phase 8 conformance passed. The 43 new tests are Surface's member tests, beside the 313 after Part A |
| `mise run check:mork-rdf` | 331 passed, 44 more than the 287 of Part A, all in `test_member.py` |
| `mise run check:mork` | 464 passed, with the five new MCN codes in the codebook and its document |
| `mise run check:mork-compilers` | 195 passed, 39 subtests |
| `mise run check:ontology-catalog` | 1319 passed, consistent, the 2 known defects |
| `mise run check:owl-profile` | 47 documents, 5 known findings, none new, and 5 tests passed |
| `literate_extract --check` for Surface and MORK | 4 and 3 artefacts consistent |
| `mise run check:identifiers` | passed, 2387 identifiers, 0 unresolved |
| `mise run check:published-decisions` | passed (6 tests) |

Part A's own run, before Part B, was `check:mork-rdf` 287 passed, `check:python-root` 313 tests OK with the phase 8 conformance, and `check:published-decisions` 6 passed. `check:mork` rewrote `ontology/mork/mtp/data/pins.lock.json`, which was restored, so its pins wait for `mise run build:mtp` at the merge. No version was bumped, so Surface and MORK wait for `mise run version:bump` at the merge, with the earlier slices' changes.

## Left open

- Whether the studio's review requirement acts on `ExpansionReview`, `DerivationReview` and `MappingReview`, which SVA-S2c decides. It reads only the projection kind today, and the workers' policy and the contracts under `contracts/` still name `engineering_review` and `mapping_review`.
- A blank member that carries a stable name and is written by `srf:fromMember` copies a blank node into the output. No test shows it, and a contract that needs it decides.
- A language tag on a literal member is not spelled, so two members that differ only by tag share a name.
- A key that reads the member of a list is spelled into an identifier, as any key is, and Surface cannot check that the member's text is stable.

## Placement

T0. Surface's projections, MORK and `mork_rdf` are open substrate, and the bundle example is generic.
