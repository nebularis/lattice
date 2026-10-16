<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H1.1, the prefix antichain and overlap check

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice H1.1
([plan §3](../plans/formal-methods-track-h.md))
**Source finding:** [review](../notes/rdf-engine/persistence-fml.md) §6.2, finding #2 and PV-X1.
**Decisions:** none ratified. Two interpretations are recorded in the status record as H-D6 and H-D7
and need our confirmation at the gate.

## Invariant

Law L3 (target coverage is a partition) needs every instance of a class to belong to exactly one
target. Each `dal:GraphPatternScope` compiles to its own target, so two graph-pattern scopes that
cover one class and declare nested `dal:graphPrefix` values (one equal to, or a prefix of, the
other) give an instance in the inner graph two targets, and the resolver has no longest-prefix rule
to choose between them. The check refuses that configuration and names a concrete graph IRI that
both scopes match. Nested `dal:iriPrefix` values on `dal:NamespaceScope` nodes are reported as a
warning only, since the resolver ranks competing scopes by `dal:priority`, which is a defined rule.

## Test cases

All in `tools/persistence/tests/test_hygiene_prefixes.py`.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| H1.1-T1 | `urn:g:lending/` and `urn:g:lending/behaviour/`, one shared class / check / one violation naming both scopes, counterexample under both prefixes | L1 | − |
| H1.1-T2 | the same prefixes, disjoint classes / check / no finding | L1 | + |
| H1.1-T3 | `urn:g:lending/behaviour/` and `urn:g:credit/behaviour/` / check / no finding | L1 | + |
| H1.1-T4 | two scopes, identical prefix, shared class / check / one violation reading "equals" | L1 | − |
| H1.1-T5 | `urn:g:lend/` and `urn:g:lending/`, shared class / check / no finding (shared leading characters are not nesting) | L1 | + |
| H1.1-T6 | nested prefixes, several classes with one in common / check / violation naming only the common class | L1 | − |
| H1.1-T7 | nested `dal:iriPrefix` values / check / one warning, not a violation, naming `dal:priority` | L1 | − |
| H1.1-T8 | disjoint `dal:iriPrefix` values / check / no finding | L1 | + |
| H1.1-T9 | a graph-pattern scope with no `dal:graphPrefix` / check / no finding | L1 | + |
| H1.1-T10 | three nested scopes declared forwards and backwards / check / identical, sorted reports (3 findings) | L2 | + |
| H1.1-T11 | every file in `ontology/persistence/examples` plus the spec / check / no violation (one test per file) | L4 | + |
| H1.1-T12 | an overlapping configuration / `python -m persistence hygiene` / exit 1, output names both scopes and a counterexample | L3 | − |
| H1.1-T13 | a clean configuration, and a warnings-only one / `hygiene` / exit 0 in both | L3 | + |

## One command

Run from the repository root. A pass is `822 passed` with no failures (the 778 existing tests plus
44 new ones). The one warning in the output is pre-existing.

```bash
mise run check:persistence
```

To run only this slice, `mise exec -- python -m pytest tools/persistence/tests/test_hygiene_prefixes.py -q`
should report `44 passed`.

## Adversarial probes

Run on 2026-10-08 against `hygiene.py`, each reverted afterwards.

| Mutation | Tests that failed |
|---|---|
| nesting decided by "first characters match" instead of `startswith` | T3, T5, T8, T13 |
| the shared-class condition removed | T2 |
| graph-prefix overlaps downgraded from violation to warning | T1, T4, T6, T12 |

The maintainer is invited to pick a different mutation, for example by flipping the `<` in the
outer/inner ordering, and confirm a test fails.

## Artefacts to inspect

- `tools/persistence/src/persistence/hygiene.py`, the check and its `Finding` record.
- `tools/persistence/src/persistence/cli.py`, the `hygiene` subcommand.
- Try it by hand: `mise exec -- python -m persistence hygiene ontology/persistence/spec/persistence.ttl ontology/persistence/examples/lending-credit-shared-class.ttl`
  should print `hygiene: 0 violation(s), 0 warning(s)` and exit 0.

## Deliberate non-coverage

- Whether two nested iri-prefix scopes resolve to different values (review C2 asks for "no two scopes
  with different resolved values can match one IRI"). That needs resolved profiles and belongs with
  H1.4 or H2.
- A longest-prefix rule. None exists, and adding one is a resolver change and a design decision.
- `dal:ShapeScope` monotonicity (review PV-D4), not in H1.
- A dedicated `mise` task. H1's closing slice adds one command that runs all five checks (plan §3).
  Until then the tests run under `check:persistence`.
