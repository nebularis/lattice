<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Phase 0 — Decisions and Non-Retrofittable Foundations (Status)

**Unit type:** Phase
**Unit ID:** `phase-0`
**Status:** ⏳ In progress — P0.1 decision pack drafted, pending human ratification
**Last updated:** 2026-09-23
**Plan:** [phase-0-plan.md](../plans/phase-0-plan.md)
**Sketch:** [phase-0-sketch.md](../sketches/phase-0-sketch.md)

---

## Current state

P0.1 (decision pack) was executed autonomously on 2026-09-23: 17 ADRs drafted (A48, A50, A51, A54, A57, A59, A62, A63, A65 through A69, A71, A74, A75, A81), all filed with **Status: Proposed**, none marked Accepted. The human was unavailable during this session and asked the agent to work autonomously and make good decisions for later review — no ADR here is self-ratified; ratification remains a human act per the Agentic Development Contract. ADR-A62's namespace harmonisation (the one part of P0.1.12 that is a mechanical change, not a decision) was executed directly: `ontology/spc/spec/spc.ttl`, `ontology/spc/README.md`, and `tools/spc/python/src/spc/ontologies/spc.owl.ttl` now use the harmonised `nebularis.org` namespace, and `ontology-architecture.md` §3 was updated to match.

No code slice (P0.2 onward) has started. `docs/architecture/iri-policy.md` (P0.1.3 deliverable) was created alongside ADR-A51.

**2026-09-23, later same day:** ADR-A51 was reviewed ([docs/developer/review/ADR-A51-review.md](../review/ADR-A51-review.md)) and found to conflict with RDF identity semantics (environment-scoped IRIs), overclaim uniqueness safety with a truncated hash, and disagree internally with `rdf-sparql-patterns-guide.md`'s own entity-identity default. ADR-A51 and `iri-policy.md` were rewritten to resolve every finding; `rdf-sparql-patterns-guide.md` was corrected in the same pass (revision IRIs now carry the dataset epoch; HMAC claim width; normalization pipeline; S6/S3 query bugs; SHACL `sh:declare` note). Full disposition: [docs/developer/review/ADR-A51-review-disposition.md](../review/ADR-A51-review-disposition.md). ADR-A51 remains `Proposed` — the correction does not constitute ratification.

## Decisions made autonomously in this session — flag for explicit human confirmation

