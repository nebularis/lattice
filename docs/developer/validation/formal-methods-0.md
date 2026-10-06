<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: formal-methods track D, the prover spike

**Unit:** [formal-methods](../status/formal-methods.md), track D
**Plan:** [formal-methods-phase-0.md](../plans/formal-methods-phase-0.md)
**Branch:** `fm/phase-0-prover-spike`, which may never merge (plan §7.1). This brief, the report
and the status record are the only things that must reach `main`
**Decides:** FM-D1 (the proof assistant, or none) and FM-D10's Haskell question
**Prior art reused, not reinstalled:** the general toolchain-feasibility spike
(`.local/formal-methods-spike/`, 2026-10-06) already installed opam, Rocq, GHC and Isabelle on
this host and built the container images track D's environment layer (slice D0) now wraps

This is the slice D1 brief: the written semantics both tracks formalise, the defects each must
catch, the one scripted MINOR change, the measures and their weights, the claim and gate scripts'
shape, and the fairness rules. D2 and D3 build against it without changing it. D4 scores against
it.

---

## 1. Invariant

Both tracks (Rocq, D2; Isabelle/HOL, D3) formalise the **same** written semantics below, from the
**same** source (this brief and the Eligibility README), under the **same** measures (§5), on the
**same** host and route (the image route, epic formal-methods §4), so that a difference in score
reflects the provers, not the spike's conduct of them. Neither track may read the other's sources
before D4 totals the measures (plan §8 fairness rules, repeated in §7 below).

## 2. Written semantics

### 2.1 The logic kernel (target TA)

A `Decision` is one of three values: `Permitted`, `Denied`, `Undetermined`. Read these as logical
values in Belnap and Fitting's strong Kleene sense, under the **information order** `⊑`:

$$ u \sqsubseteq x \iff u = \mathrm{Undetermined} \lor u = x $$

`Undetermined` is below every value, including itself; `Permitted` and `Denied` are each other's
own fixed point only (incomparable).

Strong Kleene disjunction (`or3`) and conjunction (`and3`):

| `or3 a b` | `b = Permitted` | `b = Denied` | `b = Undetermined` |
|---|---|---|---|
| `a = Permitted` | Permitted | Permitted | Permitted |
| `a = Denied` | Permitted | Denied | Undetermined |
| `a = Undetermined` | Permitted | Undetermined | Undetermined |

| `and3 a b` | `b = Permitted` | `b = Denied` | `b = Undetermined` |
|---|---|---|---|
| `a = Permitted` | Permitted | Denied | Undetermined |
| `a = Denied` | Denied | Denied | Denied |
| `a = Undetermined` | Undetermined | Denied | Undetermined |

Negation (`neg3`): `Permitted ↦ Denied`, `Denied ↦ Permitted`, `Undetermined ↦ Undetermined`.

**TA1 (monotonicity).** `or3` and `and3` are monotone in `⊑`, in each argument:
$$ a \sqsubseteq a' \implies or3(a,b) \sqsubseteq or3(a',b) \qquad a \sqsubseteq a' \implies and3(a,b) \sqsubseteq and3(a',b) $$
and symmetrically in the second argument.

**TA2 (negation).** `neg3` is an order-reversing involution that fixes `Undetermined`:
$$ neg3(neg3(a)) = a \qquad a \sqsubseteq a' \implies neg3(a') \sqsubseteq neg3(a) \qquad neg3(\mathrm{Undetermined}) = \mathrm{Undetermined} $$

### 2.2 Eligibility's set readings and negation (target TL): L15 and L16

