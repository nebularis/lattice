<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H2.1, the typed operation IR and its renderer

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice H2.1 of the
[typed IR sketch §7](../sketches/formal-methods-track-h-typed-ir.md#7-slices), under
[ADR-A123](../../architecture/decisions/ADR-A123-typed-operation-ir.md) (accepted 2026-10-10).
**Decisions needing confirmation:** the four below were confirmed by the maintainer on 2026-10-10. Two questions
from the review remain, under "Review, 2026-10-10".

## Invariant

An operation that the types of `persistence.ir` forbid is never rendered. Each hazard of the
[specification sketch §3](../sketches/formal-methods-track-h-specification.md#3-the-typed-intermediate-representation)
is a named refusal, and any value that is accepted renders deterministically to SPARQL that parses as exactly one
operation, whatever literal or IRI an adopter supplies (ADR-A79 point 5, ADR-A123 decision 2).

## What changed

- `persistence/ir.py`: the values. `Operation`, `Param` with a `Kind`, the terms (`Var`, `ParamRef`, `Const`), `Graph`
  with a mandatory `GraphRole`, `GraphBlock`, the pattern forms (`Optional_`, `NotExists`, `Bind`, `Filter`,
  `Values`, `Union_`, `Group`), the expressions (`Func`, `Op`, `Not`, `TermGuard`, `ValueGuard`), `Select`, and the
  derived `ParameterGuard`. A `Const` takes only an `Iri`, `Literal` or `Integer` from `terms.py`, so a bare string
  or a blank node cannot be built.
- `persistence/ir_render.py`: `check` (the 26 refusals of `RULES`), `render`, and `access_sets`, which derives the
  graphs and subjects read and written from the same walk. Nothing in `compile`, `instantiate` or the templates
  calls either module yet. The builders arrive in H2.2 to H2.5.
- `persistence/namespaces.py`: `PAT`, the patterns vocabulary the templates declare as `pat:`.
- **`persistence/terms.py`, a defect fix outside the slice's module list** (decision 1 below). `Literal.encode` wrote a
  literal containing a backslash before `u` or `U` so that SPARQL's whole-text `\u` escape processing mangled it.
- Tests: `test_ir.py`, `test_ir_render.py`, `ir_fixtures.py`, a pinned rendering in `fixtures/ir/`, and two cases in
  `test_terms.py`. The README describes the IR and marks it unused.

## Decisions needing confirmation

1. **`Literal.encode` changed.** The H2.1 property test T21 found that a literal value such as `A` is encoded as
   `"\\u0041"`, and rdflib's preprocessing of `\uXXXX` escapes then turns it into a syntax error. SPARQL 1.1 §19.2
   defines the preprocessing over the whole query text, so a conforming engine may do the same. The fix writes the
   `u` of such a pair as its own escape and the hex digits after it as escapes (rdflib reads up to eight digits after
   `\u`). Every previous encoding is unchanged. This touches the injection boundary of ADR-A79 point 4, so it is
   listed here for your review, not folded in silently. The corpus in `test_terms.py` still passes.
2. **Comparisons are guards, and a value comparison needs a declared kind.** An `Op` cannot compare. A
   `ValueGuard` on a term-matched `Var` or `Param` is refused unless its `kind` is `Iri`, so a builder declares
   `Compare.VALUE` on a position it reads through `FILTER` (the fence, the gap scan's `seq`). This is how the brief's
   "a position is declared term-invariant or value-compared" is made checkable. An undeclared variable counts as
   term-matched.
3. **Rules beyond the hazard table.** `UnboundGraphVariable` (a `GRAPH ?g` in `WHERE` must follow the `BIND` or
   `VALUES` that binds `?g`, the "unbound `GRAPH ?g`" row), `BindTargetInScope` (a SPARQL error that rdflib does not
   raise), `UnusedParameter` and `NameCollision` (a variable named as a parameter). Each fires on a mistake a builder
   could make in H2.2 to H2.5.
4. **Not built, left to the slice that needs it.** A sub-select (`key-claim-merge-rewrite`, H2.5), `UNION` with
   `VALUES` for the payload (R2 of the brief, a change and not a port), and Position width rendering (the append
   template pads in the query text).

**Confirmed 2026-10-10.** The maintainer accepted all four as written: the `Literal.encode` fix, comparisons as
guards with a declared kind for a value comparison, the rules beyond the hazard table, and what is left to later
slices.

## Review, 2026-10-10

A review of the slice before acceptance found five defects. The maintainer agreed F2, F3 and F5, the corrected F4, and F1 in the revised form of the ADR-A123 addendum of 2026-10-12, which also settles R1 and R2.

| # | Defect | Effect | Fix | Test |
|---|---|---|---|---|
| F1 | the required-parameter guard rendered as a top-level `FILTER`. A `FILTER` applies after its group's patterns, so a missing `$root` was bound from the data by `$root pat:seq $expectedSeq` | **a replace with no `$root` wrote every aggregate whose version row matched** (shown on rdflib with two aggregates). T16 to T18 missed it because their bootstrap operation names its target only in the `INSERT` | the guard is its own group, `{ FILTER(...) }`, first in `WHERE`. ADR-A123 decision 5 says so, corrected before acceptance | T25, T25b, T15 rewritten, T13's pinned text |
| F2 | prefix compaction rewrote every `<...>` in a constant's text, including inside a literal | a literal whose value looked like a `pat:` or `xsd:` IRI was silently changed | only an `Iri`, and a literal's datatype, are compacted | T26 |
| F3 | an optional parameter counted as bound in every solution | a `BIND` over an optional parameter fed a `Bound` template variable, a partial write when the caller left it out | only a required parameter counts as bound | a new `UnboundTemplateVariable` case in T4 |
| F4 | the checker let a `BIND` inside a nested group, a `UNION` branch or an `OPTIONAL` see variables bound outside it. SPARQL evaluates an inner group on its own and joins it afterwards (checked on rdflib, T29), so only `NOT EXISTS` sees them. The review first got this backwards and changed the `GRAPH` block, which was right, and that change is reverted (2026-10-12) | a builder could tag `Bound` a variable that is unbound at run time, a partial write, and a `GRAPH ?g` in an inner group after an outer `BIND ?g` passed, though it scans every graph | those three inner scopes start empty, and `NOT EXISTS` keeps the enclosing one | three new cases in T4, T29, T29b |
| F5 | `Const` and `Path` accepted a term built without its encoder, if it looked well formed. The IRI form allowed a backslash | `Const(Iri("<urn:x\u003E>"))` was accepted, and `\u` escapes are processed over the whole query text, so it could close the IRI | the IRI form refuses exactly what `Iri.encode` refuses, and a `Path` must have the form of an encoded path | two new `UnencodedConstant` cases in T4 |

Also removed: two unused parameters of the walk (`top`, `indent`), one that changed nothing (`in_graph`), a set that was
written and never read (`var_names`), and a function-local import.

**R1 and R2, settled 2026-10-12** by the [ADR-A123 addendum](../../architecture/decisions/ADR-A123-typed-operation-ir.md#addendum-2026-10-12-parameter-guards-are-optional-and-are-type-tests).
Guards are optional and on by default. An operation carries the derived guard or `GUARDS_OFF`, and `check` refuses
one with neither (R1). The guard is a type test per parameter, `isIRI` for an `Iri`, which also catches a missing
parameter and survives text substitution (R2). The compile flag, its `dal:` term and its `INFO` diagnostic land in
H2.2, H2.7 and H2.8.

Not changed, recorded for the slices that meet them: an optional parameter used directly in a template triple is
not tagged and can be skipped silently (no shipped template has one), and `NOW()` reaching a guard through a pattern,
such as `FILTER NOT EXISTS { GRAPH ?logGraph { ... } }` with a clock-derived `?logGraph`, is not `ClockInGuard`.

## Test cases

In `tools/persistence/tests/test_ir.py`, `test_ir_render.py` and `test_terms.py`.

| ID | Given / When / Then | Level | Invariant | +/- |
|---|---|---|---|---|
| H2.1-T1 | the base replace-shaped operation / checked / accepted, and it renders | L1 | the refusals vary one accepted value | + |
| H2.1-T2 | the refusal table / compared with `RULES` / every rule has a refusal test | L1 | no rule is unwitnessed | + |
| H2.1-T3 | the source / every `IrError` rule name / is in `RULES` | L1 | no rule is unlisted | + |
| H2.1-T4 | 55 invalid values, one or more per rule (bare string, blank node, unescaped literal, missing role, bare triple, path in a template, untagged and mistagged variables, free `GRAPH ?g`, wrong guard, `NOW()` in a guard directly and through one or two `BIND`s, guard not derived, slot misuse, unknown function and operator, aggregate outside `SELECT`, and the rest) / built and checked / `IrError` carrying that rule | L1 | one refusal per type rule | − |
| H2.1-T4b | the 44 of them that are operations / `render` / refused with the same rule | L1 | `render` cannot bypass `check` | − |
| H2.1-T5 | a property path in `WHERE` / checked / accepted, marked as a closure read | L1 | paths are read-only | + |
| H2.1-T6 | guards that match their position / checked / accepted | L1 | the refusal is not blanket | + |
| H2.1-T7 | a `GRAPH ?log` after `VALUES` with a registry slot / checked / accepted | L1 | audits stay expressible | + |
| H2.1-T8 | an operation / its guard / equal to the derived guard, and with `GUARDS_OFF` it renders none | L1 | the harness renders with guards off | + |
| H2.1-T9 | an optional parameter / guarded / it is not | L1 | only required parameters are guarded | + |
| H2.1-T10 | 11 forms (replace, no guard, insert only, no required parameter, property path, union, nested group, term and value guards, registry audit with every aggregate, value audit, every function) / rendered, parsed and translated by rdflib / one operation each | L3 | every renderable form is SPARQL | + |
| H2.1-T11 | the forms / rendered text / every function and aggregate of the supported set appears | L1 | no supported construct is unparsed | + |
| H2.1-T12 | an operation with a payload slot / rendered / the slot is `{{{payloadTriples}}}`, parameters are `$name` | L1 | an unrendered slot fails closed | + |
| H2.1-T13 | the base operation / rendered / byte-identical to `fixtures/ir/base-operation.rq` | L3 | the text is pinned | + |
| H2.1-T14 | an operation / rendered twice / identical, one prefix declaration each | L2 | determinism | + |
| H2.1-T15 | an operation with and without the guard / rendered / differ by exactly one group holding one `FILTER`, first in `WHERE` | L3 | the harness comparison of the brief §7.1 | + |
| H2.1-T16 | a bootstrap-shaped operation with every parameter bound, run on rdflib / executed / the whole record is written | L4 | the guard admits a good request | + |
| H2.1-T17 | no target, no epoch, epoch as `xsd:integer`, epoch as a string, target as a literal / executed / nothing is written | L4 | a missing or mistyped parameter is no write (TD-34, R2) | − |
| H2.1-T18 | the same operation without the guard and no epoch / executed / part of the record is written | L4 | shows what the guard prevents | − |
| H2.1-T19 | the base operation / `access_sets` / reads and writes by role and subject, the payload as a write, no read of the log graph | L1 | derived sets | + |
| H2.1-T20 | 150 seeded random valid operations / rendered / deterministic, parsed and translated as exactly one operation | L2 | validity by construction renders | + |
| H2.1-T21 | 100 seeded adversarial strings as literals / rendered and executed on rdflib / the stored object equals the string | L8 | a literal stays a literal | + |
| H2.1-T22 | 100 seeded adversarial strings as IRIs / refused, or rendered and executed / the stored object equals the IRI | L8 | an IRI stays an IRI | + |
| H2.1-T23 | eight literals with a backslash before `u` or `U` / encoded, executed on rdflib / round-trip | L8 | decision 1 | + |
| H2.1-T24 | `A` / encoded / the text holds no `\u` escape the value did not hold | L1 | decision 1 | + |
| H2.1-T25 | a replace-shaped operation over two aggregates, `$root` left out / executed on rdflib / nothing written, and with `$root` bound only that aggregate moves | L4 | review F1 | − |
| H2.1-T25b | the same without the guard / executed / both aggregates move | L4 | shows what F1 prevents | − |
| H2.1-T28 | the replace-shaped operation with its parameters substituted as text, `$root` substituted or left as text / parsed and executed on rdflib / one operation, and only the named aggregate moves, or none | L4 | ADR-A123 addendum point 2 | + |
| H2.1-T29 | a `BIND` over an outer variable in a nested group, `GRAPH` block, `OPTIONAL`, `UNION` branch and the same group / run on rdflib / unbound in the first four, bound in the last | L4 | review F4: the checker's scope is the engine's | + |
| H2.1-T29b | `NOT EXISTS` over an outer variable / run on rdflib / it sees it | L4 | review F4 | + |
| H2.1-T30 | an operation built with guards off / rendered / no guard, one operation, and it says it is off | L1 | addendum point 1 | + |
| H2.1-T26 | a literal whose value is a `pat:` IRI in angle brackets, and a typed literal / rendered and executed / the value is unchanged, the datatype compacted | L4 | review F2 | + |

## One command

Run from the repository root. A pass is `1875 passed, 1 xfailed` (1,876 collected on 2026-10-12, not yet run). The
slice as first delivered passed at `1849 passed, 1 xfailed`. The review and the addendum add 26 cases and remove none:
14 in `test_ir.py` (eight refusals, six of them also in T4b) and 12 in `test_ir_render.py`. The previous total,
before the slice, was `1360 passed, 1 xfailed`.

```bash
mise run check:persistence
```

## Artefacts to inspect

- `tools/persistence/src/persistence/ir.py` and `ir_render.py`. Read `RULES` first.
- `tools/persistence/tests/fixtures/ir/base-operation.rq`, the first rendered operation.
- `tools/persistence/tests/test_ir.py`, the refusal table `_refusals`.

## Adversarial probe

Run on 2026-10-10, restored afterwards. Each mutation is to the implementation, and the named case fails.

| Mutation | Result |
|---|---|
| the encoded-form test of `Const` removed | `UnencodedConstant` blank-node-as-`Iri` fails |
| the guard never rendered | T8 fails |
| the `NOW()` check on guards disabled | the `ClockInGuard` through-a-`BIND` case fails |
| `Literal.encode` returned to the old escaping | T21 seed 6 fails |
| the free-`GRAPH ?g` check removed | the `UnboundGraphVariable` case fails |
| an optional variable counted as definitely bound | T1 fails, since the base operation tags `?prevRev` `OptionalAllowed` |
| the value-comparison check on term-matched positions removed | the `WrongGuard` case fails |
| the path-in-template check removed in one of its two places | not detected, and correctly so, since `_node` refuses a path predicate outside `WHERE` too. The check was kept in one place. With both removed, four `PathOutsideWhere` cases fail |

## Deliberate non-coverage

- Equivalence with the templates. The harness is H2.2, with the first ports.
- The compiled profile's declarations (parameters, sets, payload contract). H2.6 and H2.7.
- The payload type, its digest and its boundary check. H2.8.
- A second SPARQL engine. T10, T20 to T22 use rdflib only. Oxigraph comes in H2.4.
