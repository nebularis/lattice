<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# The HOL sessions, and what LATTICE's proofs can draw on

**Status:** survey, 2026-11-08, for LG-Q14 and the formal-methods epic. **Source:** `src/HOL/ROOT` of Isabelle2025-2, the distribution installed on machine R, read by a script that counted the theory files under each session's directory and their size in kilobytes. The counts are the distribution's, the readings of what each session holds and what it bears on are ours, from the theory names and what we know of them, not from reading every theory. Nothing here measures a build time except the one figure in section 5. The Archive of Formal Proofs is not installed here and is not surveyed.

## 1. Why a survey

LG-Q14 asks how the ledger's proof session reaches `HOL-Library`. The answer depends on how many library theories our proofs will want over time and how many sessions will want them, since a theory loaded from source is checked again by every session that imports it, where a theory in a parent's heap is checked once per machine. This survey lists every session the distribution declares, what Main already gives without any of them, which library theories each of our proof areas is likely to reach for, and what that implies for the shape of `tools/proofs/`.

The proof areas are the ones the plans name or foresee. The ledger's laws (LG-7, LG-8). The ensemble's composition law, least fixpoint over the information order and chaotic iteration for cyclic components (E4b, E4c). Terms in time, periods, recurrences and regimes, and spans of them. Eligibility's three-valued conditions. Behaviour and instrument, state over a sequence of events. Quantification, value spaces and rounding. And every reference evaluator, test vector and oracle generated from a theory.

## 2. What Main already gives

`Main` and `Complex_Main`, which the ledger kernel imports, are the `HOL` session, 115 theories. Nothing below is an import. Orders, lattices and complete lattices as type classes with `lfp` and `gfp` and the Knaster-Tarski theorem (`Complete_Lattices`, `Inductive`), chain-complete partial orders with `ccpo.fixp` (`Complete_Partial_Order`), conditionally complete lattices and the reals and rationals as ordered fields (`Rat`, `Real`, `Archimedean_Field`), finite sets with big operators (`Finite_Set`, `Groups_Big`, `Lattices_Big`), lists with `sort_key`, `sorted`, `distinct` and their algebra (`List`), finite maps as functions (`Map`), intervals of an order (`Set_Interval`), transitive closure (`Transitive_Closure`), well-founded recursion and the function package (`Wellfounded`, `Fun_Def`), partial functions by fixpoint (`Partial_Function`), records, datatypes and codatatypes (the BNF theories), equivalence relations and quotients, the code generator with its numeral representation (`Code_Numeral`), and limits, series, derivatives and transcendental functions over ℝ and ℂ (`Complex_Main`).

The fixpoint over the information order that E4b needs is therefore statable in Main alone, as a least fixpoint of a monotone function over a complete lattice or a ccpo. The library adds the second-order results about it, continuity and a product or option order ready made, and the iteration combinator E4c would evaluate with.

## 3. Every session

81 sessions, the children of `HOL` and theirs. Theories and KB are the files under the session's directory, a proxy for what loading it from source would check. A session whose parent is not `HOL` needs that parent built first, as a heap.

### The core

| Session | Parent | Theories | KB | What it holds | Bears on |
|---|---|---|---|---|---|
| `HOL` | `Pure` | 115 | 4,680 | the logic and Main, with Complex_Main. Everything LG-7 uses | all, as the parent today |
| `HOL-Library` | `HOL` | 151 | 2,662 | the batteries, 151 theories, each importable on its own | all, see section 4 |
| `HOL-Examples` | `HOL` | 18 | 99 | notable examples, Knaster-Tarski among them | ensemble, Knaster_Tarski as a four-line reading of the fixpoint theorem |
| `HOL-Eisbach` | `HOL` | 7 | 48 | the Eisbach proof-method language | all, as a tool for writing repeated proof patterns once, if the claims grow |

### Orders, fixpoints and domain theory

