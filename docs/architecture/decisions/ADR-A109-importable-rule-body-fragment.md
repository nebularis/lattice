<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A109: The importable rule-body fragment

**Status:** Proposed
**Date:** 2026-10-26
**Related:** [ADR-A104](ADR-A104-instrument-terms-and-legal-relations.md) (decision 15 states this decision's revision), [ADR-A103](ADR-A103-eligibility-set-readings.md) (Eligibility negation), [ADR-A105](ADR-A105-closure-declarations.md) (closure declarations), [ADR-A106](ADR-A106-behaviour-configuration-runtime-occasions-and-records.md) (Behaviour), [ADR-A-C2](ADR-A-C2-clean-room-authoring-procedure.md) (authoring order)
**Unit:** [`computable-contract-substrate`](../../developer/plans/computable-contract-substrate.md)

## Context

A rule written in another rule language has a body, the conditions under which it applies. LATTICE can represent some bodies and not others. Without a stated boundary, an importer either rejects a rule for a reason nobody wrote down or accepts one and silently changes its meaning.

The question is wider than any one rule language. A contract term, a regulation and a licence each have conditions, and each needs the same answer to the same question. The answer has also been revised before it was written. ADR-A104 decision 15 revises it so that a condition may read the recorded state of another relation's occasion, which it cites as a revision of this decision. That revision has nothing to revise until this decision exists.

This decision is paper only. It delivers a statement, not code, and is worth having whether or not the rest of the rule-substrate work proceeds.

## Decision

We record only what the plan and ADR-A104 already settle. The precise statement of the fragment is open and is listed below.

1. **Subject.** This decision declares which rule bodies LATTICE represents when a rule is imported, and names the refusal for everything else.
2. **Starting scope.** The plan describes the fragment as tree-shaped and single-subject, without joins, without deontic formulas in bodies, and with connectives as nested profiles. We take this as the starting scope. The questions below test it.
3. **Revision.** A condition may read the recorded state of another relation's occasion, which is a fact, when the graph of breach, exercise and state-read edges is acyclic (ADR-A104 decision 15 and its law I6). Deontic formulas in a condition stay refused. The revision is part of this decision and is not a later amendment.
4. **Owner.** The decision is filed with the computable contract substrate unit, which holds the slice that drafts it and the evaluation that depends on it.
5. **Order of work.** It is the first decision in the rule-substrate sequence, and the rest of that sequence assumes it. The slice that builds the stratified reading it governs waits on a check for cycles among nested conditions.
6. **Dependencies.** It depends on Eligibility's conditions and nested profiles (ADR-A103) and on ADR-A104. It is depended on by the Instrument evaluation that applies it, by the design-time contradiction check, and by any importer of another rule language.

## Open questions

- **RB-1.** What exactly is in the fragment, and is each of the plan's five restrictions a rule of the fragment or a consequence of the representation?
- **RB-2.** How is each refusal named, where is it enforced (in shapes, in the compiler or in both), and how is it reported to an importer?
- **RB-3.** Which conditions in the tested contracts fall outside the fragment, and do any belong inside it?
- **RB-4.** How is the acyclicity of state reads stated for conditions that nest, and does it overlap with the acyclicity check on condition composition?
- **RB-5.** How does the fragment treat absence, given that ADR-A105 licenses it only where a closure is declared?
- **RB-6.** Does the fragment limit the language a contract term may use or only what an importer accepts?
- **RB-7.** How is the fragment versioned when it widens, and does a widening need an amendment to this decision?
- **RB-8.** The plan reads this decision as new, while ADR-A104 reads it as already existing and revised. Which wording holds when it is accepted?

## Consequences

- ADR-A104 and the plans cite a decision that exists, and the identifier check no longer needs an exception for it.
- The slices that wait on a statement of the fragment can name the questions that remain.
- Nothing is modelled. No class, shape, refusal or diagnostic is fixed here.
- Undecided are the exact boundary, the refusals and their home, and the treatment of absence.

## Provenance

Drafted on 2026-10-26 at the maintainer's request, from the citations to this number collected across the repository. It is Proposed and the maintainer has not accepted it.

It draws on ADR-A104 (decision 15, the Consequences and the addendum of 2026-10-10), the normative rule substrate plan (slice N2 in §6, the ADR table in §5, §7 and §8), its status record (the N2 row and NQ-2), the computable contract substrate plan (the ADR table and the C13 and C13a slices) and the computable contract substrate sketch (§6.2 and the layer table).
