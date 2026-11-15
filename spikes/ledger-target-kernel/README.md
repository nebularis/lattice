<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Spike: the target ledger kernel

**Status:** a spike, not production. It defines no interface and changes no tool. Nothing in `tools/`, `benchmark/` or `platform/` imports it, and `tools/proofs/ledger/` is untouched.

**Origin:** slice LG-21 of the [ledger plan](../../docs/developer/plans/ledger.md), which writes the ledger kernel once in its decided form before any further law is proved on it. The [sketch](../../docs/developer/sketches/ledger-target-kernel.md) says why each definition is as it is, what writing them down found, and what waits on a decision.

## Contents

| File | Role |
|---|---|
| `Target.thy` | the target kernel, definitions and six evaluated examples, with no law proved |
| `ROOT` | a session on the HOL heap, so the theory is type-checked |
| `model.py` | the same definitions transliterated, with a search of their laws on generated cases. It loads the model of the [spike on ranks](../ledger-ranks-and-pots/README.md) to compare against |
| `cases.py` | draws 600 inputs from fixed seeds and writes `Cases.thy` with what the model computes for each |
| `Cases.thy` | generated, never edited. Isabelle evaluates the definitions of `Target.thy` on each input and compares the result with the model's, in 60 lemmas of ten cases, so the build fails where the theory and the model disagree. It carries one small proof, a code equation that unfolds a path one step so that what reads a path evaluates |

## Running it

From the repository root. The model needs the standard library only, and stops at the first case that breaks a law. Pass a divisor for a shorter run, for example `model.py 20`.

```bash
mise exec -- python spikes/ledger-target-kernel/model.py
```

The theory needs Isabelle2025-2, which `mise run bootstrap:formal-native-isabelle` installs. It builds in about a minute, nearly all of it the 600 cases, and proves no law.

```bash
mise exec -- isabelle build -d spikes/ledger-target-kernel Ledger_Target
```

A pass is `Finished Ledger_Target`. Run one Isabelle build at a time. After a change to `model.py` or `Target.thy`, write the cases again with `mise exec -- python spikes/ledger-target-kernel/cases.py` and build.

## What it does not show

It proves no law. The sketch's section 5 has the figures of the run of 2026-11-15 and what the search leaves out.
