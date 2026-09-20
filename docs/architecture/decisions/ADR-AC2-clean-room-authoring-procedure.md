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
