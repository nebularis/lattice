<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Formal Methods, Track D: the Prover Spike

**Unit ID:** `formal-methods-phase-0`
**Epic:** [formal-methods](formal-methods.md)
**Status:** Proposed, narrowed after review on 2026-10-06 ([response](../notes/formal-methods-review-response.md))
**Status record:** the epic's [status record](../status/formal-methods.md)
**Decides:** FM-D1 (the proof assistant, or none), and the Haskell question of FM-D10
**Changes:** on a spike branch only (§7). Nothing reaches `main` except the brief, the report and the status record

## 1. Question

Is a proof assistant worth its cost for LATTICE, and if so, Rocq or Isabelle/HOL? The answer turns on
one number above all: what it costs to carry one law from its prose to a gated release, and to keep
it there when the layer changes in a MINOR step.

The chat analysis of 2026-10-06 leaned towards Isabelle/HOL for counterexample finding, automation,
proof maintenance, temporal monitoring precedent and code generation targets, and towards Rocq for
verified extraction, ML functors, dependent types and verified-compiler precedent. This spike
settles it on measurements.

A toolchain spike of 2026-10-06 has already shown that both stacks install and run on a Windows host
without administrator rights, natively and in Linux containers, and that each proves, generates,
compiles, runs and reads ASTs (epic §4, Environments). This spike therefore measures the provers, not
whether they can be installed, and runs on the image route that every later track uses.

**Lean 4** is not a track. Its machine-assisted proof tooling is advancing quickly, and it has a candidate
Rust bridge (Aeneas), but it generates only C and has no extraction trust story comparable to
MetaRocq's or a code generator with Isabelle's targets. This programme's code generation needs those,
so the argument is decisive for it.

## 2. Targets

Both tracks formalise the same targets, from the same written semantics (D1).

| # | Target | Content |
|---|---|---|
| TA | the logic kernel | three values, strong Kleene connectives, the information order, negation |
| TL | one law end to end | Eligibility's L15 (set readings) and L16 (negation), stated against an Eligibility interface with one instantiation, carried through the whole chain (§2.1) |

### 2.1 The chain

| Link | For L15 and L16 |
|---|---|
| prose | the Eligibility README's statement of the laws |
| shape | the structural shapes on `elg:valueReading` and `elg:negated` |
| formal statement | the theorems below, short, named, and extracted into the README |
| proof | in each prover, with its assumption audit (no `Admitted`, `sorry`, oracle or unchecked axiom) |
| interface | an Eligibility interface whose assumptions one instantiation discharges (non-vacuity) |
| adequacy | the decoder over the set-reading examples, each decided as `tools/test_eligibility_examples.py` expects |
| compiled backend | the SPARQL backend's decisions on the same examples equal the formal denotation's |
| claim record | the assurance profile's claim, with statement digest, assumptions, scope, method and assertor |
| report and gate | a report row, and a gate that fails when the statement digest changes unreviewed |

### 2.2 Theorems

| # | Theorem |
|---|---|
| TA1 | the binary connectives are monotone in the information order |
| TA2 | negation swaps the decided values and fixes Undetermined (L16) |
| TL1 | under some value and every value, the combined outcome is as L15 states, including Undetermined for no value |
| TL2 | a set reading is monotone in the information order of its values |
| TL3 | a negated set reading is the set reading of the negated condition only where L15 and L16 say so, and the spike records which combinations differ |

## 3. Seeded defects

| # | Defect | Property that should fail |
|---|---|---|
| S1 | every value returns Permitted when there is no value | TL1, and monotonicity under adding a value |
| S2 | negation maps Undetermined to Denied | TA2 |
| S3 | an interface assumption no instantiation can discharge | the non-vacuity check |
| S4 | a proof left with `Admitted` or `sorry` | the assumption audit, before the claim is recorded |
| S5 | a weakened theorem under its old name | the statement digest gate |

Defects about binding resolution and TD-17's shape move to track C's design models.

## 4. Measures

