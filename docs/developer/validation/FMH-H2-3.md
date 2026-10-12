<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H2.3, the named-graph row writers

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice H2.3, planned in
[plan §4.1](../plans/formal-methods-track-h.md#41-h23-the-named-graph-row-writers-planned-2026-10-12) under
[ADR-A123](../../architecture/decisions/ADR-A123-typed-operation-ir.md) and its two addenda of 2026-10-12. One slice
beyond the sizing rule, by the maintainer's approval (H-D21).
**For countersignature (non-weakening rule):** two items, below. **Open decisions:** none.

## Invariant

The four named-graph operations, `create-if-absent`, `cas-replace`, `tombstone-delete` and `unconditional-write`, each with
its dataset-guard variant where it has one, render the query their templates do (apart from the guard), a request with a
missing or mistyped parameter writes nothing, and a caller that names the root's graph itself cannot write into any graph but
the one the naming rule gives.

## What changed

- **Seven templates ported** in `builders.py` (create, replace and tombstone with their dataset-guard variants, and the unconditional write), 11 builders in all with H2.2's. The harness
  now compares 90 operations, every one equal to its template.
- **The scope rule (H2.3-Q2).** `UnboundGraphVariable` accepts a `GRAPH ?g` in an inner group when an enclosing group has
  bound `?g` before it. A `BIND` still sees nothing of the enclosing group. An engine test (T2) shows rdflib returns only
  `?g`'s triples for an `OPTIONAL`, a nested group and a `UNION` branch.
- **`Param.equals`** (ADR-A123, second addendum, and the maintainer's direction of 2026-10-12). A parameter can declare an
  expression it must equal. `ParameterGuard.derive` emits `sameTerm($p, expr)` after the parameter's type test, `check` runs
  every `equals` through the guard-expression checker (`ClockInGuard`, `UnknownFunction`, `WrongGuard`,
  `UndeclaredParameter` apply), and `GUARDS_OFF` drops it with the type tests. A builder never passes guard conjuncts.
  A new rule, `InvalidEquals`, refuses an `equals` on an optional or slot parameter or one that names a variable (the guard
  group binds none).
- **The caller-named graph.** `build(..., graph_names="caller")` declares `$g` with `equals` the naming rule of ADR-A122
  decision 8 and writes `GRAPH $g` for `?g`. `persistence instantiate --caller-graph-names` selects it, until H2.7 records the
  choice in the compiled profile. It changes only the operations that name a graph.
- **Roles written down apart from the table.** A probe that swapped the metadata and transaction roles in `GRAPH_ROLES` was
  not caught, since the existing role test asks the table for the answer. T32 states each graph's role independently.
- `cas-replace-value-guard` is not ported (TD-43, H2.3-Q1). `$assertGraph` and `$retractGraph` stay optional (H2.3-Q3).
  TD-34's row lists the operations done.

### For countersignature

1. **A refusal case removed from `test_ir.py`:** "GRAPH ?g in an OPTIONAL after an outer BIND of ?g" (`UnboundGraphVariable`).
   H2.1 added it, and the planning of H2.3 found it wrong in intent (plan §4.1, fact 1). It is replaced by three refusals
   that still hold, a `GRAPH ?g` in an `OPTIONAL` or a `UNION` branch that nothing binds, and one bound only after the group
   that uses it, and by three accepted cases (T1) with the engine test (T2).
2. **A test input changed in `test_graph_naming.py`** (HO8-T1, T2, T2b). They bound `$epoch` as an `xsd:integer`, which
   the README says is a different term and never matches. The create now carries the parameter guard, which refuses it, so
   the input is `xsd:long`. The assertions are unchanged.

## Test cases

In `test_named_graph_builders.py` unless noted. The harness cases (H2.2-T1 to T6) now run over the new stems, and T6 over both
graph-naming forms.

| ID | Given / When / Then | Level | Invariant | +/- |
|---|---|---|---|---|
| H2.3-T1 (`test_ir.py`) | `?g` bound by an enclosing `BIND`, used in an `OPTIONAL`, a nested group, a `UNION` branch / checked / accepted | L1 | the Q2 rule | + |
| H2.3-T2 (`test_ir_render.py`) | the same three shapes over two graphs on rdflib / executed / only `?g`'s triples | L4 | the rule follows the engine's join | + |
| H2.3-T3 | a create / executed / the payload is in the root's own graph, a row at `seq 1` with head, the claim, a receipt | L4 | the port behaves | + |
| H2.3-T4 | a second create of the root / executed / nothing changes | L4 | create-if-absent | + |
| H2.3-T5 | a create with no root, with and without the guard / executed / guarded writes nothing, unguarded writes a claim and no row, payload or named graph | L4 | TD-34, `NOT EXISTS` with an unbound root | − |
| H2.3-T6 | the dataset-guard create / dataset epochs 3 and 4 / writes only on a match | L4 | dataset guard | + |
| H2.3-T7 | an unconditional write / executed / the payload is in the root's graph and nowhere else | L4 | the port behaves | + |
| H2.3-T8 | a literal root, and no root / executed with and without the guard / guarded writes nothing, unguarded builds a graph name from the literal's text, and rdflib writes a root-less write into a blank-node graph | L4 | `isIRI($root)` on a literal root | − |
| H2.3-T9 | a replace / executed / exactly the payload remains and the row moves | L4 | replace | + |
| H2.3-T10 | a replace at the wrong `seq` / executed / nothing | L4 | compare-and-set | − |
| H2.3-T11 | the first replace after a create / executed / the receipt chains to the create | L4 | an unbound `OPTIONAL` variable skips only its own triple on the first revision | + |
| H2.3-T12 | a replace without and with `$assertGraph` and `$retractGraph` / executed / the receipt has the two triples only when given | L4 | H2.3-Q3 | + |
| H2.3-T13 | a replace of one root / executed beside another / the other's graph is unchanged | L4 | the join on `?g` restricts the sweep | + |
| H2.3-T14 | a replay / executed / nothing changes | L4 | retry is a no-op | + |
| H2.3-T15 | a replace under the dataset guard after the dataset epoch moved / executed / the row's epoch is rebased | L4 | `?rowEpoch` | + |
| H2.3-T16 | a replace with no root over two aggregates / executed with and without the guard / guarded writes nothing, unguarded replaces both at that `seq` | L4 | the guard before any pattern can bind `$root` | − |
| H2.3-T17 | a tombstone / executed / the graph is empty, the row is deleted at `seq 2`, the receipt is a deletion with cause and actor | L4 | tombstone | + |
| H2.3-T18 | a replace after a tombstone, and a replay of the tombstone / executed / nothing changes | L4 | a deleted row is final | − |
| H2.3-T19 | a tombstone under the dataset guard / dataset epochs 4 and 3 / writes only on a match | L4 | dataset guard | + |
| H2.3-T20 | a tombstone missing each of five parameters / executed / nothing is written | L4 | every required parameter is guarded | − |
| H2.3-T21 | a replace with the right `$g` / executed / equals the default form's result | L4 | the override changes the naming, not the result | + |
| H2.3-T22 | create, tombstone and unconditional write with the right `$g` / executed / equal to the default form | L4 | as T21 | + |
| H2.3-T23 | a wrong `$g` (another name, an unencoded root, a literal) / executed / guarded writes nothing, unguarded writes into the named graph | L4 | the guard checks the name, and without it the caller must | − |
| H2.3-T24 | a replace with the graph of another root as `$g` / executed / the stored aggregate is untouched | L4 | a wrong `$g` cannot sweep another aggregate | − |
| H2.3-T25 | the caller-named replace with every parameter's text substituted / executed with no initial bindings / `GRAPH <iri>` in the text, the same result | L4 | a text-substituting caller | + |
| H2.3-T26 | the caller-named replace / the guard line / `ISIRI($g)` then the `equals` conjunct computed from the parameter list, dropped with guards off | L3 | the guard is derived from the parameter | + |
| H2.3-T27 | the caller-named write / its text / `sameTerm($g, IRI(CONCAT(prefix, ENCODE_FOR_URI(STR($root)), suffix)))` | L3 | the naming rule is the one of decision 8 | + |
| H2.3-T28 | the append and bootstrap builders, and an unknown `graph_names` / built / unchanged, and refused | L1 | the option changes only the operations that name a graph | + |
| H2.3-T29 | the default and caller-named replace / rendered / equal to the two golden files, and differing in the 9 listed lines only | L3 | the golden `.rq` diff | + |
| H2.3-T30, T31 | a compiled profile / `instantiate` and the command line with the flag / the caller-named form | L3 | the flag works | + |
| H2.3-T32 | every graph of every ported operation / its role / equals the role its name says, from a table apart from `GRAPH_ROLES` | L3 | roles are right by an independent statement | + |
| `test_ir.py` | `equals` on an optional parameter, on a slot, naming a variable / checked / `InvalidEquals`. `NOW()` in an `equals` / `ClockInGuard`. An undeclared parameter in it / `UndeclaredParameter` | L1 | the `equals` check is an expression check | − |

### The golden diff (T29)

`fixtures/ir/replace-named-graph.rq` and `replace-named-graph-caller.rq`. The caller-named form differs from the default in
nine lines. The sweep and payload blocks and the `OPTIONAL` sweep read `GRAPH $g` where they read `GRAPH ?g`. The
`BIND(IRI(CONCAT(...)) AS ?g)` is gone. The guard line gains `ISIRI($g)` and `sameTerm($g, IRI(CONCAT(...)))`.

## One command

Run from the repository root. A pass is `2003 passed, 1 xfailed`, which is the 1920 of H2.2 and 83 new cases.

```bash
mise run check:persistence
```

## Artefacts to inspect

- `builders.py`, the `_create`, `_replace`, `_tombstone` and `_unconditional` builders beside their templates.
- `tests/fixtures/ir/replace-named-graph-caller.rq` beside `replace-named-graph.rq`.
- `ir_render.py`, `_Scope.joined` and `_equals`.

## Adversarial probe

Run on 2026-10-12, restored afterwards.

| Mutation | Result |
|---|---|
| the scope rule reverted so an outer `?g` is not visible | 29 cases fail, the ports (T2) among them |
| the guard at the top level of `WHERE` | 32 cases fail, T6 and T16 among them |
| `equals` not emitted into the guard | 14 fail, T6 and T23 among them |
| `equals` not checked for `NOW()` | 12 fail, including the refusal case |
| the sweep deleting from the transaction graph | the harness fails (T2) |
| the caller-named form still binding `?g` in the query | 21 fail |
| the tombstone not writing `pat:deleted` | the harness fails (T2) |
| the metadata and transaction roles swapped in `GRAPH_ROLES` | **not caught** by the existing role test, which asks the table. T32 added, and then caught |

## Deliberate non-coverage

- `cas-replace-value-guard` (TD-43), `$assertGraph` and `$retractGraph` as required under the patch-log model (H2.7), the payload's
  own checks (H2.8).
- Oxigraph, and the cost of a store that evaluates the inner group before the join (H2.4, TD-42).
- Recording `graph_names` in the compiled profile (H2.7).
- rdflib only. Its handling of an unbound graph variable in a template differs from the specification (T8).
