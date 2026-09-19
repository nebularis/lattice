<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Phase 6 Validation Handoff

Run `python -m pytest workers/tests/test_mork_governance.py workers/tests/test_mork_governance_ledger.py`, then `yarn check`, `yarn build`, and `yarn test`. Validate replayed queue ordering with identical snapshot fixtures, replayed governance ledger ordering, calibration gates for multiple pack/profile/model combinations, rejected bulk actions without matching calibration, named-axiom reopening of affected approvals, template-by-exception engineering review, and retrospective challenges that preserve the challenged decision identity.

The network-enabled environment must connect the queue to persisted review snapshots, publish calibration results, and verify that Pack Studio and Domain Steward roles cannot retrieve source syntax, MCN, lint diagnostics, or pack internals. This restricted authoring environment did not run Python, Yarn, Playwright, PostgreSQL, RabbitMQ, or graph-store integration commands.