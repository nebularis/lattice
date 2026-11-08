<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# lattice-testing-ledger-corpus

Generated ledger data for LATTICE's tests, checks and benchmarks ([ADR-A125](../../../docs/architecture/decisions/ADR-A125-test-support-tooling.md)). It builds two graphs under the ledger's own terms, at any size: a wide tree of account definitions, and one pass over such a tree in which every leaf takes one debit and every account moved has a balance record. `tools/test_ledger.py` validates them small, under `check`, and `benchmark/ledger-posting-cost/test_shape_scale.py` validates them at the sizes the ledger plan's LG1-09 and LG2-10 rows name, with the time recorded and never asserted (STD-155).

It carries no insurance or other domain content. The graphs hold the ledger's own classes and a value space of their own, and nothing a test asserts about them is a claim about any realisation.

## What it does

| Function | Returns |
|---|---|
| `account_tree(definitions, sections)` | `definitions` account definitions, one root, `sections` sections part of it and the rest sublimits spread across the sections, the shape real account trees have |
| `one_pass(leaves)` | a root, `leaves - 1` sections and `leaves` leaves, each leaf its own definition and account, one pass in which each leaf takes one debit of 1, and a balance record for every account moved, so `2 * leaves` records |

Each returns the data alone. The caller adds the model graphs it validates against.

## Install

`mise run bootstrap` installs it with every other Python package of the repository, and `mise run bootstrap:testing-ledger-corpus` installs it alone.
