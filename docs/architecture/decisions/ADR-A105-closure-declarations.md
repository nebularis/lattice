<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A105: Closure declarations

**Status:** Proposed 2026-10-12
**Date:** 2026-10-12
**Related:** [ADR-A103](ADR-A103-eligibility-set-readings.md) (set readings, and its 2026-10-12
addendum), [ADR-A14](ADR-A14-conformance-levels.md) (conformance level L5's "closure
assumptions"), [ADR-A106](ADR-A106-behaviour-configuration-runtime-occasions-and-records.md)
(`bhv:closureReliedOn`), [ADR-A104](ADR-A104-instrument-terms-and-legal-relations.md) (deemings),
[ADR-A115](ADR-A115-quantification-context-values.md) (context values), the computable contract
substrate plan's HQ-6a, questions HQ6a-Q1 to Q5

## Context

A record proves what it shows. Eligibility's set readings (ADR-A103) went further: a binding read
`elg:SomeValue` was Denied when every value it reached was Denied, which treats the values recorded
as all there are. With no value at all the same reading was Undetermined. So whether absence decided
depended on whether some unrelated record happened to exist: a document recorded after a deadline
let "no document within the deadline" decide, while no document at all did not. No contract term or
source licensed either. The law decides on silence only where a deeming, a time bar or a party's
authority says so, and ADR-A14's level L5 requires "closure assumptions" for a decision without
saying what one is. Instrument's `ins:when` and Behaviour's `bhv:closureReliedOn` already point here.

## Decision

1. **A set reading decides on completeness only under a closure** (HQ6a-Q1 (b)). Without one, a
   binding read `elg:SomeValue` decides only Permitted, from a value that is Permitted, and one read
   `elg:EveryValue` only Denied, from a value that is Denied. Every other outcome is Undetermined.
   Under a closure, some value is Denied when every value is Denied and every value Permitted when
   every value is Permitted, the empty case included. A closure never changes `elg:SingleValue`.
   L15 is restated to say so, and ADR-A103 gains an addendum.
2. **Eligibility declares closures** (HQ6a-Q2 (a)): `elg:Closure`, read by Eligibility's conditions
   and compilers. Behaviour and Instrument import Eligibility, so a breach record and a deeming can
   name one.
3. **The binding names its closure** (HQ6a-Q3 (a)), with `elg:closedUnder`, where it relies on it.
4. **A closure states only its source, and covers exactly the bindings that name it** (HQ6a-Q5
   (b)). `elg:licensedBy` names one source and has no range: a deeming or another term, a party
   whose register is authoritative, or an operational profile by which a deployment declares its
   records complete. Several bindings share a closure by each naming it. Nothing infers which
   bindings a closure is for.
5. **The cut is the deciding record's recording time.** A closure licenses the records as they
   stood when the decision was recorded (`fnd:Evidenced`). A decision names the closures it relied
   on with `elg:closureReliedOn`. A closure is in force from its source's effective time (L17, new).
6. **Untimed** (HQ6a-Q4 (2)). A closure over a period, such as "within 60 days of the request",
   needs a window anchored per subject, resolved at evaluation (ADR-A115), and is declared later
   with the other matters of time: supersession by a late fact, conclusive and single-purpose
   deemings, business days, and a closure's binding to the store.
7. **Refusal** (NRS D7). A compiler refuses a binding that names something which is not a closure,
   or a closure with no source, with `exe:NoClosureLicence`. A binding that names no closure never
   decides on absence, so an unlicensed decision on absence cannot be compiled at all.
8. **No Persistence content.** How a closure binds to a store, the per-root sequence and receipt
   stream (formal-methods Track H's AO-Q6) and `dal:BlockingContiguityCheck`, is decided with the
   closure over a period.

## Consequences

- Eligibility 0.12.0, `eligibility-vocab` 0.13.0 and Eligibility's shapes 0.3.0, each a MINOR marked
  breaking (ADR-A113), since L15 changes meaning. Their importers re-pin.
- `some_value` and `every_value` take whether the binding is closed, in the Isabelle theory and the
  reference semantics. Every proof claim of Eligibility's session is re-digested, since claim digests
  cover the definitions.
- Examples that relied on ADR-A103's assumption name a closure: the admissions registry under an
  operational profile, a trial protocol's full-history clause, a claims file, a facility agent's
  register and a licence's reporting clause.
- The compilers apply closures and the refusal in a following slice. Until then their SPARQL and
  SHACL backends keep ADR-A103's original reading, which the reference semantics no longer shares
  for set readings.
- Deciding on absence is always traceable to a named source. A wrong reference to a closure is
  caught by review and examples, not by a shape.
