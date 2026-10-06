<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Formal Methods, Phase 0: the Prover Experiment

**Unit ID:** `formal-methods-phase-0`
**Epic:** [formal-methods](formal-methods.md)
**Status:** Proposed, awaiting human review
**Status record:** the epic's [status record](../status/formal-methods.md)
**Decides:** FM-D1 (the proof assistant), and the Haskell question of FM-D10
**Changes:** on a spike branch only (§7). Nothing reaches `main` except the brief, the report and the status record

## 1. Question

Is Rocq with OCaml, or Isabelle/HOL with OCaml (and Haskell or Scala), the better base for the
formal methods programme? The sketch's analysis, given in chat on 2026-10-06, leaned towards
Isabelle/HOL for counterexample finding, automation, proof maintenance, temporal monitoring
precedent and multiple code generation targets, and towards Rocq for verified extraction, ML
functors, dependent types and verified-compiler precedent. This phase settles it with measurements
on the same targets.

## 2. Targets

Both tracks formalise the same two targets, from the same written semantics (FM-0.1).

| # | Target | Content | Why it is representative |
|---|---|---|---|
| TA | the logic kernel | three values, strong Kleene connectives, the information order, negation, and set readings over finite sets of values (Eligibility L15 and L16) | small, case-heavy, the base of every later theory |
| TB | Vocabulary binding resolution | contracts, schemes, bindings with scopes as sets and validity periods, applicability, maximality by scope superset, conflict, fallback to the unscoped default, a resolved record kept under its binding (ADR-A85, `tools/vocabulary/src/vocabulary/resolver.py`) | a real algorithm with a Python implementation to compare against, and the site of HQ-4 |

Theorems each track must prove on the clean specification:

| # | Theorem |
|---|---|
| TA1 | the binary connectives are monotone in the information order |
| TA2 | negation swaps the decided values and fixes Undetermined (L16) |
| TA3 | under some value and every value, the combined outcome is as L15 states, including Undetermined for no value |
| TB1 | resolution is a function of contract, context and time |
| TB2 | the selected binding is applicable and maximal by scope |
| TB3 | a conflict is reported exactly when two applicable bindings are maximal and distinct |
| TB4 | with no applicable binding, the unscoped default is used if present, and otherwise no resolution |
| TB5 | adding a binding never changes a resolution already recorded under its binding (no retroactive re-resolution) |

## 3. Seeded defects

Each defect is introduced into a copy of the specification. A track scores by finding it.

| # | Defect | Property that should fail |
|---|---|---|
| D1 | TD-17's shape: two named individuals, a functional property, two facts that give one subject both as values, and no distinctness axiom | "the two individuals are distinct" is not entailed. The counterexample is a model in which they are equal |
| D2 | HQ-4's shape: two unscoped bindings for one contract | "every contract a deployment needs resolves" fails, with the two bindings as witness |
| D3 | set reading under every value returns Permitted when there is no value | TA3, and monotonicity under adding a value |
| D4 | precedence picks a subset of scopes instead of a superset | TB2 |
| D5 | a validity period's end treated as inclusive in one rule and exclusive in another | "two bindings with adjacent periods never both apply", and agreement with the Python resolver |

## 4. Measures

| # | Measure | How | Weight |
|---|---|---|---|
| M1 | counterexample finding | for each defect: found automatically or not, wall time, agent tokens, and whether the counterexample is readable | 25 |
| M2 | proof effort | agent tokens and proof lines to prove TA1 to TB5 on the clean specification. Share of goals closed by one automated call | 20 |
| M3 | robustness to change | after the proofs, apply a scripted change to the specification (bindings gain a second, independent scope dimension). Count broken proofs and the tokens to repair them | 15 |
| M4 | generated OCaml | size, readability, native type mapping, use of unsafe casts, run time on the benchmark (§5), ease of joining the typed JSON codec | 15 |
| M5 | other targets | Haskell from both where possible, Scala from Isabelle. N-version agreement on the benchmark. Cost of keeping each build | 5 |
| M6 | architecture fit | express TB against a Vocabulary interface (a module type or a locale) and the kernel. Show that it cannot read a ledger. Show a unit-indexed quantity type | 10 |
| M7 | toolchain | install size, cold and cached build time, `mise` integration, editor and language server support | 10 |

## 5. Worker smoke test and benchmark

| Part | Content |
|---|---|
| inputs | generated deployments: up to 10,000 bindings over 1,000 contexts and 200 contracts, with validity periods, as typed JSON |
| baseline | the Python resolver in `tools/vocabulary`, on the same inputs read from Turtle |
| candidates | each track's generated OCaml, invoked by a Python wrapper as a subprocess with a fixed argument vector, input and output files in a private directory |
| differential test | every candidate's resolutions equal the Python resolver's on every input, conflicts included |
| timing | wall time and peak memory, end to end including encoding, decoding and process start, and the tool's own time alone |
| N-version | for Isabelle, the OCaml and Haskell builds give identical outputs |