| Session | Parent | Theories | KB | What it holds | Bears on |
|---|---|---|---|---|---|
| `HOL-Lattice` | `HOL` | 4 | 56 | orders, lattices and complete lattices, an older small development | ensemble, superseded by Main's classes |
| `HOL-Algebra` | `HOL-Computational_Algebra` | 49 | 1,640 | groups, rings, modules, lattices and complete lattices as locales, Galois connections | ensemble, for a locale-based information order, though Main's classes usually suffice |
| `HOLCF` | `HOL` | 111 | 930 | domain theory, cpos, continuous functions, fixpoints, the domain package | ensemble, if the composition law is stated as a least fixpoint of a continuous function over a cpo rather than over a complete lattice |
| `HOLCF-Library` | `HOLCF` | 12 | 110 | cpos for lists, options, sums, streams | ensemble, with HOLCF |
| `HOLCF-Tutorial` | `HOLCF` | 3 | 16 | tutorial | none |
| `HOLCF-ex` | `HOLCF-Library` | 11 | 91 | examples | none |
| `HOLCF-FOCUS` | `HOLCF-Library` | 6 | 50 | stream-processing functions | none |
| `HOLCF-IMP` | `HOLCF` | 2 | 3 | denotational IMP in HOLCF | none |
| `IOA` | `HOLCF` | 50 | 297 | I/O automata in HOLCF | none |
| `IOA-ABP` | `IOA` | 12 | 22 | example | none |
| `IOA-NTP` | `IOA` | 11 | 37 | example | none |
| `IOA-Storage` | `IOA` | 4 | 4 | example | none |
| `IOA-ex` | `IOA` | 2 | 4 | example | none |
| `HOL-IOA` | `HOL` | 3 | 20 | I/O automata metatheory in HOL | none, see IOA under HOLCF |

### Data structures and code generation

| Session | Parent | Theories | KB | What it holds | Bears on |
|---|---|---|---|---|---|
| `HOL-Data_Structures` | `HOL` | 55 | 425 | verified search trees, heaps, priority queues, tries, an interval tree, with running-time functions | export, for executable maps and sets with proved bounds, and time, for the interval tree |
| `HOL-Imperative_HOL` | `HOL` | 15 | 206 | a heap monad with arrays and references, for imperative code generation | export, if an evaluator is ever generated imperatively |
| `HOL-Codegenerator_Test` | `HOL-Library` | 21 | 20 | tests of code generation | export, as examples of the target adaptations |

### Arithmetic, algebra and analysis

| Session | Parent | Theories | KB | What it holds | Bears on |
|---|---|---|---|---|---|
| `HOL-Decision_Procs` | `HOL-Algebra` | 21 | 1,178 | decision procedures by reflection, linear arithmetic over ordered fields, interval approximation | ledger and quantification, for arithmetic over ℚ in proofs about rounding, if the built-in methods fall short |
| `HOL-Computational_Algebra` | `HOL` | 17 | 999 | polynomials, formal power series, primes, fraction fields | none |
| `HOL-Number_Theory` | `HOL-Computational_Algebra` | 14 | 266 | congruences, residues, totients | none |
| `HOL-Combinatorics` | `HOL` | 9 | 203 | permutations, cycles, orbits, Stirling numbers | ledger, if order independence is ever stated over permutations rather than multisets |
| `HOL-Cardinals` | `HOL` | 13 | 244 | ordinals and cardinals | none |
| `HOL-Analysis` | `HOL` | 106 | 8,534 | topology, measure, integration, derivatives in ℝⁿ | none foreseen, and too large to load from source |
| `HOL-Complex_Analysis` | `HOL-Analysis` | 14 | 1,239 | complex analysis over HOL-Analysis | none |
| `HOL-Analysis-ex` | `HOL-Analysis` | 2 | 36 | examples | none |
| `HOL-Homology` | `HOL-Analysis` | 5 | 554 | algebraic topology | none |
| `HOL-Probability` | `HOL-Analysis` | 33 | 1,282 | measure-theoretic probability, distributions, independence, Markov kernels, PMFs | none on the public side today. A parametric trigger's law is about a stated index, not a distribution |
| `HOL-Probability-ex` | `HOL-Probability` | 3 | 50 | examples | none |
| `HOL-Real_Asymp` | `HOL` | 9 | 351 | asymptotics of real functions | none |
| `HOL-Real_Asymp-Manual` | `HOL-Real_Asymp` | 1 | 14 | its manual | none |
| `HOL-Hahn_Banach` | `HOL` | 12 | 105 | one theorem of functional analysis | none |
| `HOL-Nonstandard_Analysis` | `HOL-Computational_Algebra` | 21 | 310 | non-standard analysis | none |
| `HOL-Nonstandard_Analysis-Examples` | `HOL-Nonstandard_Analysis` | 1 | 8 | examples | none |
| `HOL-Matrix_LP` | `HOL` | 8 | 126 | matrices and linear programming | none |

