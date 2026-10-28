<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A145: Set comparisons and aggregate bindings

**Status:** Proposed
**Date:** 2026-10-27
**Related:** [ADR-A103](ADR-A103-eligibility-set-readings.md) (set readings), [ADR-A105](ADR-A105-closure-declarations.md) (closures), [ADR-A91](ADR-A91-eligibility-candidate-evidence-binding.md) (evidence bindings), [ADR-A90](ADR-A90-eligibility-design-time-owl-class-backend.md) (what the OWL backend compiles), [ADR-A100](ADR-A100-hierarchical-match-over-flat-schemes.md) (hierarchical match and the relation a condition walks), [ADR-A89](ADR-A89-eligibility-ir-concept-conditions-and-profile-aggregation.md) (the IR), [ADR-A126](ADR-A126-literate-specification-layout-and-grammar.md) (the README layout)
**Unit:** [`computable-contract-substrate`](../../developer/plans/computable-contract-substrate.md)

## Context

An evidence binding reads the values one path reaches from a subject. A condition decides each value as a single candidate against concepts it names, and a set reading combines the outcomes (L15), the binding's closure licensing what only a complete set proves (L17). Two things a contract states cannot be said with that.

- **A comparison of two sets read from one subject.** "Every holder has consented", "no medication taken is prohibited" and "each territory distributed in is within the territory licensed" relate the values one path reaches to the values another path reaches. A per-value decision can name concepts statically and cannot name a second set read from data.
- **A measure over a set.** "Holders of at least two thirds of the principal consent" reads a quantity for each member of a set, and a share of one set relative to another. Nothing reads a sum or a count.

Two facts shape both. A set read from records is complete only under a closure, so each set needs its own, since a register of holders is usually complete when the consents are still arriving. And Eligibility counts and sums nothing in its own documents. Layers state and code executes, as it does for readings.

## Decision

1. **A set comparison is a condition.** `elg:SetComparison` is an `elg:Condition` that names a tested binding (`elg:testedBinding`), a reference binding (`elg:referenceBinding`) and one `elg:comparison` of a closed class, `elg:Subset`, `elg:Intersects` or `elg:Disjoint`. Both bindings name the comparison with `elg:bindsCondition` and the same subject class. The comparison fixes the reading, so neither binding declares one. Its match strategy is `elg:ExactMatch` or `elg:HierarchicalMatch`, with the relation the condition names, and it names no required or excluded concept, since the reference values take their place.
2. **One law gives each comparison its meaning.** Law L18 decides each tested value as a single candidate would be: Permitted when it matches a reference value, Denied when it matches none and the reference binding names a closure in force, otherwise Undetermined. Subset reads the outcomes as every value, Intersects as some value, and Disjoint as some value negated. The tested binding's closure licenses the reading (L15, L17) and the reference binding's closure licenses a value's Denied. The readings and negation are the existing laws, so their proofs are reused through one lemma per comparison. Membership is used only inside a comparison.
3. **The names say what each set does.** The tested set is the one whose values are looked for, the reference set the one they are looked for in. "Left" and "right" are not used, because the design standard refers to a thing by what it is.
4. **IRIs only for now.** A shape refuses a binding of a comparison that declares a value space. Literal-valued sets wait for a need, since the equality of literals depends on their datatype and the engines differ on it.
5. **An empty tested set is read as L15 reads it.** Under a closure every value over no value is Permitted and some value over no value is Denied, so a subset holds of an empty set. A requirement that a set have at least one member, and a quorum by number of members, is a count over the set's binding, `qnt:Count` with no measure path, read by an interval condition from one. Aggregate bindings admit `qnt:Count`. A comparison states no existence.
6. **Aggregate bindings, decided and not yet built.** An aggregate binding reads a measure over a set, optionally relative to a second set, and offers the result to an interval condition. The measure is a path of `elg:EvidenceStep`s from each member to its quantity, which a compiler can follow. The aggregate names two existing evidence bindings, each with its own reading and closure, so each set has its own. A share above a lower bound needs the universe closed, and below an upper bound needs both sets closed. A sum is read only over an extensive measure in one unit and on one base, which a shape checks. The implementation follows in a later change and this decision records the shape it will take.
7. **The deferral is named in prose.** An evidence or aggregate binding is an evaluation-time deferral, forced by the evaluator and Undetermined until forced. An Instrument value that a binding supplies later is a binding-time deferral. Eligibility's README names the two with no class or marker, since no query or check answers differently because of one (STD-276).
8. **The compilers refuse what they cannot state.** The SPARQL and SHACL backends compile a comparison. The OWL backend refuses it, because OWL 2 DL cannot relate the values of two paths per subject (ADR-A90), and the SWRL backend refuses it, because SWRL cannot test absence.