The smoke test uses no RabbitMQ. It exercises the subprocess half of the toolchain workers design,
which is where the cost and the risk are.

## 6. Decision rule

Each measure is scored 0 to 10 per track by the report's evidence, weighted, and summed. The higher
total wins. A margin under 5 points out of 100 is a tie, and a tie goes to the track with the higher
M1 score, since validating models is the programme's primary goal. The human may overrule with
reasons, which the status record keeps.

## 7. Where the work lives

### 7.1 A spike branch

The experiment runs on its own branch, `fm/phase-0-prover-spike`, which the human creates from
`main`. The branch may never be merged. Whatever the outcome, what it learned reaches `main`.

| Content | On the branch | Reaches `main` |
|---|---|---|
| the brief (FM-0.1) | yes | yes, with the plan's other documents |
| spike sources: theories, proofs, code generation settings, the Python wrapper, the benchmark generator | yes, under `spikes/formal-prover/`, with one subdirectory per track and one for the smoke test | no. `spikes/` is a new directory, allowed on an unmerged branch only. If phase 1 adopts any of it, it moves to the home FM-D2 decides, under that ADR |
| the report (FM-0.5) | yes | yes, carried to `main` on its own, merged or not |
| the status record's updates | yes | yes |

The branch's head commit is recorded in the report, so the result can be reproduced from it even if
the branch is later deleted.

### 7.2 What stays out of git

Two git-ignored locations, by kind:

| Location | For | Ignored by |
|---|---|---|
| `.build/formal/` | build artefacts: toolchain distributions and everything a build produces | a new `.gitignore` rule, `.build/formal/*` with `!.build/formal/.gitkeep`, following the existing `.build/` convention. FM-0.1 adds it on the branch |
| `.local/formal/` | files that are not build artefacts but must not reach GitHub: generated benchmark data, run logs, timing data | the existing `.local/**` rule |

| Kind | Location | Set by |
|---|---|---|
| the opam root and switch, with Rocq, dune and OCaml | `.build/formal/opam/` | `OPAMROOT` |
| the Isabelle distribution and its user home, including session heap images | `.build/formal/isabelle/`, `.build/formal/isabelle-home/` | `ISABELLE_HOME_USER` |
| build outputs: compiled theories, extracted and generated sources, binaries | `.build/formal/out/` | dune's build directory, Isabelle's export directory |
| generated benchmark inputs and outputs | `.local/formal/bench/` | the benchmark generator's output path |
| logs and timing data | `.local/formal/runs/` | the smoke test harness |

Toolchains are installed by the human or with the human's approval, into `.build/formal/` only.
Their versions go in the report. Before each commit on the branch, `git status` must show no build
output, no binary, no generated benchmark data and no toolchain file. Only sources, the brief, the
report, the status record and the `.gitignore` rule are tracked. The spike sources' own settings
point every tool's output at `.build/formal/` or `.local/formal/`, so a default build cannot write
into the tracked tree.

## 8. Slices

| Slice | Content | Output | Estimate (tokens) |
|---|---|---|---|
| FM-0.1 | the brief: the written semantics of TA and TB, the defects as patches, the measures, the benchmark generator, the report template, fairness rules. The `.build/formal/` ignore rule and its `.gitkeep` | Validation Pack `docs/developer/validation/formal-methods-0.md` | under 0.05M |
| FM-0.2 | the Rocq track: TA, TB, the defects, extraction to OCaml, an attempt at Haskell extraction | `spikes/formal-prover/rocq/`, measurements | 0.15M to 0.3M |
| FM-0.3 | the Isabelle track: TA, TB, the defects, code generation to OCaml, Haskell and Scala | `spikes/formal-prover/isabelle/`, measurements | 0.15M to 0.3M |
| FM-0.4 | the worker smoke test and benchmark, against the Python resolver | `spikes/formal-prover/smoke/`, measurements | 0.05M to 0.1M |
| FM-0.5 | the report: scores, evidence, recommendation | `docs/developer/notes/formal-prover-experiment.md` | under 0.05M |

**Fairness.** One model and one agent configuration for both tracks. Both tracks start from the same
written semantics, so neither invents the specification. The order of the tracks is recorded, since
the second may benefit from the first, and the report weighs that. Each track has the same token cap
per target, and a target not finished within it is scored as not finished.

## 9. Gate 0

| Criterion | Evidence |
|---|---|
| the report is complete, with every measure scored and its evidence linked | the report |
| FM-D1 is decided, with reasons if the decision rule is overruled | the status record |
| FM-D10's Haskell question is answered | the status record |
| the spike branch's head commit is recorded, and no build output, binary or toolchain file is tracked on it | the report, `git status` on the branch |
| the report and the status record are on `main` | `main` |
| the phase 1 plan is written | `formal-methods-phase-1.md` |

## 10. Out of scope

Any change under `ontology/`, `tools/`, `workers/` or `platform/`. RabbitMQ wiring. Lean 4, which
the sketch's analysis set aside, unless the human adds it as a third track.
