<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: eligibility-compiler Part B, A2 and A5, the reasoning harness

**Unit:** [`eligibility-compiler`](../status/eligibility-compiler.md)
**Decision:** [ADR-A83](../../architecture/decisions/ADR-A83-test-only-reasoning-engine-isolation.md), Accepted

## Invariant

HermiT is reachable from tests only, through `platform/reasoning-testkit`.
For builtin-free SWRL, HermiT derives what the rules derive.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| B-01 | a class hierarchy with a disjoint pair / `satisfiable`, `subsumes` / the entailed answers | L4 | + |
| B-02 | a rule and its data in two files / `values` / one derived pair | L4 | + |
| B-03 | the CLI / `subsumes` / one JSON line | L4 | + |
| B-04 | this repository / isolation check / no problems | L1 | + |
| B-05 | fixture POMs and a `pyproject.toml` declaring engines / isolation check / three problems, the testkit's own POM and a `test`-scope use excepted | L1 | - |
| A5-01 | concept rules and asked questions / HermiT / the same `exe:impliesDecision` pairs as the rules | L4 | + |
| A5-02 | profile rules / HermiT / the same `exe:impliesProfileDecision` pairs | L4 | + |
| A2-01 | Mork's and Executable's import closures / `consistent` / true | L4 | + |
| A2-02 | a precedence cycle through a materialised edge and two derivations / M7 shape / all three mappings reported, and no report once the cycle is broken | L1 | - and + |
| A2-03 | soft precedence and intent refinement two-cycles / their shapes / reported, and a cycle mixing hard and soft edges is not | L1 | - and + |
| A5-03 | bound-subject rules over skolemised roles / HermiT / the same `exe:permittedUnder` pairs, plus one reached only through a subclass | L4 | + |

A5's interval rules are not checked. They use `swrlb` builtins, which HermiT
does not evaluate. They wait on an Openllet adapter (ADR-A83).

## Commands

```bash
mise run bootstrap:reasoning-testkit
mise run check:reasoning-testkit
mise run check:reasoning-isolation
mise run check:mork-compilers
mise run check:ontology-catalog
```

`check:mork-compilers` skips `test_reasoner.py` when the jar is missing. Check
its output shows the three A5 tests passed, not skipped.

## Artefacts to inspect

- `platform/reasoning-testkit/` and its README.
- `tools/mork_compilers/src/mork_compilers/reasoning.py` and `test_reasoner.py`.
- `tools/reasoning_isolation_check.py` and `tools/test_reasoning_isolation.py`.
- ADR-A83's implementation notes.
- ADR-A97, `ontology/mork/shapes/constraints.ttl`'s acyclicity shapes and
  `tools/test_mork_order_relations.py` (A2).
