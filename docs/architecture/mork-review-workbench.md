<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# MORK Review Workbench

Phase 5 wraps existing MORK validation and community analysis in immutable review snapshots. A snapshot identifies the tenant, project, mapping graph revision, section, evidence projection, and snapshot hash. It is the review boundary, not a copy of the full MORK graph.

The six decisions are typed. Confirm accepts a mapping, Retarget changes target evidence, Reshape requests structural work without changing projection statistics, Decline records negative evidence, Teach adds a learning reference, and Defer leaves the mapping unresolved. Evidence projection must be role-restricted: Domain Stewards do not receive syntax, lint diagnostics, pack internals, or cross-tenant content.

`PostgresMorkReviewStore` persists snapshots and decisions through `workers/sql/V2__mork_review_ledger.sql`. A decision query checks tenant, project, and snapshot hash before it writes an audit row. Newer snapshot versions make prior hashes stale, so review decisions conflict safely instead of being silently applied to changed evidence.

The Review Bench is fixture-backed in `apps/mork-review-workbench`. It shows section witnesses, coverage, alternatives, snapshot context, and the six decisions. Its E2E definition verifies Reshape’s no-statistics rule and the restricted-content boundary. Existing MORK validation and community analysis are invoked only through the scope-restricted worker adapter, which returns evidence projection instead of syntax or diagnostics for Domain Stewards.