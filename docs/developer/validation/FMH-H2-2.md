<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H2.2, the equivalence harness and the first builders

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice H2.2 of the
[typed IR sketch §7](../sketches/formal-methods-track-h-typed-ir.md#7-slices) and its
[§7.1](../sketches/formal-methods-track-h-typed-ir.md#71-the-equivalence-harness-h22), under
[ADR-A123](../../architecture/decisions/ADR-A123-typed-operation-ir.md) and its addendum of 2026-10-12.
**Decisions needing confirmation:** decision 1 is decided (2026-10-12). Decisions 2 and 3 are open, and the review
recommends accepting both.

## Invariant

A builder renders the query its Mustache template does, apart from the required-parameter guard, and the guard
turns a missing or mistyped parameter into no write (TD-34). "A port changes nothing, and a change ports nothing."

## What changed

- `persistence/builders.py`: `bootstrap-version-row` and `append-event`, each with its dataset-guard variant, as typed
  `Operation` values built from the same compile-time bindings a template takes (`BUILDERS`, `build`). Each keeps
  the template's variable names. The builders take the guards flag (`guards=False` gives `GUARDS_OFF`).
- `tests/equivalence.py`: the harness. Both sides are parsed and translated to algebra by rdflib. Only the triples of
  a basic graph pattern and the conjuncts of a filter are put in order. Variable names must match. It also checks
  that a builder reads exactly the bindings its template uses, and that it compared as many operations as were ported.
- `instantiate` renders a ported operation from its builder, with the guard, and any other operation, and any operation
  under `--template-dir`, from Mustache as before. `persistence instantiate --no-parameter-guards` leaves the guards out.
  `operation_context` is now shared with the builders.
- `Kind.IRI_OR_LITERAL` and the function `ISLITERAL` in the IR (decision 1).
- The first port of `append-event` differed from its template, in an `epoch` triple I put in the non-dataset `INSERT`.
  The harness caught it before any other test did, and the builder was corrected.
- TD-34 is partly closed. Its register row says which operations are done.
- **After the review (2026-10-12).** A builder no longer chooses a graph role. `GRAPH_ROLES` in `builders.py` gives
  the role of every graph by its binding name (`txnGraph`, `metaGraphPrefix` and the rest) or by the name of the variable
  a query binds to a graph (`g`, `log`, `logGraph`, `logGraph2`, `eventGraph`, each with one meaning in every template).
  `Bindings.graph(name)` and `graph_var(name)` are the only ways a builder makes a graph. Before this, a builder that put
  the transaction graph in the `META` role passed every test, since a role is not rendered and only the derived read
  and write sets carry it.
- **After the review (2026-10-12).** `operation_context` wraps each binding as the term type its `dal:paramType` declares
  (`Iri`, `Literal` for `String` and `Literal`, `PropertyPath`, or an `int`), and refuses an unknown type. Before this,
  `Bindings.const` guessed the type from the text's first character, which would have read a composite family's
  `ownedPath` as an IRI in H2.4. A path binding is now read with `Bindings.path`, and `const` refuses one.
- `tests/equivalence.py` imports at module level, and two unused imports are gone.

## Decisions needing confirmation

1. **Decided 2026-10-12. `$occurredAt` is a new kind, `IriOrLiteral`, guarded by `isIRI || isLiteral`.** It was named
   `Term` when first built and renamed the same day, since a term includes blank nodes and `Term` means something else in
   `instrument`. The kind is a Python enum value, not an ontology class. The valid time of an event is an adopter's own
   value and the README does not type it, so a `DATATYPE` test could refuse a date an adopter uses today. The guard still
   catches a missing value. The maintainer agreed to keep it untyped as to datatype. A datatype taken from the family's
   declared valid-time property is possible in H2.7.
2. **`instantiate` now uses the builders for the four ported operations**, so the shipped `.rq` of those operations carries
   the guard. That is what closes TD-34 for them, and the S-3 and S-4 checks and the witness harness pass over the new
   text. The flag is on `instantiate` for now. The addendum puts it on `compile`, recorded in the profile, which needs the
   `dal:` term of H2.7, so the flag moves then.
3. **The harness corpus is every fixture that compiles**, the examples and the witnesses, not the examples alone. Between
   them the four templates are generated 5 times, so five comparisons run. A template that no fixture selects is not
   compared (T1 fails first, so a gap cannot hide).

## Test cases

In `tools/persistence/tests/test_builders.py`, helper `equivalence.py`.

| ID | Given / When / Then | Level | Invariant | +/- |
|---|---|---|---|---|
| H2.2-T1 | the builders and the fixture corpus / listed / the four ported templates, each generated by a fixture | L3 | the harness has operations for every port | + |
| H2.2-T2 | every ported operation of the corpus / template and builder (guards off) compared as algebra / equal, and the count equals the operations found | L3 | a port changes nothing | + |
| H2.2-T3 | each of the four builders / the bindings it reads / equal to the template's tags | L3 | no binding is ignored or invented | + |
| H2.2-T4 | the harness run on one operation fewer, and on none / `require_compared` / fails | L2 | the harness cannot pass vacuously | − |
| H2.2-T5 | a dropped triple, a pattern in another graph, a renamed variable, in each of two builders / compared / `Mismatch` | L2 | the harness can fail | − |
| H2.2-T6 | each builder with and without the guard / rendered / equal to the other plus exactly one group holding one `FILTER` of the type tests the parameter list implies, first in `WHERE` | L3 | the guard is the whole difference | + |
| H2.2-T7 | `append-event` on a stream row, run on rdflib / executed / the sequence and head move, the claim, the event and the log are written | L4 | the port behaves | + |
| H2.2-T8 | the first revision / executed / no `prevRev` triple, and the revision is still written | L4 | an unbound variable in a template skips its triple only | + |
| H2.2-T9 | the same request twice / executed / the second changes nothing | L4 | a retry is a no-op | + |
| H2.2-T10 | a second event / executed / the sequence is 2 and the revision chains to the first | L4 | the chain | + |
| H2.2-T11 | the dataset-guard variant / executed against dataset epochs 3 and 4 / writes only on a match | L4 | the dataset guard | + |
| H2.2-T12 | `bootstrap-version-row` twice / executed / one row of three triples, unchanged by the second | L4 | idempotent | + |
| H2.2-T13 | the dataset-guard bootstrap / dataset epoch 4 and 3 / writes only on a match | L4 | the dataset guard | + |
| H2.2-T14 | no epoch, no target, epoch as `xsd:integer`, target as a literal / executed with and without the guard / guarded writes nothing, unguarded writes the exact bad rows | L4 | TD-34 demonstrated and closed | − |
| H2.2-T15 | `append-event` with each parameter but `stream` left out in turn (8 cases) / executed / nothing is written, no claim | L4 | every required parameter is guarded | − |
| H2.2-T16 | `append-event` with no `$stream` over two stored streams / executed with and without the guard / guarded writes nothing, unguarded writes a stored stream's record | L4 | the guard is tested before any pattern can bind the parameter (F1) | − |
| H2.2-T17 | a compiled `append` / `instantiate` with and without `guards=False` / the guard is present and absent | L3 | the ported operations are emitted from their builders | + |
| H2.2-T18 | an overriding template library / `instantiate` / rendered by Mustache, no guard | L3 | `--template-dir` keeps its meaning | + |
| H2.2-T19 | the command line with and without `--no-parameter-guards` / run / the files carry the guard or not | L4 | the flag works | + |
| H2.2-T20 | every ported operation of the corpus / every graph in it / has the role `GRAPH_ROLES` gives its binding or variable name | L3 | read and write sets carry the right roles | + |
| H2.2-T21 | every template / its `GRAPH {{{slot}}}` and `GRAPH ?var` names, comments removed / all in `GRAPH_ROLES` | L3 | the table covers the ports still to come | + |
| H2.2-T22 | every generated operation of the corpus / `operation_context` / each value has the type its `dal:paramType` declares, and `Iri`, `Integer` and `PropertyPath` are all seen | L3 | bindings are typed by declaration, not by their text | + |
| H2.2-T23 | a binding with an unknown `dal:paramType` / `operation_context` / refused | L1 | an unknown type is not guessed | − |
| H2.2-T24 | a `PropertyPath` binding / `Bindings.path` and `Bindings.const` / a `Path`, and `const` refuses it | L1 | a path is never read as a constant | − |

## One command

Run from the repository root. A pass is `1920 passed, 1 xfailed`, which is the 1875 of H2.1 and 45 new cases, 40 in the
slice as first built and 5 added after the review. Run on 2026-10-12 at `1920 passed, 1 xfailed`.

```bash
mise run check:persistence
```

## Artefacts to inspect

- `tools/persistence/src/persistence/builders.py`, beside `templates/append-event.mustache`.
- `tools/persistence/tests/equivalence.py`.
- An instantiated `append.rq`, from `persistence compile` then `persistence instantiate` on `template-append-event.ttl`
  in the witness directory.

## Adversarial probe

Run on 2026-10-12, restored afterwards. The last three rows are the review's probes.

| Mutation | Result |
|---|---|
| the guard placed at the top level of `WHERE`, not in its own group | T6, T15 (epoch) and T16 fail |
| `instantiate` ignores the builders | T17 and T19 fail |
| an `IriOrLiteral` parameter given no guard test | T6 (both append variants) and T15 (`occurredAt`) fail |
| a builder reads one binding more than its template | T2 and T3 fail |
| `append-event` writes one extra triple to the log | T2 fails |
| `bootstrap` writes `seq` as an integer, not an `xsd:long` | T2 and T4 fail |
| the harness's own mutations (dropped triple, other graph, renamed variable) | caught, T5 |
| `append-event`'s transaction graph given the `META` role, before the review | **not caught**, 1915 passed. Led to `GRAPH_ROLES` |
| the same, written as `Graph(GraphRole.META, b.const("txnGraph"))`, after the review | T20 fails |
| `operation_context` wraps every binding as an `Iri`, after the review | T22 fails |

## Deliberate non-coverage

- The other operations. H2.3 (the named-graph row writers), H2.4 (composite), H2.5 (key claims and audits).
- Oxigraph. The behaviour tests use rdflib, as in H2.1, and the composite benchmark of H2.4 brings in Oxigraph.
- The caller-side parameter check of H2-Q4 and the `dal:` term that records whether guards are on. H2.8 and H2.7.
- Text-substituting callers for the builders. H2.1's T28 substitutes text into an IR operation and runs it. No test does
  that for a builder's output yet.
