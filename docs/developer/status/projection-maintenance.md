<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Derived data maintained in the write, and replies that do not wait - Status

**Unit ID:** `projection-maintenance`
**Status:** 🟡 PM0 to PM2 built 2026-11-01, PM3 next
**Last updated:** 2026-11-01
**Plan:** [projection-maintenance.md](../plans/projection-maintenance.md)
**Sketch:** [projections-maintained-in-the-write.md](../sketches/projections-maintained-in-the-write.md)

## Current position

Sketched and planned on 2026-10-31 at the maintainer's request, answering SQ-Q2 with BL-09 now and replies that do not wait as a pattern. PM-Q1 to PM-Q9 were answered the same day. BL-09 left the backlog for this plan. PM1 and PM2 need DR1, and PM3 waits for DR4 and PM2 (PM-Q4).

**Next action:** PM3, the event exchange and the WebSocket notifier. For the maintainer, ADR-A149's addenda of 2026-11-01, ADR-A16's, and the Validation Packs of [PM1](../validation/PM1.md) and [PM0 and PM2](../validation/PM2.md).

## Log

- 2026-10-31: sketched, every question answered, planned.
- 2026-11-01: PM-Q10 to PM-Q12 answered with the leanings, one event stream of CloudEvents with a notifier a transport, channels named by lifetime, and PM3 building the WebSocket notifier alone. BL-13 holds webhooks and AMQP grants. The maintainer asked for every planned slice on `claude/config-authoring-studio`, built autonomously.
- 2026-11-01: PM0 is folded into PM2, since most of what it renames, the refresher and its worker, PM2 removes. Renaming first would rewrite those files twice.
- 2026-11-01: PM0 built after all, ahead of PM2's removal of the refresher, so the studio's contract, code, graph names and documents say promotions and a rebuild job. The unit's own names, here and in the sketch and plan, stay.
- 2026-11-01: PM1 built. `surface.maintenance` and the `surface maintenance` command give each promotion a clear and a fill, typed operations of the persistence IR, that keep its rows from a write's delta beside the source or in a graph of their own. An index contract and a shared data graph wait as TD-138. 40 random writes on each of three paths, two placements and two engines leave the rows a rebuild gives.
- 2026-11-01: PM2 built with DR4. Each write keeps its sources' promoted partitions in its own request, the refresher is gone, a publish is one commit and its registry entry is read at once. A start rebuilds only when the promotions grew, and warns without rebuilding when one changed, which a new test covers and a probe broke. PM-Q7's effect check is not built, a cautious deviation. A Sonnet subagent did PM0's rename.