| Decision | What was assumed | Why |
|---|---|---|
| Accept ADR-A74 (graph-primary) | Yes, accepted as drafted | Epic's own stated default; rejecting it reorders ~40% of the plan. No contrary instruction was given. |
| `graph-spi` vs `semantic-dataset-spi` (blocks P0.5.1) | **Not resolved** — left open, no P0.5 slice attempted this session | This decision has execution consequences (module deletion or coexistence) that should not be taken without confirmation, unlike a documentation-only ADR draft |
| ADR-A44 numbering collision | Filed the epic's "amended A44" content as new **ADR-A81** instead of touching the existing accepted ADR-A44 | Amending A44 would have silently corrupted an unrelated, already-accepted decision (MORK Teaching Pack) |
| Scope of this session | P0.1 decision pack only (13 slices' worth of ADRs); no build/code scaffolding (P0.2+) attempted | P0.2.1 itself requires a build-tooling decision (ADR-A76, Maven vs Gradle) and produces a running module skeleton — higher-risk to leave unreviewed than documentation-only ADR drafts |

## Pre-execution blockers

| Blocker | Detail | Resolution owner |
|---|---|---|
| `graph-spi` vs `semantic-dataset-spi` relationship undecided | See [phase-0-plan.md §2](../plans/phase-0-plan.md#2-pre-execution-decision-points-resolve-before-the-named-slice-starts). Still open — not resolved in this session. | Human — must resolve before P0.5.1 |
| All 17 P0.1 ADRs are `Proposed`, not `Accepted` | Every ADR above needs an explicit human ratification pass (Step 1–5 human validation gate) before the Phase 0 exit gate can close | Human |

Nothing else blocks P0.2 starting, once a human has reviewed the P0.1 ADRs (or explicitly authorised proceeding before formal ratification).

## Slice status

| Slice | ADR(s)/deliverable | Status | Notes |
|---|---|---|---|
| P0.1.1 | ADR-A74 | Drafted, Proposed | `data-architecture.md` §1–3, §5–7 rewrite still outstanding |
| P0.1.2 | ADR-A75 | Drafted, Proposed | |
| P0.1.3 | ADR-A51 + `iri-policy.md` | Drafted, Proposed, reviewed and corrected | `iri-policy.md` created; both revised 2026-09-23 per [ADR-A51-review.md](../review/ADR-A51-review.md) — see [disposition](../review/ADR-A51-review-disposition.md) |
| P0.1.4 | ADR-A54 | Drafted, Proposed | Graph-name validator (P0.3.7) not yet built |
| P0.1.5 | ADR-A65 | Drafted, Proposed | `ontology/governance/shapes/provenance.ttl` (P0.3.6) not yet built |
| P0.1.6 | ADR-A67 | Drafted, Proposed | |
| P0.1.7 | ADR-A68 | Drafted, Proposed | DPO/legal review still recommended, not performed |
| P0.1.8 | ADR-A63 | Drafted, Proposed | |
| P0.1.9 | ADR-A48 | Drafted, Proposed | Replaces `solution-design-specification.md` §7.1 CAP framing — doc rewrite still outstanding |
| P0.1.10 | ADR-A50 + ADR-A81 (renumbered from "A44 amended") | Drafted, Proposed | Numbering collision — see table above |
| P0.1.11 | ADR-A57 | Drafted, Proposed | |
| P0.1.12 | ADR-A59, ADR-A66, ADR-A71, ADR-A62 | Drafted, Proposed | ADR-A62's namespace rename executed; the other three are documentation only |
| P0.1.13 | ADR-A69 | Drafted, Proposed | |
| P0.1.14 | Threat model document | Not started | Requires owner-per-control assignment; needs human risk input |
| P0.1.15 | NFR/SLO catalogue | Not started | Epic's own framing: "are the numbers ones you are willing to be held to" — requires human sign-off on numbers, not agent invention |
| P0.2+ | Build skeleton, ontology, store SPI, coordination, host, messaging, synthetic data | Not started | |

## Milestone tracker

| Milestone | Demonstrable outcome | Status |
|---|---|---|
| M0 | Walking skeleton (browser → HTTP → domain → response, in compose, one correlation ID traceable, Playwright smoke) | Not demonstrated |
| M1 | Store conformance (signed capability + benchmark report, TDB2 + Fuseki, hostile scoping suite green) | Not demonstrated |

## ADR ratification tracker

| ADR | Subject | Status |
|---|---|---|
| A44 | Control Plane HTTP runtime — **renumbered to A81** to avoid collision with the existing accepted A44 (MORK Teaching Pack) | Superseded by renumbering; see A81 |
| A48 | Transaction boundary catalogue (replaces CAP framing) | [Drafted, Proposed](../../architecture/decisions/ADR-A48-transaction-boundary-catalogue.md) |
| A50 | Role-profiled deployment | [Drafted, Proposed](../../architecture/decisions/ADR-A50-role-profiled-deployment.md) |
| A51 | IRI & identity policy | [Drafted, Proposed](../../architecture/decisions/ADR-A51-iri-and-identity-policy.md) |
| A54 | Dataset topology | [Drafted, Proposed](../../architecture/decisions/ADR-A54-dataset-topology.md) |
| A57 | Change feed | [Drafted, Proposed](../../architecture/decisions/ADR-A57-change-feed.md) |
| A59 | `PartitionedWorkQueue` abstraction | [Drafted, Proposed](../../architecture/decisions/ADR-A59-partitioned-work-queue-abstraction.md) |
| A62 | SPC namespace harmonisation | [Drafted, Proposed](../../architecture/decisions/ADR-A62-spc-namespace-harmonisation.md) — namespace rename executed |
| A63 | `projectId` vs `environmentId` | [Drafted, Proposed](../../architecture/decisions/ADR-A63-project-vs-environment-scoping.md) |
| A65 | Provenance | [Drafted, Proposed](../../architecture/decisions/ADR-A65-provenance-model.md) |
| A66 | Principal model | [Drafted, Proposed](../../architecture/decisions/ADR-A66-principal-model.md) |
| A67 | Bi-temporal | [Drafted, Proposed](../../architecture/decisions/ADR-A67-bi-temporal-model.md) |
| A68 | PII & erasure | [Drafted, Proposed](../../architecture/decisions/ADR-A68-pii-and-erasure.md) |
| A69 | Pack trust model / safe SPARQL subset | [Drafted, Proposed](../../architecture/decisions/ADR-A69-pack-trust-and-safe-sparql-subset.md) |
| A71 | Platform licence MPL-2.0 + SPI seam | [Drafted, Proposed](../../architecture/decisions/ADR-A71-platform-licence-and-spi-seam.md) |
| A74 | Graph-primary realm model | [Drafted, Proposed](../../architecture/decisions/ADR-A74-graph-primary-realm-model.md) |
| A75 | Three-tier store SPI | [Drafted, Proposed](../../architecture/decisions/ADR-A75-three-tier-store-spi.md) |
| A76 | Maven vs Gradle | Not drafted — deferred to P0.2.1 (build skeleton slice) |
| A81 | Control Plane HTTP runtime (was "A44 amended") | [Drafted, Proposed](../../architecture/decisions/ADR-A81-control-plane-http-runtime.md) |

## Documentation and README debt tracker

Tracks [phase-0-plan.md §3–5](../plans/phase-0-plan.md#3-documentation-obligations--docsarchitecture) as it is worked off.

| Item | Status |
|---|---|
| `docs/architecture/iri-policy.md` (P0.1.3) | Done |
| `data-architecture.md` §1–3, §5–7 rewrite for A74 (P0.1.1) | Outstanding |
| `solution-design-specification.md` §7 rewrite for A48 (P0.1.9) | Outstanding |
| `ontology-architecture.md` SPC section update for A62 | Done |
| `docs/architecture/nfr.md` + `nfr.yaml` (P0.1.15) | Outstanding — needs human SLO sign-off |
| Threat model document (P0.1.14) | Outstanding |
| All other rows in the plan's §3–5 tables | Outstanding |

## Next steps

1. **Human reviews and ratifies (or rejects) the 17 `Proposed` ADRs above.** Per the human validation gate protocol, review each ADR's Context/Decision/Consequences before anything downstream depends on it.
2. Human resolves the `graph-spi`/`semantic-dataset-spi` decision point (still open) before P0.5.1.
3. Human confirms or corrects the ADR-A44/A81 renumbering.
4. Once ratified, begin P0.2 (build skeleton) — including deciding ADR-A76 (Maven vs Gradle) as part of that slice.
5. `data-architecture.md` and `solution-design-specification.md` rewrites (tied to A74 and A48 respectively) should follow ratification, not precede it, in case ratification changes the decision content.

