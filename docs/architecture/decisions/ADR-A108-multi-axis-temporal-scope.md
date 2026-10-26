<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A108: Multi-axis temporal scope

**Status:** Proposed
**Date:** 2026-10-26
**Related:** [ADR-A114](ADR-A114-external-and-natural-keys.md) (the Foundation change that shared this one's planned window), [ADR-A113](ADR-A113-breaking-changes-at-major-version-zero.md) (breaking changes at major version zero), [ADR-A01](ADR-A01-layer-dependency-order.md) (layer order), [ADR-A85](ADR-A85-vocabulary-scoped-temporal-binding-resolution.md) (scoped and temporal binding), [ADR-A104](ADR-A104-instrument-terms-and-legal-relations.md) (Instrument)
**Unit:** [`normative-rule-substrate`](../../developer/plans/normative-rule-substrate.md)

## Context

A norm is not in effect on one date. Whether it is in force, whether it has effect and whether it applies to a given case are separate questions with separate times. The same is true of data about contracts, where the time a fact was recorded, the time it was true, the date agreed and the date it operates can all differ.

Foundation gives a thing one temporal scope, an interval, and the property that states it admits one value. A model that needs a second axis has to invent it, and so each applied module and each layer above Foundation will invent its own. Two kinds of source need more than one axis. A rule language that distinguishes in-force, efficacy and applicability names three. Open CBAA independently names four.

Because Foundation is the lowest layer, any change to how it states time reaches every module that imports it. The cost of the change is therefore much larger than the cost of the decision, and the order in which it is made matters more than the detail. This decision exists to fix the problem, the owner and the order before any modelling, so that the work can be scheduled and the questions argued once.

## Decision

We record only what the plan and accepted decisions already settle. Every modelling question is open and is listed below.

1. **Subject.** This decision covers how a thing that is temporally scoped may carry more than one temporal scope, each along its own axis.
2. **Owner.** Foundation owns temporal scope (ADR-A01), so the change is made there. A layer above Foundation cannot add an axis for the layers below it.
3. **Cost.** The change reaches Foundation's specification, shapes and vocabulary and every importer of Foundation, which the plan counts as 14 files including five applied modules.
4. **Order.** The change is serialised. It does not start while applied insurance Phase 2 is still authoring files that import Foundation, because it would force the branches doing so to re-pin a file they are rewriting. The plan recommends waiting for Phase 2 to complete. That recommendation is the plan's own decision D4, and the maintainer has not yet taken it.
5. **Window.** It does not share a window with the Foundation change of ADR-A114, which has been made on its own. It takes its own later window.
6. **Dependencies.** This decision depends on the Foundation temporal scope as it stands, on ADR-A113 for what a breaking change costs in version terms, and on the completion of applied insurance Phase 2. No other decision is recorded as waiting for it.

## Open questions

- **MT-1.** Which axes exist, and is the set fixed or chosen by the adopter? The rule-language set and the Open CBAA set differ.
- **MT-2.** Does a thing carry one scope per axis, and what becomes of the current single scope and the data already written against it?
- **MT-3.** How is an axis identified, and does the vocabulary machinery of ADR-A85 resolve it?
- **MT-4.** How does this relate to the bi-temporal model proposed for the runtime (transaction time and valid time as parameters of a query)?
- **MT-5.** How do an entry into force that differs by holder and the life of an offer before agreement fit the axes?
- **MT-6.** What do shapes and evaluation require of a scope with several axes, and does any checked rule change?
- **MT-7.** What is the version consequence. The plan calls it a major change, and under ADR-A113 a breaking change at major version zero is a minor increment. Which holds?
- **MT-8.** Is the change needed at all before a consumer requires a second axis, given its cost, and what would count as that requirement?

## Consequences

- The plan, the status record and ADR-A114 cite a decision that exists, and the identifier check no longer needs an exception for it.
- ADR-A114's note that this change keeps its own later window refers to a Proposed decision.
- Nothing is modelled and nothing changes in Foundation.
- Undecided are the axes, the shape of the change, its version and whether it proceeds. Also undecided is the plan's decision D4 on the timing relative to Phase 2.

## Provenance

Drafted on 2026-10-26 at the maintainer's request, from the citations to this number collected across the repository. It is Proposed and the maintainer has not accepted it.

It draws on ADR-A114 (the paragraph on the cascade of NRS N9), the normative rule substrate plan (§1, §4.5, §5 table, slice N9 in §6, §7, decisions D4 and risk R2 in §9 and §10), its status record (the N9 row and decision D4), the legal rule markup mapping sketch referenced there, and pending design decision PDD-11. ADR-A67 is the proposal MT-4 refers to.
