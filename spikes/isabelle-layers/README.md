# Isabelle/HOL models of the LATTICE layers

A spike, not yet aligned to the formal-methods track (no claim records, no gate markers, no literate extraction). One theory per layer, each stating the laws its README states and proving what can be proved of them without a reasoner. The session extends the committed `Eligibility` session so that the kernel's connectives and closed set readings are reused rather than restated.

## Build

From the repository root:

```bash
isabelle build -d tools/proofs/eligibility -d spikes/isabelle-layers LatticeLayers
```

A pass prints `Finished LatticeLayers`. The session loads `HOL-Library`'s code adaptations from source for `CodeGen`, so no `HOL-Library` heap is needed. Every theorem is kernel-checked, with no `sorry`, `oops`, `axiomatization` or `by eval`. Locales carry the assumptions a theorem rests on, named at its head.

## Status

All thirteen layer theories and the two code-generation theories build, and every theorem in them is proved. Two statements were corrected during proof, and both are findings rather than proof engineering: a padded position reads back as its value only when the value fits the width (Minting's `val_dp` carries that premise, and width zero reads back nothing), and profile resolution's tie is Ambiguity only when no top candidate avoids reasoning (Persistence's `tie_is_ambiguity` and `reasoning_tie_is_ambiguity`), since the rule prefers one that does.

## What each theory proves

| Theory | Source | Main results |
|---|---|---|
| `Foundation` | Foundation §4, §6 to §8, ADR-A137 | a finite acyclic supersession chain is irreflexive and asymmetric, keeps one identity, and ends at a latest version, unique when succession is functional. The key chain `externalKey ⊒ hasIdentity ∘ externalKey` locates a version by its identity's keys and is a fixpoint. The reproducibility theorem: a judgement from a version whose meaning-bearing targets are immutable is the same in every store state, with a counterexample for a mutable target |
| `Temporal` | Foundation §7, Quantification Q14 | half-open zoned validity: abutting periods are disjoint, an empty period holds nothing, the start is in and the end is out. Overlap of non-empty periods is exactly the two FILTERs of Vocabulary's conflict shape, and not for empty ones. Month arithmetic clamps the day, stays valid, is monotone in the day, and is not two additions of one month |
| `Quantification` | Quantification §5.1, §6, §9, §10 | closed and open limits (Q2), the meet of ranges is exact (Q4a and Q4b), overlap screens and is not complete, with the README's own counterexample (Q5), granularity never coerces and refinement keeps a definite answer (Q10), cyclic ranges are periodic with the two degenerate cases and the wrapping window, truncated difference keeps a zero-bounded space non-negative (Q8), a sum is definite exactly over like values (Q13) |
| `Vocabulary` | Vocabulary §4, §5.1, §7.2, ADR-A85 | resolution is local to the applicable bindings, a winner is applicable and valid at the time (invariant 7), the winner's scopes include every applicable binding's (dominance), equal specificity never wins and the shape's condition is a moment where neither can (invariant 4), fallback agreement keeps one scheme across a scopeless binding's boundary (invariant 6), closures never extend validity and the earliest ends it |
| `Behaviour` | Behaviour §5.3, ADR-A106, Instrument §11.3 | on a proper state tree default entry gives a well-formed configuration (B11), well-formedness is local to a subtree, a composite holds exactly when occupied, exit clears the subtree and history restores a well-formed configuration (B5), an internal transition changes nothing, the gate rule with its truth table, and a pass terminates when derived triggers are acyclic (B10) |
| `Ledger` | track E's E4a laws, ADR-A131 | a draw succeeds or fails whole, settling keeps balances non-negative, conservation per account, draws at one position settle independently of proposal order, and a pro-rata split conserves its total through rounding with a residual below the number of parts |
| `Instrument` | Instrument §4.4, §4.5, §13, §14, I5, I9, I10 | Hohfeld's correlation is an involution pairing distinct conceptions, one modal verb per class, a stated range resolves per occasion by translation and an unbound role is Undetermined (I9), exercise outside a window has no effect and a closed window lapses (I10), tolling never advances a deadline and adds up, gates stay out of design-time comparison (DP6) |
| `Party` | Party §4, §6, §9, I11 | own shares cover the whole when they sum to one, under each-for-whole a payer recovers one less its inward share, silence is undetermined, filling an occupancy is a new version that keeps its role and leaves the old version open |
| `Persistence` | Persistence §5.1, §5.3, §5.5.3, §5.6.2, §5.6.3, §5.6.6, §5.6.8, TD-118 | Applied exactly when the guard held, every other outcome names a guard that failed, key reuse is reported, no lost update, dense sequences, writes are local and retries idempotent, a bump orders every new position above every old one, the dataset guard refuses a stale writer and a row-level guard admits one (the TD-118 witness), key claims give one owner, monotonic ownership and a definitive follow-up read, profile resolution picks the top priority and a tie is Ambiguity |
| `Membership` | Persistence §5.6.11, ADR-A132 | delta-encoded members read back exactly, a member dropped and added again is a member, the nearest checkpoint is one, nothing between is, and no chain is longer than the interval |
| `Minting` | identity minting specification §3 to §6 | the length-prefixed tuple encoding is injective, instantiated with decimal, percent-encoding decodes and never emits a slash, dot segments collide or escape and the refusal restores injectivity, zero-padded positions order as numbers and overflow breaks read-back, null and empty scope collide without the EmptyScope refusal |
| `Surface` | Surface §8, §9, §11 | the local-name policy collides across namespaces and the digest policy does not, staleness is exactly a changed read-set hash, materialisation is idempotent (R4), closure relations are reflexive, stepwise and scoped, traversal terminates on an acyclic basis (R5), a local-signature surface is conservative over the source signature and the property composes (X1) |
| `EligibilityConditions` | Eligibility §5.1, §5.2, L9 to L14 | the decision table as a function: absent or out-of-scheme candidates are Undetermined, exclusion precedence (L10), exclusion granularity (L11), default inclusion (L12), the flat-scheme precondition (L14) with closure reduced to equality, exclusions only narrow, and profile composition is the kernel's closed readings with their characterisations, monotonicity and set invariance |

## What is deliberately not here

- SPC's session types and MORK's notation: nothing in their READMEs is stated as a law of the kind these theories prove.
- Entailment regimes: Surface's X1 is proved over asserted triples only.
- Q3's canonical form for range sets and Q6's conversion coherence: both need a representation decision (dense against discrete spaces, conversion chains) the README leaves to a profile.
- Store isolation: Persistence's model applies writes one at a time, which is what a store's atomic update promises and nothing more. Write skew between updates is the conformance test's.

## Generating an evaluator

The question was what generating an evaluator from these models looks like. Everything below was run on Linux x86_64 with 4 cores and 15 GB, Isabelle2025-2, GHC 9.4.7 and Isabelle's own Scala 3.3.4, on 2026-10-30. Generated code was written outside the repository and never enters git.

Two theories hold the work. `CodeGenPlain` gives the code equations and exports Haskell under the code generator's default representations. `CodeGen` imports it, adds `HOL-Library.Code_Target_Numeral` and `HOL-Library.Code_Abstract_Char`, evaluates the models with `value` and exports Haskell, SML and Scala. A clean build of the session took 26 s, and the largest single process peaked at 4.3 GB resident.

### What executes

| Fragment | As written | What it needed |
|---|---|---|
| Quantification's ranges, meet, cyclic windows and sums, Temporal's month arithmetic | executes | nothing |
| Minting's percent-encoding, dot segments and fixed-width positions | executes | nothing |
| Minting's tuple encoder | no code equations | `enc` was a `fun` inside the locale `length_prefix`, whose equations are conditional on the locale's assumptions. It now takes the length rendering as its first argument, and the locale states `enc_injective` about `enc lenstr`. `tuple_encoding_injective` is unchanged in meaning |
| Ledger's settlement and pro-rata split, Behaviour's configurations and gate, Instrument's anchors and windows, the eligibility composition, key claims | executes | nothing |
| Persistence's `guard`, `guard_row` and `confirm` | not executable | each quantifies existentially over the row option, which the generator could only run by enumerating the row type. A case split, proved equal to the definition, is the code equation |
| Vocabulary's `resolve` and Persistence's `resolve_dim` | not executable, `Type ... not of sort enum` | the test for one winner is `∃w. S = {w}` and the winner is `THE w. S = {w}`. HOL's `is_singleton` and `the_elem` say the same and execute on a finite set, so a code equation restates each over them. Sets did not need restating as lists, because set literals already execute, and `Max` over one executes too |
| Eligibility's `scheme.decide` and `scheme.below_eq` | `No code equations for scheme.decide` | the hierarchical match is a reflexive-transitive closure of `broader`, given as a predicate inside the locale `scheme`, which has no interpretation. It needs the relation as a finite set of pairs, so that `rtrancl`'s own code equations apply, and either an interpretation or explicit parameters to give the generator a constant. Not done here |
| Membership | not exercised | its definitions sit in a locale with no interpretation, the same obstacle as `scheme` |

### What the representations cost

Under the default representations `nat` is a Peano datatype, `int` is built over binary numerals, and `char` is a datatype of eight booleans. `value "dp 19 (91438 :: nat)"` computes ten to the eighteenth in unary and did not finish, which is why the first build of `CodeGen` ended in the session's 600 s timeout. With the adaptations `nat` and `int` are newtypes over the target's integers, `char` is a newtype over an integer, and the same value prints `0000000000000091438`. `Code_Abstract_Char` also changes how `value` prints a string, as a list of `Chr` codes.

| Export | Files | Size | Compiles |
|---|---|---|---|
| Haskell, default representations | `Lattice.hs`, `Str_Literal.hs` | 1,985 lines, 57.5 KB | `ghc -O0`, no warnings |
| Haskell, with the adaptations | `Lattice.hs`, `Bit_Shifts.hs`, `Str_Literal.hs` | 1,136 lines, 35.8 KB | `ghc -O0`, no warnings |
| Scala, with the adaptations | `lattice_scala.scala` | 716 lines, 24.8 KB | `isabelle scalac`, no warnings. It first warned that three pairs of generated classes differ only in case, such as `Lattice$Nat` and `Lattice$nat`, which overwrite each other on a case-insensitive filesystem such as macOS's default. `CodeGen` renames the three constructors for Scala with `code_identifier`, and any new datatype whose constructor shares its name with its type will need the same |
| SML, with the adaptations | `lattice_sml.ML` | 463 lines, 16.1 KB | exported, not compiled on its own |

The generated modules export their types without constructors, so a caller cannot build a `Nat` or a `Char`. Both theories export `nat_of_integer`, `integer_of_nat`, `char_of_integer`, `integer_of_char`, `String.explode` and `String.implode` for that reason.

### Against the specification

A driver of twenty-three lines called the exported functions and printed the results. The same driver ran against both Haskell builds, and a Scala translation of it against the Scala build.

| Call | Specification | Haskell, adapted | Haskell, default | Scala |
|---|---|---|---|---|
| `enc decimal ["v1", "person-email-unique", "acme", "ada@example.org"]` | `2:v119:person-email-unique4:acme15:ada@example.org` (§4.1) | same | same | same |
| `pct` of the bytes of `a/b` | `a%2Fb` (§6.2) | `[97,37,50,70,98]`, which is `a%2Fb` | same | same |
| `dec` of that | `a/b` | `[97,47,98]` | same | same |
| `dp 19 91438` | nineteen digits, zero-padded | `0000000000000091438` | no output within 60 s | same as adapted |
| TD-118 witness, `guard` and `guard_row` on the stale store and request | false and true | false, true | not reached | false, true |

`tuple_bytes` and `percent_encode` in `packages/minting/python` give the same two strings. The model's strings are byte strings, so a non-ASCII component has to reach `enc` as its UTF-8 bytes, where the Python library encodes it itself.

### As a reference evaluator

A hypothesis, not a decision. The generated Haskell could stand beside the Python reference in `tools/reference/eligibility` as a differential oracle for the fragments that execute, under four conditions.

- The trust base is stated. The theorems hold of the Isabelle definitions. The generated code adds the code generator, the target compiler and the adaptations' mapping of `nat`, `int` and `char` onto target integers, none of which the kernel checks.
- It covers what the models cover. These theories state a layer's laws, not its whole behaviour, and the eligibility decision table does not yet execute, so a comparison with the Python reference starts with the minting encodings, the persistence guards, the ledger split and the composition of decisions.
- The adaptations are always on. Without them an ordinary fixed-width position does not terminate, so the default representations are fit for nothing beyond small values.
- A thin layer adapts the interface. It converts between the target's integers and strings and the generated types, and between Unicode text and UTF-8 bytes, and the same conformance vectors the Python reference reads would have to be run through it.

Track E's E2, a proved SPARQL compiler core, is a different object. This spike shows only that the extraction path runs end to end at this scale.
