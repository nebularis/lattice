<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: PM3, completion events and the WebSocket notifier

**Unit:** [`projection-maintenance`](../status/projection-maintenance.md), slice PM3 of the [plan](../plans/projection-maintenance.md), built on 2026-11-01 in autonomous mode.

**For countersignature (non-weakening rule):** no test was weakened or removed. The browser's job reads keep polling as their fallback.

## Invariant

A job's completion reaches a browser that subscribed to it with no poll, and no event reaches a principal who may not read the job it names, at subscription or at delivery (PM-Q10 (a), PM-Q11 (c), PM-Q12).

## What changed

- **The events.** `StudioEvents` makes a CloudEvent of each applied job update, about 400 bytes in JSON with the job's status and workspace and no content (ADR-A30). The writer hands it on once the request that applied the update committed, and a failure to publish is logged and never fails the write.
- **The exchange.** The writer publishes to the topic exchange `lattice.studio.events` through `platform-outbox`'s `RabbitMqEventPublisher`, which now writes the CloudEvents AMQP binding's binary mode, the attributes as `cloudEvents:` headers.
- **The notifier.** `Notifier` holds the sessions, authenticates a session's first frame with the service's authenticator, checks each subscription and each delivery by `StudioApi.mayRead`, and bounds a session to 200 subjects and a frame to 16 KiB. `EventConsumer` feeds it from a queue of the instance's own. Without a broker, the service's own writer feeds it directly.
- **The socket.** `/api/events` on Helidon's WebSocket module (`helidon-webserver-websocket` 4.5.6, of the Helidon release the service already uses), refusing an upgrade whose `Origin` is another host.
- **The browser.** `events.ts` keeps one socket a tab, and `awaitJob` and the build view wait on a job's events between reads, reading again after five seconds without one, or polling as before when the socket is closed.
- **Documents.** The contract README's "Completion events" section, and the outbox README.

## Tests

| ID | Given / When / Then | Level | Pass |
|---|---|---|---|
| PM3-T1 | a job submitted, then finished / `anAppliedJobUpdateIsOneEventNamingTheJobWithItsStatusAndWorkspaceAndNoContent` / one event, its subject the job, its data the status and workspace, under 512 bytes | L3 | |
| PM3-T2 | a refused job update / `aRefusedJobUpdatePublishesNothing` / no event | L1, negative | |
| PM3-T3 | a first frame that is not auth, an unknown principal, malformed JSON / `aSessionAuthenticatesFirstAndAnyOtherFirstFrameClosesIt` / closed with 1008. A known principal gets ready | L8, negative | |
| PM3-T4 | two sessions on two jobs / `anEventReachesOnlyTheSessionsSubscribedToItsJob` / each hears its own, and nothing after unsubscribing | L1 | |
| PM3-T5 | a reviewer subscribed to a shared workspace's job, then the workspace locked / `noEventReachesAPrincipalWhoMayNotReadItsJobAtSubscriptionOrAtDelivery` / the event withheld at delivery, a later subscription refused as absent, a subject that is no job refused | L8, negative | |
| PM3-T6 | a frame over 16 KiB / `aFrameLongerThanTheLimitIsRefusedUnread` / closed | L8, negative | |
| PM3-T7 | a real WebSocket on a real server / `aBrowserWaitingOnTheSocketHearsItsJobFinishWithNoPoll` / ready, subscribed, then the job's event | L4 | |
| PM3-T8 | an upgrade from another origin / `aSocketOpenedFromAnotherSiteIsRefused` / refused | L8, negative | |
| PM3-T9 | an event's AMQP headers / `theEventsOfTheBrokerAreReadBackFromTheirHeaders` / the same event, and nothing when an attribute is missing | L3 | |
| PM3-T10 | the browser's socket faked / `events.test.ts`, 3 tests / auth first, subscribe after ready, unsubscribe on close, a watcher woken by its event and one kept from before it waited, the fallback after its wait | L1 | |
| PM3-T11 | the real stack / `e2e-stack/stack.spec.ts`, an author compiles / the page receives the job's Succeeded event on its socket | L6 | |

**The one command:** `mise run check:config-studio`, then `mise run test:config-studio-browser` for PM3-T11.

## Results, 2026-11-01

- `EventsTest` 9 of 9, `events.test.ts` 3 of 3, and `test:config-studio-browser` 20 on the fake service and 2 on the real stack.
- Probe: with the check at delivery removed, PM3-T5 failed, and it passed again once restored.
- On the real stack a compile's page received the job's Running and Succeeded events about 120 ms apart, and read the job once for each.

## Deviations from the plan

1. **Only job updates are events.** A commit event for every write has no subscriber yet, and the plan's done criterion is a job's completion. It is one more type on the same exchange when one is needed.
2. **The pending marks are the job states the studio already shows.** A reply that does not wait is today a job, which the build view marks Queued or Running until its event arrives. Marks for a tier 2 materialisation wait for PM4.
3. **The fake service has no socket,** so the journeys on it exercise the fallback, and the real stack exercises the socket.

## Decisions taken alone, for the maintainer's review

1. **A session authenticates with its first frame,** carrying the headers an HTTP request would, since a browser sets no header on a WebSocket and a token in the URL would be logged. Its alternatives are a short-lived ticket minted by an HTTP request, which is one more credential to keep, or a cookie, which the studio does not use.
2. **The upgrade is refused when `Origin` names another host,** so a page of another site cannot open a session on a loopback service whose local authentication trusts the name a frame gives.
3. **A subscription is acknowledged with a `subscribed` frame,** so a client knows when an event can no longer be missed.
4. **No event is durable.** Each instance's queue lives with its connection, and a missed event costs a reader one fallback read, five seconds at most. A durable channel is BL-13's.
5. **A job the principal may not read answers as absent,** so a subscriber learns nothing of it.
