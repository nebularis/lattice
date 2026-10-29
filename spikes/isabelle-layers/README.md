# Isabelle/HOL models of the LATTICE layers

A spike, not yet aligned to the formal-methods track (no claim records, no gate markers, no literate extraction). One theory per layer, each stating the laws its README states and proving what can be proved of them without a reasoner. The session extends the committed `Eligibility` session so that the kernel's connectives and closed set readings are reused rather than restated.

## Build

From the repository root:

```bash
isabelle build -d tools/proofs/eligibility -d spikes/isabelle-layers LatticeLayers
```

A pass prints `Finished LatticeLayers`. Every theorem is kernel-checked, with no `sorry`, `oops`, `axiomatization` or `by eval`. Locales carry the assumptions a theorem rests on, named at its head.

## Status

All thirteen theories build and every theorem in them is proved. Two statements were corrected during proof, and both are findings rather than proof engineering: a padded position reads back as its value only when the value fits the width (Minting's `val_dp` carries that premise, and width zero reads back nothing), and profile resolution's tie is Ambiguity only when no top candidate avoids reasoning (Persistence's `tie_is_ambiguity` and `reasoning_tie_is_ambiguity`), since the rule prefers one that does.

## What each theory proves

| Theory | Source | Main results |
|---|---|---|
| `Foundation` | Foundation §4, §6 to §8, ADR-A142 | a finite acyclic supersession chain is irreflexive and asymmetric, keeps one identity, and ends at a latest version, unique when succession is functional. The key chain `externalKey ⊒ hasIdentity ∘ externalKey` locates a version by its identity's keys and is a fixpoint. The reproducibility theorem: a judgement from a version whose meaning-bearing targets are immutable is the same in every store state, with a counterexample for a mutable target |
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
