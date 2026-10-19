<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Phase 5 Validation Handoff

**Status:** Accepted
**Governing ADRs:** [ADR-A22](../../architecture/decisions/ADR-A22-mork-governance-and-versioning-foundation-alignment.md), [ADR-A25](../../architecture/decisions/ADR-A25-llm-participation-and-deterministic-production-gate.md), [ADR-A42](../../architecture/decisions/ADR-A42-mork-review-snapshot-and-decision-learning-boundary.md)

Run `python -m pytest workers/tests/test_mork_review.py workers/tests/test_mork_review_lifecycle.py workers/tests/test_mork_analysis_worker.py`, then `yarn check`, `yarn build`, and `yarn test`. Apply `workers/sql/V2__mork_review_ledger.sql` to PostgreSQL. Validate that each of Confirm, Retarget, Reshape, Decline, Teach, and Defer has its defined effect, stale snapshots conflict, and Domain Stewards cannot receive MCN, lint diagnostics, pack internals, or cross-tenant evidence.

The network-enabled environment must connect scope-restricted worker wrappers to existing MORK validation and community-analysis modules. It must seed immutable mapping snapshots and demonstrate evidence projection through the Review Bench without returning restricted content. This authoring environment did not run Python, Yarn, Playwright, RabbitMQ, or graph-store integration commands.