| # | Measure | How | Weight |
|---|---|---|---|
| M0 | cost to carry the law end to end | tokens and wall time from prose to gate, both laws | 20 |
| M1 | counterexample finding | for S1 to S3: found automatically or not, wall time, readability | 15 |
| M2 | proof effort and agent success | tokens and lines for TA1 to TL3. The share of agent proof attempts the kernel accepts, and the cost of discarding a failed one | 15 |
| M3 | proof-repair cost under a MINOR change | apply a scripted change of the kind a real release makes: a fourth value reading is added to L15. Count broken proofs and the tokens to repair them | 15 |
| M4 | generated OCaml | size, readability, native type mapping, unsafe casts, fit with the typed codec | 5 |
| M5 | other targets | Haskell from both where possible, Scala from Isabelle, and whether N-version agreement comes nearly free | 5 |
| M6 | architecture fit | the interface, and `DesignEnv` against `RunEnv`: scored separately for a typing error (Rocq can) and a definitional guarantee with a theorem (Isabelle) | 10 |
| M7 | toolchain and CI | on macOS (Apple silicon), Windows and Linux: image size, time to pull or build, idle and peak memory and CPU per job, cold and cached dependency-aware builds, `mise` integration. Native authoring: install time and size per host, and editor support. Whether the tool has an arm64 build | 5 |
| M8 | library fit | lattices, orders, quantities, Datalog and SQL semantics, and the licence each import would bring | 5 |
| M9 | consistency with prior choices | the engine notes chose Rocq. The cost of switching is counted, not ignored | 5 |

## 5. Decision rule and abandonment

Each measure is scored 0 to 10 per prover by the report's evidence, weighted and summed.

| Outcome | Action |
|---|---|
| neither prover completes the chain within its budget (§8) | **abandon the prover** for now. Track E does not start. Tracks A, B and C continue |
| one completes it | that prover, unless its M3 is below 4 |
| both complete it | the higher total. A margin under 5 points is a tie, broken by M0, then M3 |

The human may overrule with reasons, which the status record keeps.

## 6. What is recorded

The report records each tool by its image or archive digest, with its name and version as a label.
It records the spike branch's head commit, every measure's evidence, the assumption audit's output,
and the MINOR change's diff and repair.

## 7. Where the work lives

### 7.1 A spike branch

The experiment runs on its own branch, `fm/phase-0-prover-spike`, which the human creates from
`main`. The branch may never be merged. Whatever the outcome, what it learned reaches `main`.

| Content | On the branch | Reaches `main` |
|---|---|---|
| the brief (D1) | yes | yes, with the plan's other documents |
| spike sources: theories, proofs, code generation settings, the decoder, the gate script, image definitions and environment tasks | yes, under `spikes/formal-prover/`, one subdirectory per prover | no. `spikes/` is a new directory, allowed on an unmerged branch only. If track E adopts any of it, it moves to the home FM-D2 decides, under that ADR |
| the report (D4) | yes | yes, carried to `main` on its own, merged or not |
| the status record's updates | yes | yes |

The branch's head commit is recorded in the report, so the result can be reproduced from it even if
the branch is later deleted.

### 7.2 Hosts and routes

Both tracks run on the image route of epic §4 for everything measured, on the same host, so that
neither prover gains from its host. The images are built in D0 under the epic's rules: one tool per
image, staged builds, `linux/amd64` and `linux/arm64`, pinned by digest, one container per job with
no network and capped resources.

| Host | Engine | Native authoring route |
|---|---|---|
| macOS, Apple silicon | any OCI engine, its virtual machine capped | Isabelle's macOS bundle, the Rocq Platform's macOS installer |
| Windows | any OCI engine on WSL 2, capped through `.wslconfig` | Isabelle's Windows bundle and ghcup, under a short `LATTICE_FORMAL_ROOT`. Rocq through the Rocq Platform installer, since opam builds it from source in hours |
| Linux | the engine directly | the distribution bundles, opam, ghcup |

MetaRocq, used if the Rocq track needs to read its own terms, and GHC's WebAssembly backend are
image-only. A native result is advisory, and only an image run is recorded in the report.

