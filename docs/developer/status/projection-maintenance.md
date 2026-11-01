<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Derived data maintained in the write, and replies that do not wait - Status

**Unit ID:** `projection-maintenance`
**Status:** 🟡 PM1 built 2026-11-01, PM2 with PM0 next
**Last updated:** 2026-11-01
**Plan:** [projection-maintenance.md](../plans/projection-maintenance.md)
**Sketch:** [projections-maintained-in-the-write.md](../sketches/projections-maintained-in-the-write.md)

## Current position

Sketched and planned on 2026-10-31 at the maintainer's request, answering SQ-Q2 with BL-09 now and replies that do not wait as a pattern. PM-Q1 to PM-Q9 were answered the same day. BL-09 left the backlog for this plan. PM1 and PM2 need DR1, and PM3 waits for DR4 and PM2 (PM-Q4).

**Next action:** PM2 with PM0 folded in, and DR4 with it. For the maintainer, ADR-A16's addendum of 2026-11-01 and [PM1's Validation Pack](../validation/PM1.md).

## Log

- 2026-10-31: sketched, every question answered, planned.
- 2026-11-01: PM-Q10 to PM-Q12 answered with the leanings, one event stream of CloudEvents with a notifier a transport, channels named by lifetime, and PM3 building the WebSocket notifier alone. BL-13 holds webhooks and AMQP grants. The maintainer asked for every planned slice on `claude/config-authoring-studio`, built autonomously.
- 2026-11-01: PM0 is folded into PM2, since most of what it renames, the refresher and its worker, PM2 removes. Renaming first would rewrite those files twice.
- 2026-11-01: PM1 built. `surface.maintenance` and the `surface maintenance` command give each promotion a clear and a fill, typed operations of the persistence IR, that keep its rows from a write's delta beside the source or in a graph of their own. An index contract and a shared data graph wait as TD-138. 40 random writes on each of three paths, two placements and two engines leave the rows a rebuild gives.
