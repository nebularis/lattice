<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: PM3a and PM3b, events over the broker's Web MQTT

**Unit:** [`projection-maintenance`](../status/projection-maintenance.md), slices PM3a and PM3b of the [plan](../plans/projection-maintenance.md), from the [sketch](../sketches/browser-events-over-web-mqtt.md), built on 2026-11-02 in autonomous mode.

**For countersignature (non-weakening rule):** PM3-T3, PM3-T7 and PM3-T8 tested the service's WebSocket, its first-frame authentication and its Origin check, which this slice removes with the socket. Each is replaced by a test of what now does that job, PM3b-T3, PM3b-T6, PM3b-T7 and PM3b-T10. PM3-T5, the check at delivery, holds unchanged.

## Invariant

A job's completion reaches a browser tab that watches it with no poll, and no event reaches a principal who may not read the job it names, at subscription or at delivery. The broker lets a tab in only as its principal and onto its own tab's topics only, and holds no permission the graph holds (PM-Q20 (d)).

## What changed

- **The broker's checks.** `BrokerAuth` answers RabbitMQ's HTTP auth backend at `/api/broker/{user,vhost,resource,topic}`. A tab connects as its principal with the app's own credential, from a client id naming its principal and tab, and may use only its session queue, `amq.topic`, its tab's watch topic for writing and its tab's events topic for reading.
- **The relay.** `Relay`, from `EventConsumer`, reads the studio's events as before and every tab's watch topic, and publishes what the notifier allows to the tab's events topic. `Notifier` keeps its watchers and its check at delivery, keyed by principal and tab, loses its first-frame authentication, and authenticates each subscribe frame by the headers it carries, which must name the topic's principal.
- **The service.** The WebSocket listener, its Origin check and `helidon-webserver-websocket` are gone. `LATTICE_STUDIO_EVENTS_URL` turns events on, `/api/session` names it, and the page's CSP adds it to `connect-src`.
- **The browser.** `events.ts` keeps its interface over the `mqtt` client library 5.16.1, loaded as a chunk of its own, with a will message that tells the relay the tab is gone.
- **The stack and the harness.** The stack's broker enables `rabbitmq_web_mqtt` and `rabbitmq_auth_backend_http`, with the broker's own users first, and serves Web MQTT on loopback. The harness also serves it over TLS, with a certificate Erlang's `public_key` makes for the run, so no platform needs openssl, and the real-stack run connects over `wss`.
- **Documents.** The contract README's "Completion events", the sketch, the plan's slices and BL-13.

## Tests

| ID | Given / When / Then | Level | Pass |
|---|---|---|---|
| PM3b-T1 | PM3-T1 and PM3-T2 unchanged, the event and a refused update | L3, L1 | |
| PM3b-T2 | PM3-T9 on `Relay.read` | L3 | |
| PM3b-T3 | frames with no headers, another principal's headers, an unknown principal, malformed JSON / `aSubscribeFrameMustCarryItsOwnPrincipalsHeaders` / refused or dropped, no tab kept. Its own headers are watched, unacknowledged | L8, negative | |
| PM3b-T4 | two tabs on two jobs / `anEventReachesOnlyTheTabsWatchingItsJob` / each hears its own, nothing after unsubscribing, and a tab gone is forgotten | L1 | |
| PM3b-T5 | PM3-T5 / `noEventReachesAPrincipalWhoMayNotReadItsJobAtSubscriptionOrAtDelivery` / withheld at delivery once locked, a later watch refused as absent | L8, negative | |
| PM3b-T6 | a frame over 16 KiB, 21 tabs of one principal / `aFrameLongerThanTheLimitIsDroppedUnread`, `aPrincipalWatchesFromABoundedNumberOfTabs` / dropped, refused | L8, negative | |
| PM3b-T7 | the broker's user and vhost checks / `theBrokerLetsAPrincipalInOnlyAsItselfFromAClientIdOfItsOwn`, `theBrokersPasswordIsTheBearerTokenOfTheDeploymentsAuthenticator` / an unknown principal, another's client id, none, a bad or another's token refused | L8, negative | |
| PM3b-T8 | the broker's resource and topic checks / `aPrincipalMayUseOnlyItsTabsSessionQueueAndTopics` / another's events, another tab's, a wildcard, forging one's own events, the studio's own exchange refused | L8, negative | |
| PM3b-T9 | no events offered / `theBrokersChecksAreNotServedWhenTheStudioOffersNoEvents`, `theSessionNamesWhereEventsAreOffered` / `404`, and the session names the URL when offered | L3 | |
| PM3b-T10 | the browser's client faked / `events.test.ts`, 6 tests / its user, client id, will and topics, a watcher woken by its event, all woken when the connection drops and watched again when back, polling with no events, the browser build's default export, a principal's name in a topic | L1 | |
| PM3b-T11 | the real stack over TLS / `e2e-stack/stack.spec.ts`, an author compiles / the page receives the job's Succeeded event over `wss` | L6 | |
| PM3b-T12 | the real broker / `the broker lets a browser in only as its principal...` / an unknown principal and another's client id refused at CONNECT, another principal's events refused at SUBSCRIBE | L8, negative | |

