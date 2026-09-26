<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A103: Eligibility set readings

**Status:** Proposed
**Date:** 2026-09-26 (proposed)
**Related:** ADR-A87 (concept exclusion), ADR-A89 (profile aggregation), ADR-A90 (design-time OWL classes), ADR-A91 (evidence binding), ADR-A100, ADR-A-C2
**Unit:** [`applied-insurance-reference`](../../developer/plans/applied-insurance-reference.md) (Phase 3, epic decision D12)

## Context

**Premise.** An evidence binding reads a subject's candidate along a path (ADR-A91). Many paths
reach several values: a person holds several qualifications, a record carries several codes, and
a path through a many-valued step multiplies what follows it. Today a binding that reaches more
than one value is Undetermined (`exe:SeveralCandidates`, "no reading of several is defined"). A
rule that means "some value qualifies" or "every value qualifies" cannot be stated.

**Examples.**

1. *Admissions.* An applicant qualifies for an engineering course when some qualification they
   hold is in mathematics or physics. An applicant with a history and a physics qualification is
   admitted.
2. *Clinical trials.* A patient is eligible when every recorded diagnosis is on the trial's
   permitted list. A patient with one permitted and one excluded diagnosis is not eligible.

## Decision

1. **A reading on the binding.** `elg:valueReading` on an `elg:EvidenceBinding` takes one of three
   individuals of `elg:ValueReading`:

   | Reading | Outcome over the values the path reaches |
   |---|---|
   | `elg:SingleValue` (default when absent) | one value: its outcome. None: Undetermined (`exe:MissingCandidate`). Several: Undetermined (`exe:SeveralCandidates`). Unchanged from today |
   | `elg:SomeValue` | Permitted when any value is Permitted. Denied when every value is Denied. Otherwise, or when there is no value, Undetermined |
   | `elg:EveryValue` | Denied when any value is Denied. Permitted when every value is Permitted. Otherwise, or when there is no value, Undetermined |

   Each value is decided by the condition as a single candidate would be, including ADR-A87's
   exclusions and ADR-A100's law. The readings are strong Kleene quantifiers over those outcomes,
   as profile aggregation is over conditions (ADR-A89).
2. **Exclusion over a set.** An exclusion that must deny when any value is excluded is a condition
   with the exclusion, read `elg:EveryValue`.
3. **The compilers.** The IR carries the reading. SPARQL and SHACL aggregate each subject's value
   outcomes by counting, as profile aggregation does. SWRL, being DL-safe and monotonic, derives
   only the outcomes a sound subset allows: Permitted under `SomeValue`, Denied under
   `EveryValue`. The OWL backend compiles `SomeValue` as `∃path.C` and `EveryValue` as
   `∀path.C ⊓ ∃path.⊤`, for design-time checks only, relaxing ADR-A90's single-valued claim for
   bindings that declare a reading.
4. **Correlation is out of scope.** Each condition in a profile reads its own path. A rule that
   needs two values to come from the same intermediate node binds its subject to that node.

## Consequences

- Eligibility takes a MINOR bump: a class, three individuals and a property are added, and a
  binding without a reading behaves as today. The import-pinning cascade runs.
- Examples and README text follow ADR-A-C2: the two examples above are authored as fixtures before
  the law's prose.
- Every backend changes. The IR and SPARQL and SHACL are one slice, SWRL and OWL another.