### Programs, semantics and state

| Session | Parent | Theories | KB | What it holds | Bears on |
|---|---|---|---|---|---|
| `HOL-IMP` | `HOL` | 56 | 329 | the IMP language of Concrete Semantics, with abstract interpretation and Hoare logic | ensemble, as a worked model of a least fixpoint semantics and of collecting semantics, to read rather than import |
| `HOL-IMPP` | `HOL` | 5 | 32 | IMP with procedures | none |
| `HOL-Hoare` | `HOL` | 18 | 118 | Hoare logic for imperative programs | none |
| `HOL-Hoare_Parallel` | `HOL` | 16 | 299 | Owicki-Gries for shared variables | none |
| `HOL-Statespace` | `HOL` | 5 | 50 | state spaces as locales with distinct names | behaviour and instrument, as one way to model a record of state with proved distinctness |
| `HOL-TLA` | `HOL` | 18 | 197 | Lamport's Temporal Logic of Actions | time and behaviour, as a reading on stating properties of state over time, not as an import |
| `HOL-TLA-Inc` | `HOL-TLA` | 1 | 13 | example | none |
| `HOL-TLA-Buffer` | `HOL-TLA` | 2 | 8 | example | none |
| `HOL-TLA-Memory` | `HOL-TLA` | 9 | 96 | example | none |
| `HOL-UNITY` | `HOL-Auth` | 44 | 447 | the UNITY program logic | none |
| `HOL-MicroJava` | `HOL` | 60 | 644 | a Java fragment and its VM | none |
| `HOL-NanoJava` | `HOL` | 8 | 46 | a smaller Java fragment | none |
| `HOL-Bali` | `HOL` | 24 | 1,236 | a larger Java formalisation | none |
| `HOL-SPARK` | `HOL` | 24 | 105 | SPARK Ada verification conditions | none |
| `HOL-SPARK-Examples` | `HOL-SPARK` | 15 | 58 | examples | none |
| `HOL-SPARK-Manual` | `HOL-SPARK` | 7 | 39 | manual | none |
| `HOL-Unix` | `HOL` | 2 | 58 | a Unix file-system model | none |
| `HOL-Auth` | `HOL` | 49 | 915 | authentication protocol verification | none |
| `HOL-SET_Protocol` | `HOL` | 7 | 169 | the SET payment protocol | none |

### Logic, metatheory and tools

