<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Derived data maintained in the write, and replies that do not wait - Status

**Unit ID:** `projection-maintenance`
**Status:** 🟡 PM0 to PM3 built 2026-11-01, PM3a and PM3b, events over the broker's Web MQTT, built 2026-11-02
**Last updated:** 2026-11-02
**Plan:** [projection-maintenance.md](../plans/projection-maintenance.md)
**Sketch:** [projections-maintained-in-the-write.md](../sketches/projections-maintained-in-the-write.md), and PM3's rework in [browser-events-over-web-mqtt.md](../sketches/browser-events-over-web-mqtt.md)

## Current position

Sketched and planned on 2026-10-31 at the maintainer's request, answering SQ-Q2 with BL-09 now and replies that do not wait as a pattern. PM-Q1 to PM-Q9 were answered the same day. BL-09 left the backlog for this plan. PM1 and PM2 need DR1, and PM3 waits for DR4 and PM2 (PM-Q4).

**Next action:** the maintainer reviews [PM3b](../validation/PM3b.md) and answers PM-Q19, PM-Q21 and PM-Q22, then PM3c, the proxy run. PM4's questions, PM-Q13 to PM-Q17, were put in chat on 2026-11-02 and are not yet written into the plan.

## Log

- 2026-10-31: sketched, every question answered, planned.
- 2026-11-01: PM-Q10 to PM-Q12 answered with the leanings, one event stream of CloudEvents with a notifier a transport, channels named by lifetime, and PM3 building the WebSocket notifier alone. BL-13 holds webhooks and AMQP grants. The maintainer asked for every planned slice on `claude/config-authoring-studio`, built autonomously.
- 2026-11-01: PM0 is folded into PM2, since most of what it renames, the refresher and its worker, PM2 removes. Renaming first would rewrite those files twice.
- 2026-11-01: PM0 built after all, ahead of PM2's removal of the refresher, so the studio's contract, code, graph names and documents say promotions and a rebuild job. The unit's own names, here and in the sketch and plan, stay.
- 2026-11-01: PM1 built. `surface.maintenance` and the `surface maintenance` command give each promotion a clear and a fill, typed operations of the persistence IR, that keep its rows from a write's delta beside the source or in a graph of their own. An index contract and a shared data graph wait as TD-138. 40 random writes on each of three paths, two placements and two engines leave the rows a rebuild gives.
- 2026-11-01: PM2 built with DR4. Each write keeps its sources' promoted partitions in its own request, the refresher is gone, a publish is one commit and its registry entry is read at once. A start rebuilds only when the promotions grew, and warns without rebuilding when one changed, which a new test covers and a probe broke. PM-Q7's effect check is not built, a cautious deviation. A Sonnet subagent did PM0's rename.
- 2026-11-01: PM3 built. The writer publishes a CloudEvent for each applied job update on `lattice.studio.events`, the service's notifier delivers it over the WebSocket `/api/events` to a subscribed session whose principal may read the job, checked at delivery, and the browser waits on a job's events between reads with polling as the fallback. The real-stack suite shows a compile's completion arriving on the socket.
- 2026-11-02: the maintainer questioned PM3's own WebSocket as a protocol we would have to keep, and asked for the broker's Web MQTT with or without a proxy. Sketched in [browser-events-over-web-mqtt.md](../sketches/browser-events-over-web-mqtt.md), with PM-Q18 to PM-Q22 open. The broker's behaviour there is from RabbitMQ 4.4's documentation, not yet probed. The diagrams render with mermaid 11.4.1.
- 2026-11-02: PM-Q18 (a) and PM-Q20 (d) answered by the maintainer, who refuted (a) to (c) as copies of a permission in the broker that fail open. PM3a probed RabbitMQ 4.4's Web MQTT and HTTP auth backend (recorded in [PM3b](../validation/PM3b.md)), and PM3b built the broker's checks of identity, the relay in place of the WebSocket, `events.ts` over mqtt.js 5.16.1, and TLS in the real-stack run. PM-Q19 (c) and PM-Q21 (a) with (b) built as leanings while open.
