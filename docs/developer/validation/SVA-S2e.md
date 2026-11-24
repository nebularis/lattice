<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-S2e, the projection expression vocabulary and the lowering of a derivation

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-S2e, built on 2026-11-23 and 2026-11-24 in autonomous mode, from the [projection backend sketch](../sketches/projection-backend.md) as the maintainer answered it.

## Invariant

A derivation projection states its operation as a typed expression on its result-target role binding, over evidence role bindings of the same contract, and the lowering carries it across deterministically into a MORK mapping scheme: a root iterating the carrier class with the source-node identity, a reference for each evidence role the expression reads, and an assertion of the result property whose value is the lowered expression. The same contract gives the same graph whatever the order of its triples. MORK's string expressions are unchanged.

## What changed

- **Surface**, from its README: `srf:ProjectionExpression` and its kinds, the four arithmetic operations, a typed literal, rounding to a scale and a choice on a comparison, the six comparison operators, `srf:derivedAs` on the result-target binding, `srf:bindsDatatype` on a role binding, ordered operands, and laws P6 to P9 (one expression on a derivation's result binding and none elsewhere, operands that are expressions or evidence bindings of the same contract, typing, and no cycle), with 19 shapes. The ARR example states its product. The release note says P6 may invalidate a derivation that states no expression.
- **MORK**, from its README: `mork:ValueExpression` and its kinds beside the string algebra, `mork:IdentityRule` with `mork:SourceNodeIdentity`, `mork:valueExpression`, and 20 shapes. MCN gains codes for the new terms, since its coverage test requires one for every term.
- **The lowering**, `tools/surface/src/surface/lowering.py` with `expression.py`: a derivation lowers to a scheme, and every other kind keeps its bare mapping until its slice.
- **Six existing Surface shapes** used `VALUES` inside a SPARQL constraint, which SHACL forbids, so pySHACL could not load the constraints file. Each is rewritten with `FILTER (... IN (...))`, which keeps its meaning.
- **The addenda** to ADR-A18 and ADR-A23, Proposed, for the maintainer to accept.

## Choices the sketch did not settle, put to the maintainer

1. A role binding states its datatype with `srf:bindsDatatype`, and an expression node its result datatype, so a shape can check typing from the contract alone. It restates the property's range, which nothing yet checks against.
2. The numeric datatypes are integer, decimal, float and double with XPath's promotion, a quotient at least decimal, a result's datatype equal to its binding's, and an ordering comparison only between numbers.
3. Rounding is to the nearest with ties toward positive infinity, as SPARQL's `ROUND`, and a negative scale is allowed. A quotient by zero is undefined.
4. Operands are ordered, `leftOperand` and `rightOperand`, where the sketch's placeholder had one unordered property, since a difference and a quotient need an order.
5. The lowered root carries the old bare mapping's parameter bindings and note, and the contract's IRI appears only in that note.

## Tests

| ID | Given / When / Then | Level | The break tried | The failure it gave |
|---|---|---|---|---|
| S2e-T1 | the ARR contract / lowered / a scheme MORK's shapes accept | L1 | | |
| S2e-T2 | the ARR contract, repeated and in five orders of its triples / lowered / the same graph | L1 | | |
| S2e-T3 | an untyped operand, an operand naming the subject or result binding, an unknown IRI or another contract's binding, a choice missing a branch, a wrong datatype, a non-numeric operand, mismatched branches, a cycle, a derivation with no expression, a source-node root stating another identity / validated / each refused | L1 | | |

## Checks run

| Command | Result |
|---|---|
| `mise run check:python-root` | OK, the phase 8 conformance passed |
| `mise run check:mork` | 464 passed |
| `mise run check:mork-rdf` | 103 passed |
| `mise run check:mork-compilers` | 195 passed |
| `mise run check:ontology-catalog` | 1319 passed, consistent, the 2 known defects |
| `mise run check:owl-profile` | 5 passed |
| `literate_extract --check` for Surface and MORK | consistent |
| `mise run check:identifiers`, `check:published-decisions` | passed |
| `mise run check:ontology-versioning -- --base-ref main` | names Surface and MORK as unbumped, with persistence from earlier slices, bumped at the merge. Run by the delegated developer |

Each but the last was run by the delegated developer and again by the reviewer. `check:mork` rewrites `ontology/mork/mtp/data/pins.lock.json`, which was restored, so its pins wait for `mise run build:mtp` at the merge.

## Placement

T0. Surface, MORK and their compilers are open substrate.
