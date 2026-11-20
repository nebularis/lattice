<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# `tools/proofs/shared/`, the shared session

`LatticeShared` holds a definition only where two developments both use it ([ADR-A-FM2](../../../docs/architecture/decisions/ADR-A-FM2-formal-methods-theory-home.md)'s addendum of 2026-11-18). Today that is a position and an amount. It is `session LatticeShared = LatticeBase +`, with `quick_and_dirty = false` and its own `timeout`, as the ledger's session has.

## What it holds

| Theory | Definitions | Laws |
|---|---|---|
| `Positions.thy` | `position`, a synonym for the natural numbers. `reached`, the position a sequence of writes has reached, which is the number of its writes | SP1 to SP4 |
| `Amounts.thy` | `('k, 'n) amounts = 'k => 'n`, a number for each key. `amount_zero`, `amount_add`, `amount_diff`, `amount_le` and `amount_sum`, each key by key | SA1 to SA5 and SAn |

**A position** is a natural number on a named axis, and two positions are compared only within one axis. The axis is not a type here. So the checker does not refuse a comparison across two axes, and whoever states two positions keeps them on one axis. On a sequence the writer assigns each position, the next number at each write, with no gap. Position 0 means nothing is written yet, and position n is the n-th write. On an effective axis, such as the day a posting takes effect, positions may skip and several facts may share one.

**An amount** gives a number for each key, and the number type stays generic. Each law names the weakest class it needs: a commutative monoid to add, a group to subtract, a partial order to compare, an ordered group to do both. A development that stores an amount and computes nothing with it reads it at any type. Code exported from a theory fixes the number type when it is exported.

## What is proved

Each row is a theorem between `(* GATE:BEGIN <id> *)` and `(* GATE:END *)` markers, with its claim record under `claims/`. An instance kept on purpose ends in `n`.

| Claim | Theorem | Law |
|---|---|---|
| SP1 | `Positions.nothing_written_is_position_zero` | a sequence is at position 0 exactly when nothing is written |
| SP2 | `Positions.a_write_takes_the_successor` | a write moves a sequence to the successor of its position |
| SP3 | `Positions.positions_are_totally_ordered`, `Positions.no_position_between_successors` | any two positions are ordered, and no position lies between a position and its successor |
| SP4 | `Positions.a_position_pins_one_prefix` | two prefixes of one sequence at the same position are the same writes, so a read pinned to a position reads a fixed fact |
| SA1 | `Amounts.adding_amounts_is_a_commutative_monoid` | adding amounts is commutative and associative, with the zero amount as its unit, over any commutative monoid |
| SA2 | `Amounts.subtracting_undoes_adding` | subtracting an amount undoes adding it, and an amount less itself is zero, over any abelian group |
| SA3 | `Amounts.amounts_are_partially_ordered` | comparing key by key is reflexive, transitive and antisymmetric, over any partial order |
| SAn | `Amounts.amounts_are_not_totally_ordered` | 1 and 0 on two keys against 0 and 1 are not comparable either way, over the integers |
| SA4 | `Amounts.adding_keeps_the_order`, `Amounts.within_is_a_difference_of_at_least_zero` | adding an amount to both sides keeps the order, over any ordered semigroup, and one amount is within another exactly when the difference is at least zero, over any ordered group |
| SA5 | `Amounts.the_sum_adds`, `Amounts.the_sum_keeps_the_order` | the sum over a set of keys adds and sends the zero amount to zero, over any commutative monoid, and keeps the order, over any ordered commutative monoid |

## Who imports it, and who does not

| Who | Imports it |
|---|---|
| a development outside the layers, such as a model of persistence | yes, and never a layer's session unless it models that layer |
| a layer's theorem theory, where its kernel also defines what this session defines | yes, to prove the two agree, so a drift fails a build |
| a layer's generated `Kernel.thy` | no. It keeps importing `Main` or `Complex_Main`, so a layer's formal statement stands by itself |
| the prelude, `../base/` | no. It imports library theories and nothing else |

The ledger's session imports it in `Agreement.thy`, whose lemma `amounts_agree` reads one amount at the kernel's type and at this session's. The lemma type-checks only while both name the same type, so a change to either one fails the ledger's build at that lemma. The ledger's `ROOT` names this session in a `sessions` clause and still parents on the prelude.

## How it is kept

It is hand-written. No README generates it. Its claims are gated as a layer's are: `gate.py` digests each gated statement together with every definition in this directory, so a changed definition moves every claim's digest here and the gate reports it. A changed definition here moves no digest of a layer, but it fails the build of every layer that proves agreement with it.

## Building

`mise run check:proofs` builds the prelude, then this session, then each layer, and gates each. It builds this session whatever layers are named, since a layer may import it. Every build runs from `tools/proofs/`, and every layer's build names `-d base -d shared` before its own directory, so every build names this directory the same way. To build it alone, from the repository root:

```bash
python spikes/formal-prover/env/driver.py --route native --workdir tools/proofs isabelle build -d base -d shared LatticeShared
python tools/proofs/gate.py tools/proofs/shared
```