## Alternatives considered

**C9b3-Q2, how a comparison is stated.**

- *A per-value decision "is a member of the values another binding reaches", with the three comparisons only as names for the readings.* One property and one law, with L15 to L17 doing the rest. Set aside because the comparison is where intent is named for a shape to check, and where a rule for an empty universe would be stated if drafting needed one. A reading with no name for what it compares leaves a shape nothing to ask.
- *A condition kind naming two bindings and one of three comparison individuals, whose meaning is membership.* Taken. The cost is a second law, L18, with L15 and L17 still doing the quantifying.

**C9b3a-Q1, what the two sets are called.**

- *Role properties on the bindings, with `elg:bindsCondition` from both.* Keeps "a binding binds one condition" uniform, but adds to every binding a role that only comparisons read, and two triples where one link on the comparison serves.
- *Names from the law, `elg:subset` and `elg:superset`.* Read well for Subset only, and wrongly for Intersects and Disjoint.
- *`elg:testedBinding` and `elg:referenceBinding` on the comparison.* Taken. Both bindings still name the comparison, and a shape requires the comparison's two links to name two of its own bindings.

**C9b3a-Q2, an empty tested set.** The maintainer decided on a count (decision 5).

- *A self-intersection.* A second condition in the profile, Intersects of the tested set with itself, which holds exactly when the set has a member. Declined because it makes drafting state existence as a set operation, which drafting does not.
- *A flag on the comparison, `elg:requiresMember`.* Declined because it adds a term whose reading of the same empty set differs from L15's.

**C9b3a-Q3, values that are literals.**

- *Literals by value equality on the binding's space.* Needs the space's equality and a decision per engine on numeric and date equality, and costs an engine-dependent `=` per pair. Not taken now.
- *IRIs only.* Taken (decision 4).

**C9b3-Q3, an aggregate binding.** The measure may be a word that an Instrument layer resolves, but Eligibility cannot import Instrument, so no Eligibility compiler could read it. A path is taken. The aggregate may carry its own steps and one closure for both sets. One closure cannot say that the universe register is complete while the consents are not, which is the usual case before a window closes, so two bindings are taken.

## Consequences

- Eligibility gains one condition class, one closed class of three individuals, three properties, one law and two shapes, in its README under ADR-A126's layout. No version moves on the branch, and the release is bumped at merge (ADR-A129).
- The reference semantics gains `decide_set_comparison`, and a new Isabelle theory proves the comparisons' outcomes against the existing readings, so a comparison inherits their monotonicity and negation laws.
- Per subject, a comparison runs one existence test into the reference set for each tested value, so the cost is the sum over subjects of tested values times one lookup. The compilers state it where they generate the query.
- A comparison can be Denied only through the reference set's closure. A reference set still being filled, such as consents before the window closes, leaves a missing value Undetermined and never Denied.
- A condition that needs an existence check is written as a count once aggregate bindings are built. Until then the requirement cannot be stated.
- The OWL and SWRL backends refuse a comparison, so a design-time class cannot be produced for one.
- Under hierarchical match a tested value outside the scheme is Undetermined with `exe:OutsideScheme`, as a single candidate is (L9), and a reference value outside the scheme matches nothing. Over a scheme in which no member has a link of the condition's relation, a tested value that is not equal to a reference value is Undetermined with `exe:NoHierarchy` whatever the closure, as ADR-A100 decides for required concepts, which the reference values stand in for.

## Provenance

Drafted on 2026-10-27 in slice C9b3a of the [`computable-contract-substrate`](../../developer/plans/computable-contract-substrate.md) unit, at the maintainer's answers to C9b3-Q2 (a comparison is a condition whose meaning is membership), C9b3-Q3 (the measure is a path and the two sets keep their own closures), C9b3a-Q1 (tested and reference), C9b3a-Q2 (existence is a count), C9b3a-Q3 (IRIs only) and C9b3a-Q4 (this record). It is Proposed and the maintainer has not accepted it.

It draws on the [consent and group powers sketch](../../developer/sketches/consent-and-group-powers.md), §2.3, Eligibility's README, the set-reading and closure decisions, and the compilers' existing concept and interval backends.
