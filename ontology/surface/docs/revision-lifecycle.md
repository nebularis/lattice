<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

⚠️ **DEPRECATED** — This document has been migrated to the LATTICE documentation governance structure.

**New location:** [docs/operator/surface-revision-lifecycle.md](../../../docs/operator/surface-revision-lifecycle.md)

**Reason:** Moved to operational documentation with state machine, versioning scheme, and lifecycle events.

**Migration date:** 2026-09-22

For current revision lifecycle procedures and state machine, refer to the link above. This file is retained for historical reference.

---

# Surface Revision Lifecycle

The Surface workflow control plane wraps the existing compiler. It does not change the semantics implemented by `tools/surface`.

Each revision references immutable contract and profile graph revisions. It moves through `DRAFT`, `REVIEW_REQUESTED`, `APPROVED`, `GENERATED`, `RELEASED`, or `SUPERSEDED`. A revision cannot generate before approval, and a generated or released revision must retain its generated graph reference and approval evidence.

A generated revision becomes a release candidate only when it has generated-output digests and passed semantic gate evidence. The candidate carries contract, profile, and generated graph references into the release-stack-neutral `ReleaseIntent`. The release stack cannot replace the semantic evidence with signing or deployment evidence.

Surface generation, parity, and invalidation are invoked through the `surface-job-request` contract. The job references contract, profile, and source graphs by tenant, project, graph IRI, and revision hash. It does not carry Turtle, RDF, credentials, browser tokens, or shell commands.

The existing fixtures remain the initial acceptance corpus:

- `ontology/surface/examples/saas-subscription-currency.ttl` for Promotion.
- `ontology/surface/examples/clinical-trial-crosswalk.ttl` for crosswalk fidelity.
- `ontology/surface/examples/employment-job-family.ttl` for Index and closure.
