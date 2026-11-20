<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-I5a, the shared proof session

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), MSA-I5a
**Brief:** [machine S brief of 2026-11-18](../notes/machine-s-brief-2026-11-18.md), sections 3, 4 and 5, with the [brief of 2026-11-19, the multi-store half](../notes/machine-s-brief-2026-11-19-multi-store.md), section 4.2, and the [ledger half](../notes/machine-s-brief-2026-11-19.md), section 6.
**Decisions:** [ADR-A-FM2](../../architecture/decisions/ADR-A-FM2-formal-methods-theory-home.md) and its addendum of 2026-11-18 (accepted).
**Machine:** machine S, Windows, Isabelle2025-2 through `FMX_ISABELLE`. **Placement:** T0, public. Proof tooling, nothing domain-specific.
**Status:** built 2026-11-19, not verified.

## Invariant

A position and an amount are defined once, in `LatticeShared`, and their laws are proved and gated there as a layer's are. The ledger's kernel keeps its own amount, and one lemma in a ledger theorem theory reads an amount at both types, so a drift between the two fails the ledger's build. No kernel changes, so no claim digest of a layer moves.

## What changed

- `tools/proofs/shared/`, new. `ROOT` declares `session LatticeShared = LatticeBase +` with `document = false`, `quick_and_dirty = false` and `timeout = 90`, and the theories `Positions` and `Amounts`. A README says what it holds, who imports it and who does not, and how it is kept. Ten claim records under `claims/`, in the ledger's form.
- `Positions.thy`: `type_synonym position = nat`, and `reached`, the position a sequence of writes has reached, its number of writes. It imports `HOL-Library.Sublist`, already in the prelude's heap, for `prefix`.
- `Amounts.thy`: `type_synonym ('k, 'n) amounts = "'k \<Rightarrow> 'n"`, as the ledger's kernel states it, and `amount_zero`, `amount_add`, `amount_diff`, `amount_le` and `amount_sum`, each key by key, each with the weakest sort it needs. It imports `Main`.
- `tools/proofs/ledger/Agreement.thy`, new: the lemma `amounts_agree`. `tools/proofs/ledger/ROOT` gains `sessions LatticeShared` and the theory `Agreement`. The session still parents on `LatticeBase`. `Kernel.thy` is untouched.
- `tools/proofs/check.py`: after the prelude it builds and gates `LatticeShared` with `-d base -d shared`, whatever layers are named, and every layer's build passes `-d base -d shared -d <layer>`. `shared` is never taken for a layer.
- `tools/proofs/README.md` lists the session, with a table of the four sessions, and the by-hand build commands name `-d shared`. `tools/proofs/ledger/README.md` has a row for `Agreement.thy`.

## The laws

| Claim | Theorem | Sort of the number type | State |
|---|---|---|---|
| SP1 | `Positions.nothing_written_is_position_zero`: `reached ws = 0` exactly when `ws = []` | none | passed |
| SP2 | `Positions.a_write_takes_the_successor`: `reached (ws @ [w]) = Suc (reached ws)` | none | passed |
| SP3 | `Positions.positions_are_totally_ordered`, `Positions.no_position_between_successors` | none | passed |
| SP4 | `Positions.a_position_pins_one_prefix`: two prefixes of one sequence at the same position are equal | none | passed |
| SA1 | `Amounts.adding_amounts_is_a_commutative_monoid` | `comm_monoid_add` | passed |
| SA2 | `Amounts.subtracting_undoes_adding` | `ab_group_add` | passed |
| SA3 | `Amounts.amounts_are_partially_ordered` | `order` | passed |
| SAn | `Amounts.amounts_are_not_totally_ordered`, a negative instance on two keys | `int` | passed |
| SA4 | `Amounts.adding_keeps_the_order`, `Amounts.within_is_a_difference_of_at_least_zero` | `ordered_ab_semigroup_add`, `ordered_ab_group_add` | passed |
| SA5 | `Amounts.the_sum_adds`, `Amounts.the_sum_keeps_the_order` | `comm_monoid_add`, `ordered_comm_monoid_add` | passed |

## Test cases

| ID | Given, when, then | Level | Positive or negative | Pass criterion |
|---|---|---|---|---|
| MSAI5a-01 | the shared session built by `check:proofs` | L1 | positive | `LatticeShared` builds, and its gate reports 10 claims passed and `GATE: pass` |
| MSAI5a-02 | the ledger's session built with `Agreement.thy` | L1 | positive | `Finished Ledger`, its gate reports 73 claims passed and `GATE: pass`, no digest mismatch |
| MSAI5a-03 | the shared amount changed to `'k \<Rightarrow> 'n option`, the ledger's session built | L1 | negative | the build fails, here in the shared theory's first definition, since `option` has no zero |
| MSAI5a-04 | the shared amount changed to `'k \<Rightarrow> 'n option` with the rest of `Amounts.thy` set aside in a comment, the ledger's session built | L1 | negative | the build fails at `Agreement.thy` line 16, the lemma `amounts_agree` |
| MSAI5a-05 | every claim digest of the ledger and of Eligibility after the change | L1 | positive | no `STATEMENT DIGEST MISMATCH` row, and no claim record changed |
| MSAI5a-06 | the generated kernels against their READMEs | L0 | positive | `check:formal-freshness` reports 3 artefacts consistent |

## The agreement lemma and the probe

```isabelle
lemma amounts_agree:
  "(v :: ('k, 'n) Kernel.amounts) = (v :: ('k, 'n) Amounts.amounts)"
  by (rule refl)
```