Source: `ontology/eligibility/README.md` §6 (`elg:L15`, `elg:L16`), ADR-A103,
`tools/mork_compilers/src/mork_compilers/sparql_backend.py` (`_read_set`, `_negate`), and the
oracle fixtures in `tools/mork_compilers/src/mork_compilers/test_set_readings.py`
(`ReadingTests`, `NegationTests`). A bound condition whose binding reads several values first
decides **each value** as a single candidate would (a separate law, not this spike's target),
giving a list of per-value `Decision`s, `xs : list Decision`. L15 then combines that list; L16
then negates the combined result.

**SomeValue** (`elg:SomeValue`) and **EveryValue** (`elg:EveryValue`), defined over a nonempty
fold and a stated empty case:

```
some_value []        = Undetermined
some_value (x :: xs) = fold_left or3  x xs

every_value []        = Undetermined
every_value (x :: xs) = fold_left and3 x xs
```

**TL1 (L15's statement, as the law's prose states it, independent of the fold).**

$$ some\_value(xs) = \mathrm{Permitted} \iff \mathrm{Permitted} \in xs $$
$$ some\_value(xs) = \mathrm{Denied} \iff xs \neq [] \land \forall x \in xs,\ x = \mathrm{Denied} $$
$$ some\_value(xs) = \mathrm{Undetermined} \iff xs = [] \lor (\mathrm{Permitted} \notin xs \land \mathrm{Undetermined} \in xs) $$

and the dual for `every_value`, swapping `Permitted` and `Denied`.

**TL2 (monotonicity, L15 lifted from TA1).** Lift `⊑` pointwise to equal-length lists
(`Forall2 (⊑)`). Then:
$$ xs \mathrel{Forall2(\sqsubseteq)} ys \implies some\_value(xs) \sqsubseteq some\_value(ys) $$
and the same for `every_value`. (Proved by induction on the list, reusing TA1 at each step: this
is the architectural reason L15's reading and L16's negation compose the way the kernel's
connectives do, rather than needing their own monotonicity argument.)

**TL3 (negation after reading, L16, and where a plausible alternative disagrees).** L16's own
words: the condition "is evaluated as it stands, **including its value reading**, and **then**"
negated. That order matters, and the spike records two comparisons, not one:

- **(a) Holds always — De Morgan duality.**
  $$ neg3(some\_value(xs)) = every\_value(map\ neg3\ xs) $$
  Negating the combined `SomeValue` result equals reading the negated per-value list under
  `EveryValue`. This is a theorem (provable by induction from TA1/TA2), not a coincidence of the
  fixtures: it is the general strong Kleene duality between `∨` and `∧` restated for folds.
- **(b) Fails in general — a wrong alternative L16 rules out.** Negating each value first and
  **keeping the same** reading is *not* the same as negating the combined result:
  $$ neg3(some\_value(xs)) \neq some\_value(map\ neg3\ xs) \quad\text{in general} $$
  Witness: `xs = [Permitted; Denied]`. `some_value(xs) = Permitted` (any value Permitted), so the
  correct, L16-stated result is `neg3(Permitted) = Denied`. The wrong alternative computes
  `map neg3 xs = [Denied; Permitted]`, then `some_value([Denied; Permitted]) = Permitted` (it too
  has a Permitted member) — **Permitted, not Denied**. The two disagree. This is exactly the
  confusion L16's "evaluated as it stands... and then" guards against, and is why TL3 states both
  directions rather than only the positive one.

### 2.3 The adequacy oracle

`tools/mork_compilers/src/mork_compilers/test_set_readings.py` fixes six value mixes against a
hierarchical-match condition where `a`, `a2` are Permitted, `b`, `bx` are Denied and `stranger` is
Undetermined (outside the bound scheme):

| Mix | Values | `SomeValue` (tested) | `EveryValue` (tested) |
|---|---|---|---|
| `pd` | `[Permitted; Denied]` | Permitted | Denied |
| `dd` | `[Denied; Denied]` | Denied | (not asserted; Denied by TL1) |
| `du` | `[Denied; Undetermined]` | Undetermined | Denied |
| `pp` | `[Permitted; Permitted]` | (not asserted; Permitted by TL1) | Permitted |
| `pu` | `[Permitted; Undetermined]` | Permitted | Undetermined |
| `none` | `[]` | Undetermined | Undetermined |

`NegationTests.test_negated_bound_condition_swaps_decided_outcomes` additionally asserts that
negating a `SomeValue`-read condition swaps every one of these per-subject outcomes
(`Permitted ↔ Denied`, `Undetermined` fixed) — the adequacy evidence for TL3(a), read at the
"after reading" point L16 specifies.

Each track's adequacy step (plan §2.1) evaluates `some_value`/`every_value`/`neg3 ∘ some_value`
against this table inside the prover (`Eval`/`compute` or `value`/`code_simp`) and shows every row
matches. A row that does not match is an adequacy failure, not merely a proof failure, and is
reported as such (plan's chain, "adequacy" link).

## 3. Seeded defects, as patches

Each defect is a one-definition change applied to an otherwise-working development, to measure
whether, and how automatically, each track's tooling catches it (M1). Applied and reverted one at
a time; never combined.

| # | Patch | Breaks | Expected symptom |
|---|---|---|---|
| S1 | `some_value [] := Permitted` (was `Undetermined`) | TL1's third clause; the `none` row of §2.3 | the adequacy row fails; TL1 as stated is no longer provable for the empty case |
| S2 | `neg3 Undetermined := Denied` (was `Undetermined`) | TA2's third clause | TA2 fails to prove; `neg3 ∘ neg3 ≠ id` on `Undetermined` |
| S3 | an interface assumption no instantiation can discharge: a module/locale `ReadingInterface` assuming `∀ xs, some_value xs = every_value xs` (false in general: `xs = [Permitted; Denied]` gives `Permitted ≠ Denied`) | non-vacuity (track A5's concern, surfaced at this scale): any theorem proved *from* the interface is proved of nothing real | instantiating the interface with the real `some_value`/`every_value` fails to discharge the assumption |
| S4 | a theorem left with `Admitted.` (Rocq) / `sorry` (Isabelle) | the assumption audit (AR5 of [assurance-records.md](../sketches/assurance-records.md)) | the gate script's source/assumption scan finds the marker and fails the claim |
| S5 | TA1 restated under its old name with a strictly weaker conclusion (`or3 a b ⊑ or3 a b` instead of the real monotonicity statement) | nothing logically (the weak statement is trivially true) | the **statement digest** (AR9) changes though the name does not, and the gate fails the unreviewed restatement (assurance-records.md §5, "no unreviewed restatement") |

S1–S2 and S5 are caught by both tracks' core toolchain (type-checking/`Qed`/`done`, plus a digest
compare). S3 and S4 probe the surrounding assurance tooling (the interface and the gate script)
more than the prover itself. S3's non-vacuity phrasing and S4's "left with `Admitted`/`sorry`" are
the plan's own words (formal-methods-phase-0.md §3).

## 4. The MINOR change, scripted

"A fourth value reading is added to L15" (plan §4, M3), modelled as a closed sum type so the
change is a genuine exhaustiveness break, not a cosmetic one:

```
Inductive reading := SingleValueR | SomeValueR | EveryValueR.

apply_reading SingleValueR xs single = single
apply_reading SomeValueR   xs _      = some_value xs
apply_reading EveryValueR  xs _      = every_value xs
```

The scripted change adds one constructor, `MostValueR` (majority rule: `Permitted` if strictly
more values are `Permitted` than `Denied`, `Denied` if strictly more are `Denied`, else
`Undetermined`, with the empty list `Undetermined`), and measures the tokens and lines to repair
every proof and pattern match the addition breaks (every `match`/`case` over `reading` that is no
longer exhaustive, and any lemma stated by enumerating the three prior constructors). This is a
MINOR, backward-compatible addition in LATTICE's own versioning terms (ADR-A86, ADR-A113): nothing
existing is removed or renamed, matching "the kind of change a real release makes."

## 5. Measures, weights and scoring

Reproduced from formal-methods-phase-0.md §4 for completeness; that plan is the source of truth
if the two differ after a later edit.

| # | Measure | Weight |
|---|---|---|
| M0 | cost to carry the law end to end (tokens, wall time, both laws) | 20 |
| M1 | counterexample finding for S1–S3 (automatic or not, wall time, readability) | 15 |
| M2 | proof effort and agent success for TA1–TL3 | 15 |
| M3 | proof-repair cost under §4's scripted MINOR change | 15 |
| M4 | generated OCaml: size, readability, native type mapping, unsafe casts | 5 |
| M5 | other code-generation targets (Haskell, Scala, N-version agreement) | 5 |
| M6 | architecture fit: interface design, a typing error vs. a definitional theorem (§6 below) | 10 |
| M7 | toolchain and CI: image size, pull/build time, memory/CPU, `mise` integration, native install | 5 |
| M8 | library fit: lattices, orders, Datalog/SQL semantics, licences | 5 |
| M9 | consistency with the engine notes' prior choice of Rocq | 5 |

Each measure is scored 0 to 10 per prover in D4, from the evidence D2 and D3 produce. §5 of the
plan gives the decision rule (weighted sum, a margin under 5 points is a tie broken by M0 then
M3) and the abandonment rule (neither track completes the chain within its budget ⇒ do not start
track E; A, B, C continue regardless).

### 5.1 M6 in this spike's scope

Target TA/TL carries no `DesignEnv`/`RunEnv` distinction (that is track B4's reference evaluator,
later). M6 is scored here on a smaller, concrete instance of the same question the plan poses
("a typing error... and a definitional guarantee with a theorem"): an interface requiring *"a
function from `list Decision` to `Decision`, monotone in `⊑`"* (§3's `ReadingInterface`, S3). Rocq
can refuse a non-monotone candidate implementation **at construction time** (a dependent record
packing the function with its monotonicity proof makes an unproved candidate ill-typed). Isabelle's
`locale`/`interpretation` instead requires the assumption to be **discharged as a proof
obligation** when the locale is interpreted, which is a build failure, not a type error. Both
reject the bad candidate; the spike records which point in the pipeline rejects it and how legible
the rejection is to someone who is not a type theorist. A full `DesignEnv`/`RunEnv` comparison is
explicitly deferred to track E and is not scored here.

## 6. Claim and gate scripts (spike form)

Both tracks share one claim shape and one gate script, so that track D itself produces evidence in
the shape track A's assurance profile will later require (assurance-records.md, FM-D3 — the `asr:`
prefix there is provisional, and is repeated here unchanged, not finalised by this spike).

- **`spikes/formal-prover/claim-schema.json`**: a JSON Schema for one claim record: `subject`
  (which theorem/law), `statedAs`, `statementDigest` (sha256 of the normalised statement text),
  `method` (`Proof` for TA1/TA2/TL1–TL3, `Review` for the adequacy table), `scope`,
  `assumptionAudit` (the prover's own assumption listing, verbatim), `tool` (name, version, image
  or archive digest — FM-D15, epic §4), `outcome` (`passed`/`failed`).
- **`spikes/formal-prover/gate.py`**: for one track's claims directory, (a) recomputes each
  statement digest from the theory source and fails on an unreviewed mismatch (S5), (b) scans the
  theory sources for `Admitted`/`admit`/`sorry`/`oracle`/`axiomatization` outside an explicitly
  allow-listed defect file, and fails if found (S4), (c) prints a one-line law report row per
  claim. Each track's own `claims/*.json` and `gate.py`'s pass/fail output are evidence for D4,
  not graded pass/fail themselves — the gate is infrastructure both tracks share, built once.

## 7. Fairness rules

Repeated from the plan (§8) because D2 and D3 must both honour them without re-reading it:

1. One model, one agent configuration, for both tracks, on one host, on the image route.
2. Both start from this brief (§2) and the Eligibility README, not from each other's sources.
3. The order the tracks are built in is recorded in the report (plan §4's slice order: D2 then
   D3), and D4 weighs whether the second may have benefited from the first.
4. A target not finished within its budget (D2/D3: capped at 0.25M tokens each) is scored as not
   finished, not scored partially.

## 8. Artefacts to inspect

- `spikes/formal-prover/env/`: the D0 environment layer (driver, images, `mise` tasks), already
  built and smoke-tested before D1 was written.
- `spikes/formal-prover/rocq/`: D2's theories, proofs, defect patches, the MINOR-change diff,
  extraction output, claims.
- `spikes/formal-prover/isabelle/`: D3's theories, proofs, defect patches, the MINOR-change diff,
  `export_code` output, claims.
- `docs/developer/notes/formal-prover-experiment.md`: the D4 report, scored against this brief.

## 9. Deliberate non-coverage

Binding resolution and scheme composition (track C). The evaluation context, `DesignEnv`/`RunEnv`
and Behaviour's macrostep (track B4, track E). Any condition kind other than the one L15/L16
govern (interval, exact/set/hierarchical match are a separate law, assumed correct here and fed as
already-decided `Decision`s). Performance benchmarking beyond M7's toolchain measures (track F).
Lean 4 (plan §1). Running generated code against the live graph (epic §3, out of scope entirely).

## 10. Handoff

Written before D2 and D3, as the plan requires. Updated only if a defect in this brief is found
during D2/D3 (recorded as a change, not a silent edit, per the gate's own "no unreviewed
restatement" rule applied reflexively to the brief itself).
