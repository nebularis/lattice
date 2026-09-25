<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A91: Eligibility candidate evidence binding

**Status:** Accepted
**Date:** 2026-09-25 (proposed), 2026-09-25 (accepted)
**Related:** ADR-A01 (layer dependency order), ADR-A17 (unified projection
authoring), ADR-A24, ADR-A89, ADR-A90
**Unit:** [`applied-ontology-readiness`](../../developer/plans/applied-ontology-readiness.md)

## Context

Every Eligibility backend reads a candidate from an `elg:Question`
(`elg:candidateRangeSet`, `elg:candidateValue`). An applied ontology keeps its
facts on its own properties: an employee's job family, a patient's diagnosis
and weight, a loan's credit score. To evaluate a condition today it must copy
each fact into a question first. The copy duplicates state, detaches the
decision from the fact it was based on, and has to be kept in step by code
outside the graph.

The `mork-eligibility-compiler` sketch identified this gap and deferred an
"executable projection contract" layer pending an ADR. Surface already reads
domain data through declared paths (`srf:PathStep`, an indexed step list
chosen because it canonicalises and hashes directly), but Surface does not
import Eligibility and sits outside the ADR-A01 chain.

## Options

| Option | Summary | Cost |
|---|---|---|
| A. Eligibility binding | Eligibility declares an evidence binding: condition, subject class, and an indexed step list to the candidate | Eligibility MINOR. The step-list pattern exists twice until lifted to Foundation |
| B. Foundation path steps first | Lift the step-list pattern to Foundation, then use it from Eligibility and Surface | Foundation MINOR, cascading to every layer. Surface migrates `srf:PathStep` |
| C. Surface binding | A Surface contract kind binds conditions to domain paths and lowers into the Eligibility IR | Surface must reference Eligibility terms, against its current import set |
| D. Materialised questions | A Surface projection writes questions from domain data. No new terms | Works today. Keeps the duplication this ADR exists to remove |

## Decision

Option A, with D remaining available.

1. Eligibility adds `elg:EvidenceBinding`, relating one condition to the
   subject class whose instances it evaluates and to an ordered list of
   `elg:EvidenceStep` (property, direction, index), shaped like
   `srf:PathStep` so a later lift to Foundation needs no data change.
2. The terminal value is a `skos:Concept` for concept conditions and a
   `qnt:Quantity` for interval conditions. A literal terminal value is read on
   a value space the binding names.
3. Questions and decisions produced through a binding name their subject with
   a new `elg:aboutSubject`. `elg:subjectRoleOccupancy` keeps its meaning for
   party subjects.
4. The IR (ADR-A89) reads candidates through a binding when one exists and
   from the question otherwise. Every backend, including the OWL backend of
   ADR-A90, uses the same binding.

## Consequences

- An applied ontology evaluates conditions directly over its own data, with
  decisions linked to the subject and, through provenance, to the facts read.
- Eligibility takes a MINOR bump with the ADR-A86 cascade.
- The step-list pattern is duplicated between Eligibility and Surface. ADR-A92
  records the Foundation lift as a candidate for the same Foundation change
  that introduces the derived-artefact contract.
- Alternation and zero-or-more paths stay out of scope, as for Surface.

## Implementation notes (2026-09-25, `applied-ontology-readiness` AOR-9)

- The compiled artefacts key their rows and shape reports by the subject
  itself and mint no question or decision record. `elg:aboutSubject` (item 3)
  therefore has no producer yet and is not declared.
- Subjects are the instances of the subject class and of its subclasses, as a
  SHACL `sh:targetClass` selects them.
- SWRL records a bound outcome per condition with `exe:permittedUnder` and
  `exe:deniedUnder`, since `exe:impliesDecision` on a subject would not say
  which condition decided it. A bound interval rule reads one terminal form: a
  literal where the binding names `elg:readOnSpace`, else a `qnt:Quantity`.