A type synonym is expanded when a statement is read, so the lemma is only reflexivity. Its force is in reading it. One variable carries both type constraints, so the statement type-checks only while both synonyms expand to the same type. The type variables are fixed, so no instantiation reconciles a drift, and Complex_Main's coercions find none from a type variable.

The probe edited `tools/proofs/shared/Amounts.thy` from a script that kept the file's bytes, built the ledger's session with `isabelle build -d base -d shared -d ledger Ledger`, and wrote the bytes back. The file's SHA-256 was `C19575F9…DEE524` before and after, and the script reported `restored: True` each time.

- **MSAI5a-03**, the synonym changed to `"'k \<Rightarrow> 'n option"` alone. `Ledger FAILED`, with `Failed to load theory "Ledger.Agreement" (unresolved "LatticeShared.Amounts")`, `Type unification failed: No type arity option :: zero`, at command `definition` (line 19 of `shared/Amounts.thy`). The shared theory's own definitions refuse the drift first.
- **MSAI5a-04**, the same change, with every definition and law after the synonym set aside in a comment so the shared theory still checks. `Ledger FAILED`, with `Type unification failed`, `Failed to meet type constraint: Term: v :: 'k ⇒ 'n, Type: 'k ⇒ 'n option`, `Cannot generate coercion from "'n" to "'n option"`, at command `lemma` (line 16 of `ledger/Agreement.thy`). This is the agreement lemma.

## What the gate digests

`gate.py` digests each gated statement together with every `datatype`, `record`, `type_synonym`, `fun`, `definition` and `abbreviation` block in the layer's directory. `Agreement.thy` holds one `lemma` and no such block, and no line of its comments opens with one of those words, so it adds nothing to a ledger digest. The claim records of the ledger and of Eligibility are unchanged, and the gate recomputed every digest and found each equal.

## One command

```bash
mise run check:proofs
```

A pass is `GATE: nothing to gate` for the prelude and `GATE: pass` for `shared`, `eligibility` and `ledger`, with 10, 33 and 73 claims passed.

## What was run, in full

- `mise run check:proofs` before the change: exit 0. `LatticeBase` current, `GATE: nothing to gate`. `Running Eligibility ...`, `Finished Eligibility (0:00:04 elapsed time)`, 33 claims passed, `GATE: pass`. `Ledger` current, 73 claims passed, `GATE: pass`.
- `isabelle build -d base -d shared LatticeShared`, through the driver: `Finished LatticeShared (0:00:02 elapsed time)`.
- `python tools/proofs/gate.py tools/proofs/shared`: 10 rows `Proof passed`, `Assumption audit: clean`, `GATE: pass`.
- `mise run check:proofs` after the change: exit 0. `LatticeBase` current, `GATE: nothing to gate`. `LatticeShared` current, 10 claims passed, `GATE: pass`. `Eligibility` current, 33 claims passed, `GATE: pass`. `Running Ledger ...`, `Finished Ledger (0:00:23 elapsed time)`, 73 claims passed, `Assumption audit: clean, no sorry/oops/admit/oracle/by-eval found`, `GATE: pass`. No `STATEMENT DIGEST MISMATCH` and no `failed` row. The prelude's heap was not rebuilt by the added `-d shared`.
- The two probes, as above, each `probe build exit: 1` and `restored: True`.
- `mise run check:proofs` after the probes: exit 0, the same lines, with `Finished Ledger (0:00:23 elapsed time)`, since the failed probe builds left the ledger to be built again.
- `mise run check:formal-freshness`: `3 formal-methods artefact(s) consistent with their literate READMEs`.
- `mise run check:identifiers`: `identifier check passed: 2379 identifiers mentioned in 1020 files, 0 unresolved, 0 defined twice`.
- `mise exec -- python tools/writing_rules.py` on the four changed Markdown files: `writing rules: 0 failure(s), 15 warning(s)`. Each warning is a hard-wrapped line of `tools/proofs/README.md` in a paragraph this slice did not change. The first run reported two failures there, a semicolon in each of two lines this slice had not written, and both were rewritten.

| Session | Claims before | Claims after |
|---|---|---|
| `LatticeBase` | 0, nothing to gate | 0, nothing to gate |
| `LatticeShared` | did not exist | 10 |
| `Eligibility` | 33 | 33 |
| `Ledger` | 73 | 73 |

## Deliberate non-coverage

- **No agreement for a position.** The ledger's kernel takes a day and a recording as natural numbers and names no position type, so there is nothing to agree with yet. Where a layer's kernel names a position, its theorem theory proves agreement the same way.
- **No type for each axis.** A position is a synonym, as the brief asks, so nothing refuses a comparison across axes. A type of its own for each axis changes the layers' kernels.
- **No agreement for the kernel's operations.** The kernel's `nothing`, `less`, `fits_in` and `total` are the shared `amount_zero`, `amount_diff`, `amount_le` and `amount_sum` at `linordered_idom`, but the brief asks for agreement on the type alone, and no lemma states it.
- **The agreement lemma has no claim record.** It is a check on the build, not a law of the ledger, and the gate does not notice a claim whose marked statement is removed, so a record would add no guard.
- **No code export.** Nothing in the shared session is exported.

## Doc delta

- `tools/proofs/shared/README.md`, new.
- `tools/proofs/README.md`: a paragraph and a table for the shared session, and `-d shared` in the build commands. Its opening sentence and the `Kernel.thy` row lose a semicolon each, for the writing rules.
- `tools/proofs/ledger/README.md`: a row for `Agreement.thy`.
- No ontology README changed, so no release note and no version.