| Session | Parent | Theories | KB | What it holds | Bears on |
|---|---|---|---|---|---|
| `HOL-Proofs` | `Pure` | 24 | 166 | HOL with explicit proof terms | none |
| `HOL-Proofs-ex` | `HOL-Proofs` | 3 | 9 | examples | none |
| `HOL-Proofs-Extraction` | `HOL-Proofs` | 8 | 44 | program extraction from proofs | none |
| `HOL-Proofs-Lambda` | `HOL-Proofs` | 13 | 112 | lambda calculus metatheory | none |
| `HOL-Nominal` | `HOL` | 24 | 1,235 | nominal datatypes for binders | none |
| `HOL-Nominal-Examples` | `HOL-Nominal` | 23 | 1,117 | examples | none |
| `HOL-Induct` | `HOL` | 14 | 99 | inductive and coinductive definition examples | none |
| `HOL-ZF` | `HOL` | 5 | 81 | ZF set theory inside HOL | none |
| `HOL-Types_To_Sets` | `HOL` | 8 | 101 | the Types-To-Sets extension | none |
| `HOL-Import` | `HOL` | 3 | 12 | import of HOL Light proofs | none |
| `HOL-Prolog` | `HOL` | 4 | 12 | a Lambda Prolog fragment | none |
| `HOL-TPTP` | `HOL` | 15 | 226 | TPTP interchange | none |
| `HOL-Metis_Examples` | `HOL` | 11 | 143 | prover examples | none |
| `HOL-Nitpick_Examples` | `HOL` | 15 | 108 | counterexample finder examples | none |
| `HOL-SMT_Examples` | `HOL` | 6 | 114 | SMT solver examples | none |
| `HOL-Quickcheck_Examples` | `HOL` | 8 | 44 | Quickcheck examples | none |
| `HOL-Mutabelle` | `HOL` | 1 | 3 | a mutation testing tool | none |
| `HOL-Mirabelle-ex` | `HOL` | 0 | 0 | a test case for Mirabelle | none |
| `HOL-Quotient_Examples` | `HOL-Algebra` | 11 | 96 | quotient type examples | none |
| `HOL-Predicate_Compile_Examples` | `HOL` | 16 | 122 | predicate compiler examples | none |
| `HOL-Datatype_Examples` | `HOL-Library` | 24 | 188 | datatype package examples | none |
| `HOL-Corec_Examples` | `HOL-Library` | 17 | 63 | corecursion examples | none |
| `HOL-Isar_Examples` | `HOL-Computational_Algebra` | 12 | 89 | Isar style examples | none |
| `HOL-ex` | `HOL-Library` | 82 | 845 | miscellaneous examples | none, though While_Combinator_Example and Transitive_Closure_Table_Ex show two library theories at work |

## 4. HOL-Library, theory by theory

151 theories, each importable on its own through `sessions "HOL-Library"`, with only the ones named and their dependencies checked. Grouped by what they are for, with the ones our proof areas reach for in bold.

| Group | Theories |
|---|---|
| Orders and lattices | Complemented_Lattices, Countable_Complete_Lattices, Dual_Ordered_Lattice, Finite_Lattice, Lattice_Algebras, Lattice_Constructions, Lub_Glb, **Option_ord**, Preorder, **Product_Order**, Product_Plus, Fun_Lexorder, Lexord, **List_Lexorder**, List_Lenlexorder, Prefix_Order, Product_Lexorder, Subseq_Order, Complex_Order, Multiset_Order |
| Fixpoints and iteration | Bourbaki_Witt_Fixpoint, **Complete_Partial_Order2**, **Order_Continuity**, **While_Combinator**, Partial_Function's companions Monad_Syntax, **Monad_Syntax**, State_Monad, Open_State_Syntax |
| Collections | **Multiset**, DAList_Multiset, Tree_Multiset, **FSet**, Disjoint_FSets, **Finite_Map**, **Mapping**, AList, AList_Mapping, DAList, Dlist, RBT, RBT_Impl, RBT_Mapping, RBT_Set, IArray, NList, ListVector, Tree, Tree_Real, Poly_Mapping, Groups_Big_Fun, FuncSet, Function_Algebras, Function_Division |
| Lists and sequences | **Sublist**, More_List, Sorting_Algorithms, Comparator, Confluence, Confluent_Quotient, **Stream**, **Linear_Temporal_Logic_on_Streams**, Omega_Words_Fun, Diagonal_Subsequence, Cancellation |
| Sets and cardinality | **Disjoint_Sets**, **Set_Algebras**, Set_Idioms, Infinite_Set, Infinite_Typeclass, Countable, Countable_Set, Countable_Set_Type, Cardinality, Equipollence, Indicator_Function, Ramsey |
| Numbers and intervals | **Extended**, **Extended_Nat**, **Extended_Real**, **Extended_Nonnegative_Real**, **Interval**, Interval_Float, Float, Centered_Division, Signed_Division, Discrete_Functions, Log_Nat, Nat_Bijection, Nonpos_Ints, Numeral_Type, Periodic_Fun, Power_By_Squaring, Real_Mod, Saturated, Sum_of_Squares, Quadratic_Discriminant, Landau_Symbols, Liminf_Limsup, Going_To_Filter, Word, Z2, Type_Length, Uprod |
| Code generation | **Code_Target_Numeral**, Code_Target_Int, Code_Target_Nat, Code_Abstract_Nat, Code_Binary_Nat, **Code_Abstract_Char**, Code_Bit_Shifts_for_Arithmetic, Code_Cardinality, Code_Lazy, Code_Prolog, Code_Real_Approx_By_Float, Code_Target_Numeral_Float, Code_Test, Char_ord, Time_Commands, Time_Functions, Time_Manual, Parallel, Debug |
| Datatypes, quotients and transfer | BNF_Axiomatization, BNF_Corec, Datatype_Records, Case_Converter, Pattern_Aliases, Phantom_Type, Combine_PER, Conditional_Parametricity, Quotient_List, Quotient_Option, Quotient_Product, Quotient_Set, Quotient_Sum, Quotient_Syntax, Quotient_Type, Old_Datatype, Old_Recdef |
| Proof tools and syntax | Rewrite, Reflection, Simps_Case_Conv, Transitive_Closure_Table, Predicate_Compile_Alternative_Defs, Predicate_Compile_Quickcheck, Refute, Realizers, Suc_Notation, LaTeXsugar, OptionalSugar, Library, README |