**The one command:** `mise run check:config-studio`, then `mise run test:config-studio-browser` for PM3b-T11 and PM3b-T12.

## Probes of the broker, PM3a

Run on 2026-11-02 against RabbitMQ 4.4.0 from the stack's own archive, with a logging HTTP auth backend and an mqtt.js client:

- a Web MQTT CONNECT reaches `user_path` with `username`, `password` and `client_id`, then `vhost_path` with `client_id`
- a SUBSCRIBE asks `resource_path` to configure, write and read the queue `mqtt-subscription-<client id>qos0`, to read `amq.topic`, and `topic_path` to read the routing key, with `variable_map.client_id`. A PUBLISH asks to write `amq.topic` and the routing key. No check is made as a message is delivered, which (d) does not rely on
- a topic's `/` arrives as `.` in the routing key, and an AMQP publish to `amq.topic` reaches the MQTT subscriber
- an unclean drop publishes the will message on its topic
- a user the HTTP backend denies is refused with CONNACK 134
- Web MQTT over TLS with a PEM certificate and key works with the same checks

## Results, 2026-11-02

- `EventsTest` 13 of 13, `events.test.ts` 6 of 6, and `test:config-studio-browser` 20 on the fake service and 3 on the real stack, PM3b-T11 over `wss` and PM3b-T12 among them.
- Probes. With the check at delivery removed from `Notifier`, PM3b-T5 failed, and with the topic rule widened to any tab's events, PM3b-T8 failed. Both passed again once restored. A restored file keeps its old timestamp, so Maven's incremental build skipped it until it was touched.
- What the real stack found, each fixed in this slice. Erlang's test root certificate cannot serve TLS, and its default chain is signed with SHA-1, which Node and browsers refuse, so the harness makes a SHA-256 chain. The broker refuses an empty MQTT password before it asks any backend, so a tab signed in locally sends `local`. The library's browser build exports one default object, so `events.ts` takes `connect` from either export. Its default timers run in a worker from a blob URL, which the page's policy refuses, so it uses native timers. Jena writes an event's JSON with spaces, which the stack test now allows.

## Deviations from the sketch

1. **The compose stack offers no events.** Its broker container has neither plugin, so `studio:up --docker` leaves `LATTICE_STUDIO_EVENTS_URL` unset and the browser polls. The compose runner of the harness does the same.
2. **The relay keeps no subscribed frame.** A refused or lost watch costs a fallback read, as the sketch's §5.3 says.

## Decisions taken alone, for the maintainer's review

1. **PM-Q19 (c) and PM-Q21 (a) with (b)** are built as their leanings, while they are open. The broker is given the app's own credential, which the service checks, and each subscribe frame carries the headers again.
2. **The broker's own users come first** (`auth_backends.1 = internal`). A deployment's internal users need passwords no browser holds, as the stack's `guest` on loopback only does for development.
3. **A tab may read its own events topic only, not its principal's other tabs',** so one tab's watches never wake another.
4. **The broker's checks are served by the service on its own port,** and a proxy must not route `/api/broker/`. Moving them to a port of their own is a change to `StudioHttpServer` if a deployment wants it.
