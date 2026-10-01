<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A-C2: Clean-Room Authoring Procedure for Substrate Content

**Status:** Accepted
**Date:** 2026-09-17

## Context

Substrate content (`ontology/eligibility/`, `ontology/behaviour/`, `ontology/instrument/`, and their `spec/`, `vocab/`, `shapes/`, `ontology/examples/`) must remain usable without knowledge of any specific industry or deployment. Design discussion that references a specific applied use case is valuable for motivating and stress-testing a mechanism, but if substrate prose, naming, or worked examples are drafted by paraphrasing that discussion, the substrate ends up structurally shaped around one deployment's inventory even when no deployment-specific term appears verbatim.

This project's containment posture is deliberately lightweight: there is no requirement for a physically separate repository or an adversarial two-role review. Applied-layer or deployment-specific content may be authored anywhere in this repository at the user's discretion, and committed or not at the user's discretion. The one standing rule is about the *direction of authorship* for substrate content specifically.

## Decision

Substrate content is authored in this order:

1. **The generic premise, in writing, first** — a domain-neutral statement of the problem the mechanism solves, true on its own terms without reference to any deployment.
2. **Non-domain worked examples** — at least two, drawn from unrelated fields (for example, employment, lending, clinical trials, SaaS subscriptions), authored before the mechanism prose that would generalise from them.
3. **Mechanism prose** — the layer's README, its classes, properties, and laws — written to fit the premise and the examples already committed, not adapted from any closed or applied-layer design note.

Applied-layer or deployment-specific material may be read for context and to sanity-check that a mechanism is sufficient, but it is never the source of substrate wording, class naming, section structure, or worked-example structure. Where a design conversation happens to reference a specific applied deployment, that reference stays in the applied-layer material — under `WINGMAN/` or wherever the user directs it — and does not travel into substrate text, even in generalised or renamed form.

## Consequences

- Gate 2 (Eligibility) and Gate 3 (Behaviour) both author `ontology/examples/` before `README.md`.
- No substrate `README.md`, `spec/*.ttl`, or `vocab/*.ttl` names a specific commercial deployment, brand, or closed-estate identifier, in any form.
- This procedure replaces the heavier "two-role clean-room" and "physical repository split" machinery considered earlier in this programme's planning; those are not required given the relaxed containment posture, and are not implemented.

## Addendum (2026-10-01): insurance examples in the computable contract substrate

**Status:** Accepted 2026-10-01 (Gate A), with ADR-A112 (CCS decision CC-D7).

**Scope.** The examples and templates of the layers the computable contract substrate unit
authors: Wording, Instrument and Behaviour (`ontology/<layer>/examples/`, and
`ontology/instrument/templates/` under ADR-A104).

**The relaxation.** Insurance examples may sit in those layers beside other-domain examples when
both conditions hold, per scenario of the unit's catalogue:

1. every scenario an insurance example shows is also shown by an other-domain example, and
2. the insurance example is not more comprehensive: every class and property it uses for that
   scenario is also used by an other-domain example of the same scenario.

**Unchanged.** The authoring order of the Decision above: the premise, then two non-domain
examples, then mechanism prose. Insurance examples are added after them. No substrate text names a
specific commercial deployment, brand or closed-estate identifier, in any form, so an insurance
example is generic: no insurer's or broker's name, policy or agreement number, or market reference.

**Consequences.** The unit's scenario coverage test (CCS slice C15) checks both conditions for
every scenario and fails on either. Fuller insurance renderings stay in `applied/insurance` and in
Open CBAA.