## 5. What loading from source would cost

The one measurement we have is the whole `HOL-Library` session, 2,662 KB of theory text, built as a heap on machine R on 2026-11-08 in 6 min 4 s under a 2.5 GB Poly/ML cap with two threads. A `sessions` clause checks a subset, the theories named and what they import, so a prelude of a dozen theories is a small fraction of that, to be measured on its first build. The three sessions whose size rules out loading from source are `HOL-Analysis` (8,534 KB), `HOL-Algebra` (1,640 KB) and `HOL-Probability` (1,282 KB, over `HOL-Analysis`), and none of our areas reaches for them. `HOLCF` (930 KB) is the one heavy session an area might want, if the ensemble's fixpoint is stated over a cpo, and it would then be a parent with a heap rather than a source import.

## 6. What each proof area reaches for

| Area | In Main | From the library |
|---|---|---|
| ledger, LG-8 | `sort_key`, `sorted_list_of_set`, finite sums, ℚ | `Multiset` for order independence as `mset ps = mset ps'`, `Sublist` for the integer `spread` as a subsequence, `FSet` or `Finite_Map` if key sets and amount vectors become data, `Extended_Nat` if a ceiling ever needs an explicit infinity |
| ensemble, E4b and E4c | `lfp` over a complete lattice with `lfp_unfold` and `lfp_lowerbound`, `ccpo` with `fixp_induct`, Knaster-Tarski | `Option_ord` for an information order with the unknown fact as bottom, `Product_Order` for the pointwise order on an ensemble of facts, `Order_Continuity` for `sup_continuous_lfp`, the fixpoint as the supremum of the iterates, which is what chaotic iteration computes, `Complete_Partial_Order2` for continuity on products and function spaces, `While_Combinator` for `lfp_while`, an executable iteration proved to reach the fixpoint |
| terms in time, periods, regimes and spans | `Set_Interval` for `{a..b}` over an order | `Interval` as a type with `lower`, `upper` and `set_of` over any preorder, `Disjoint_Sets` for `partition_on` and `disjoint_family_on`, a partition into period bins, `Stream` and `Linear_Temporal_Logic_on_Streams` for `alw`, `ev` and `HLD` if a law is stated over an infinite event stream |
| eligibility | `Option`, datatypes | `Monad_Syntax` for readable three-valued evaluation, `Finite_Map` for an environment |
| behaviour and instrument | records, lists of events, `fold` | `Stream` for unbounded event sequences, `Mapping` for state keyed by a term |
| quantification and rounding | `Rat`, `floor`, `Archimedean_Field` | nothing. `Centered_Division` and `Signed_Division` state other integer rounding rules and are a reading, since the kernel states its own `floor_part` and the rules are proved against it |
| evaluators, vectors and oracles | the code generator | `Code_Target_Numeral`, `Code_Abstract_Char`, `RBT_Mapping`, which the isabelle-layers spike already loads from source |

## 7. The prelude, firmed

The theories the areas above name, each read for the construct we would use. Lines are the theory's own.