### 7.3 What stays out of git

Two git-ignored locations, by kind:

| Location | For | Ignored by |
|---|---|---|
| `.build/formal/` | build artefacts: toolchain distributions, image build contexts, caches keyed by image digest, and everything a build produces | a new `.gitignore` rule, `.build/formal/*` with `!.build/formal/.gitkeep`, following the existing `.build/` convention. D0 adds it on the branch |
| `.local/formal/` | files that are not build artefacts but must not reach GitHub: run logs, timing data | the existing `.local/**` rule |

| Kind | Location | Set by |
|---|---|---|
| the opam root and switch, with Rocq, dune and OCaml | `.build/formal/opam/` | `OPAMROOT` |
| the Isabelle distribution and its user home, including session heap images | `.build/formal/isabelle/`, `.build/formal/isabelle-home/` | `ISABELLE_HOME_USER` |
| build outputs: compiled theories, extracted and generated sources, binaries | `.build/formal/out/` | dune's build directory, Isabelle's export directory |
| logs and timing data | `.local/formal/runs/` | the spike's scripts |
| native toolchains on a Windows host without long paths | a short root outside the repository | `LATTICE_FORMAL_ROOT` |
| a proxy's root certificate, where a host needs one to build images | outside the repository, passed to the build as a secret | the host's own setting, never committed |

Toolchains are installed by the human or with the human's approval, into `.build/formal/`, or the
short root, only. Images are pulled or built with the same approval.
Before each commit on the branch, `git status` must show no build output, no binary, no generated
data and no toolchain file. Only sources, the brief, the report, the status record and the
`.gitignore` rule are tracked.

## 8. Slices

| Slice | Content | Output | Estimate (tokens) |
|---|---|---|---|
| D0 | environments: the two prover images and the host-language images under epic §4's rules, multi-arch and pinned. The `check:formal-network`, `bootstrap:formal-images`, optional `bootstrap:formal-native-<tool>` and `check:formal-smoke` tasks in their spike form, with the Python driver. The smoke suite (prove, generate code, compile, run, read an AST, cross-compile) passing on macOS, Windows and Linux by the image route. M7's environment measures | `spikes/formal-prover/env/`, and a section of the report | under 0.05M |
| D1 | the brief: the written semantics of TA and TL, the defects as patches, the MINOR change as a patch, the measures, the report template, the claim and gate scripts in their spike form, fairness rules | Validation Pack `docs/developer/validation/formal-methods-0.md` | under 0.05M |
| D2 | the Rocq track | `spikes/formal-prover/rocq/` | 0.1M to 0.25M, capped at 0.25M |
| D3 | the Isabelle track | `spikes/formal-prover/isabelle/` | 0.1M to 0.25M, capped at 0.25M |
| D4 | the report: scores, evidence, recommendation or abandonment | `docs/developer/notes/formal-prover-experiment.md` | under 0.05M |

**Fairness.** One model and one agent configuration for both tracks, on one host and the image route. Both start from the same written
semantics. The order of the tracks is recorded, since the second may benefit from the first, and the
report weighs that. A target not finished within the cap is scored as not finished.

## 9. Gate D

| Criterion | Evidence |
|---|---|
| the report is complete, with every measure scored and its evidence linked | the report |
| FM-D1 is decided, or the prover abandoned, with reasons if the rule is overruled | the status record |
| FM-D10's Haskell question is answered | the status record |
| the abandonment thresholds of the epic §6 are revised with the measurements | the epic plan |
| the smoke suite passes on macOS, Windows and Linux by the image route, for the chosen prover's stack | D0's results in the report |
| no build output, binary, image, certificate or toolchain file is tracked on the branch | `git status` on the branch |
| the report and the status record are on `main` | `main` |

## 10. Out of scope

Any change under `ontology/`, `tools/`, `workers/` or `platform/`. Performance benchmarks, which are
track F's. Binding resolution, which is track C's. Lean 4 (§1).
