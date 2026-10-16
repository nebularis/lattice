<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H1.2d, refuse a multi-valued single-valued property (TD-25)

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), a fix arising from H1.2c
**Decided by:** the maintainer, 2026-10-09 (H-D10): the compiler refuses a multi-valued functional
property in the resolver. No ADR. It changes `tools/persistence` behaviour for malformed input only.
**Finding:** TD-25, see [FMH-H1.2c](FMH-H1-2c.md).

## Invariant

Law L1: the compiler's output is a function of the configuration and not of the order its triples
were written in. For every `dal:` property the compiler treats as single-valued, a subject that
declares two values is refused by name, so no value is chosen by position.

## What changed

- `persistence/functional.py` (new): `functional_value(graph, subject, predicate)` returns the one
  value, `None` if there is none, and raises `CrossAxisViolation` of kind
  `MultiValuedFunctionalProperty` for a second distinct value. The message names the subject, the
  property and the values.
- 66 reads of a `dal:` property now use it, in `scopes`, `resolver`, `capability`, `validator` and
  `recipes`. Reads of SHACL and RDF-list properties, and of the compiler's own output, are unchanged.
- `compile_targets` wraps target discovery, which reads scope priorities before any target exists,
  so the refusal reaches the CLI as a `CompileError` and not a traceback.
- An architecture test fails if a `dal:` property in the compile path is read with a bare
  `Graph.value` again.
- The TD-25 expected-failure test is now a real test. TD-25 is removed from the register. TD-15 is
  reworded, since a uniqueness constraint naming several scopes is now refused and not silently
  narrowed.

## Scope and limits

- A subject nothing refers to is never read, so a stray second value on an unused scope is not
  refused. Its output cannot change, so L1 holds. A reader who wants every such input rejected needs
  the structural shapes run over the whole graph, the second option in H-D10's table.
- `dal:keyProperty` and the other properties that hold an RDF list are checked at the list head only.
- A property that is multi-valued by design (`dal:coversClass`, `dal:claimScheme`) is not read this way
  and is unchanged.

## Test cases

In `tools/persistence/tests/test_functional.py` unless noted.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| H1.2d-T1 | no value, one value, two values / the helper / `None`, the value, a refusal listing both | L1 | +/− |
| H1.2d-T2 | a scope with priorities 1 and 3 / compile / refused, naming the scope, the property and both values | L3 | − |
| H1.2d-T3 | the same, written 1,3 and 3,1 / compile / the same refusal both ways (before, the two orders resolved to different strategies) | L2 | − |
| H1.2d-T4 | a scope with one priority / compile / resolved as before | L3 | + |
| H1.2d-T5 | a profile with two values for its own dimension / compile / refused | L3 | − |
| H1.2d-T6 | a namespace scope with two prefixes that a profile uses / compile / refused | L3 | − |
| H1.2d-T7 | a uniqueness constraint naming two scopes / compile / refused (TD-15's old behaviour was to use one silently) | L4 | − |
| H1.2d-T8 | an identity profile with two minted templates / compile / refused | L4 | − |
| H1.2d-T9 | every shipped example / compile / none is refused for this kind | L4 | + |
| H1.2d-T10 | a multi-valued configuration / `persistence compile` / exit 1 and the kind on stderr | L3 | − |
| H1.2d-T11 | the compile-path source / AST scan / no `dal:` property read with a bare `Graph.value` | L1 | + |
| witness | `refusal-MultiValuedFunctionalProperty.ttl` / witness check / the new rule is witnessed (86 of 86) | L4 | + |

## One command

Run from the repository root. A pass is `869 passed, 1 xfailed`. The one expected failure is TD-23.

```bash
mise run check:persistence
```

## Adversarial probes

Run on 2026-10-09, each reverted afterwards.

| Mutation | Result |
|---|---|
| the priority read in `scopes.py` reverted to `graph.value` | T2, T3 (both orders), T10 and T11 fail, and the witness for the new rule fails, so 10 tests fail |
| one read in `recipes.py` (`mintedIriTemplate`) reverted to `graph.value` | T8 and T11 fail, T11 naming the line |
| `functional_value` made to return the first value without refusing | 14 tests fail, including every refusal case |

## Before and after

Before, `ex:A dal:priority 1, 3` against a scope at priority 2 resolved `dal:concurrencyProfile`
to `ProvidedConcurrency` when `1` was written first and to `Optimistic` when `3` was. After, both
orders give `MultiValuedFunctionalProperty at https://example.org/lending#A`.

## Deliberate non-coverage

- Running the structural SHACL shapes as part of `compile` (the other option in H-D10). Not chosen.
- Unused subjects (above).
- TD-23, still an expected failure.