| Theory | Lines | What we use | For |
|---|---|---|---|
| `Multiset` | 5,054 | `mset`, `mset_eq_setD`, `ex_mset`, sums over a multiset | LG-8's LO1, any law over a bag of proposals |
| `Sublist` | 1,531 | `subseq`, `prefix`, `suffix`, `list_emb` | LG-8's integer `spread` |
| `FSet` | 2,017 | the type of finite sets with `fmember`, `fsum` | key sets as data, if LG-8 or E4b want it |
| `Finite_Map` | 1,427 | the type of finite maps, `fmlookup`, `fmupd` | amount vectors and environments as data |
| `Mapping` | 962 | abstract maps for code generation | state keyed by a term in an exported evaluator |
| `Option_ord` | 454 | `option` as a preorder with `None` at the bottom and `Some` lifted by the base order, `less_eq_option_None` | the information order on a fact, unknown below known. A flat order needs the fact type ordered by equality, a one-line instance, so this import is a convenience E4b's brief confirms or drops |
| `Product_Order` | 313 | the pointwise order on pairs, with `Product_Plus` | the order on an ensemble of facts |
| `Order_Continuity` | 447 | `sup_continuous`, `sup_continuous_lfp`, `inf_continuous_gfp` | E4b, the least fixpoint as the supremum of the iterates |
| `Complete_Partial_Order2` | 1,774 | `cont`, `mcont`, ccpo instances for products and functions, fixpoint induction | E4b and E4c, continuity of the composed evaluation |
| `While_Combinator` | 562 | `while_option`, `while_rule`, `lfp_while`, `rtrancl_while` | E4c, chaotic iteration as a loop proved to reach `lfp` |
| `Interval` | 836 | the `interval` type, `lower`, `upper`, `set_of`, `width` | spans and periods over an ordered time type |
| `Disjoint_Sets` | 671 | `disjoint_family_on`, `partition_on`, `partition_on_space` | period bins as a partition |
| `Extended_Nat` | 669 | `enat` with `∞` | an unbounded count or ceiling, only if a law needs one |
| `Stream` | 636 | the codatatype of streams, `snth`, `sdrop` | event sequences without end |
| `Linear_Temporal_Logic_on_Streams` | 872 | `alw`, `ev`, `HLD`, `nxt`, `ev_at` | laws over an event stream, if behaviour or instrument state one |
| `Monad_Syntax` | 75 | `do` notation | readable three-valued evaluation in eligibility |
| `Code_Target_Numeral` | 11 | numerals as target integers | every export |
| `Code_Abstract_Char` | 190 | characters as an abstract type | every export with strings |
| `RBT_Mapping` | 247 | `Mapping` implemented by red-black trees | every export with maps |

Nineteen theories. With what they import inside the library, the closure is 38 theories and 28,133 lines, two fifths of the library's 69,551, so a prelude built from source is not a small fraction of the six-minute library build on machine R, more likely two or three minutes under the same cap, which FME-0 measures. It is built once per machine into a heap, and after that every layer session starts from it.

Considered and not imported. `Extended_Nonnegative_Real`, 2,009 lines over `Extended_Real`, built for measure theory, where a ceiling is a rational and an absent one is an option. `Set_Algebras`, which arrives with `Interval` and is not used directly. `Periodic_Fun`, about real-valued periodic functions, not calendar recurrences. `Centered_Division` and `Signed_Division`, a reading for rounding rules the kernel states itself. `Countable`, which arrives with `FSet`. `HOLCF`, which is a parent and not an import if E4b states the composition over a cpo, a question for its brief. The analysis, algebra and probability stacks, which no area reaches for.

## 8. The decision

LG-Q14 is decided (d) on 2026-11-08. One public session, `LatticeBase`, in `tools/proofs/base/`, `session LatticeBase = HOL +` with `sessions "HOL-Library"` and one theory importing the nineteen above, built once per machine into a heap. Every layer session parents on it, the ledger's first, so a library theory is checked once per builder, no machine builds the `HOL-Library` heap, and a private estate's sessions have a public heap to parent on. Adding a library theory is one import in the prelude, reviewed once. The slice is track E's FME-0, and ADR-A-FM2 needs an addendum, since its decision 1 names one session per layer and the prelude is not a layer's.
