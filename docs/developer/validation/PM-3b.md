<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: PM-3a and PM-3b, events over the broker's Web MQTT

**Unit:** [`projection-maintenance`](../status/projection-maintenance.md), slices PM-3a and PM-3b of the [plan](../plans/projection-maintenance.md), from the [sketch](../sketches/browser-events-over-web-mqtt.md), built on 2026-11-02 in autonomous mode.

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
| PM3b-T12 | the real broker / `the broker lets a browser in only as its principal, with the session's key...` / `guest`, a local principal without the session's key, an unknown principal and another's client id refused at CONNECT, another principal's events refused at SUBSCRIBE | L8, negative | |
| PM3b-T13 | the broker's checks / `aLocalPrincipalConnectsOnlyWithTheKeyAPageOfTheStudiosOwnOriginReads`, `theBrokersChecksAnswerOnlyUnderTheirSecret` / a local principal without the key, a path without the secret or with another, refused | L8, negative | |
| PM3b-T14 | the stack / `tools/test_config_studio_stack.py`, 5 tests / the broker's user and secret made once a stack and private, its configuration with no `guest`, the compose override for the kind of Docker, and the compose broker published on loopback alone | L1, L3 | |

**The one command:** `mise run check:config-studio`, then `mise run test:config-studio-browser` for PM3b-T11 and PM3b-T12.

## Probes of the broker, PM-3a

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

## The broker's user, the local key and the Docker stack, 2026-11-02

Reviewing why the Docker stack offered no events found a hole in both development stacks. Their broker kept `guest`/`guest`, accepted from loopback, and its users come before the service's checks. Web MQTT checks no `Origin` and no CORS rule guards a WebSocket, so any page a developer's browser opened could connect as `guest`, read every tab's events and publish to any tab. A page could also connect as a local principal, whose check trusted the name. PM-3's Origin check had stopped both.

- **One broker user.** The stack makes a user `studio` with a password once for each stack, in `.build/config-studio/infra/broker` with the URIs, readable by their owner alone, and the broker has no `guest`. A new broker gets the user from its configuration. One an older stack made gets it, and loses `guest`, through `rabbitmqctl` when the stack starts it, and `studio:up` says when a running broker still has `guest`. The `studio:*` tasks of mise.toml read the URIs as `*_FILE`.
- **The broker's checks need their secret,** `/api/broker/<secret>/<check>`, made with the password.
- **A local principal needs the session's key,** made at each start of the service, which only a page of the studio's own origin can read.
- **The Docker stack offers events.** `studio:infra` and `studio:up --docker` write the broker's configuration and add an override for the kind of Docker. Docker Desktop, on any platform, forwards `host.docker.internal` to the host's loopback, where the service listens, so `docker-compose.desktop.yml` publishes the ports on loopback. Docker Engine on Linux does not, so `docker-compose.host-network.yml` puts the broker and the add-in proxy on the host's network, each listener on loopback, and names the node `rabbit@localhost`, since Erlang's port mapper listens on loopback alone. The add-in proxy had the same gap on Docker Engine before this change.

Run on 2026-11-02, macOS, Docker Desktop 29.8.0:

- `test:config-studio-browser`, 20 and 3, with PM3b-T12 refusing `guest` and a keyless local principal on the real broker. `EventsTest` 15 of 15, `events.test.ts` 6 of 6, the stack's tests 11 of 11.
- The compose broker with `docker-compose.desktop.yml`, on ports clear of the developer's own stack, and a service on the host: a local principal with the session's key connected and subscribed, `guest`/`guest` and a local principal without the key were refused, so the broker reached the service's checks on the host's loopback through `host.docker.internal`.
- The compose broker with `docker-compose.host-network.yml` in Docker Desktop's VM, which stands in for a Linux host: it booted with every listener on `127.0.0.1` on the stack's ports and `studio` its only user, and through a stand-in for the service on the same network's loopback it authenticated an allowed user and refused another under the secret. Its first boot failed on the port mapper until the node was named `rabbit@localhost`.
- The Caddyfile renders to `0.0.0.0:3443` and `host.docker.internal:8090` by default, and to `127.0.0.1:3443` and `127.0.0.1:8090` with the host network's settings.

Not run: Docker Engine on a Linux host itself, and anything on Windows. On Windows the processes stack runs `rabbitmqctl.bat` through `cmd`, as `studio:down` already does, the password and secret hold only `A-Za-z0-9_-`, and Docker Desktop takes the Desktop override.

## Deviations from the sketch

1. **The compose stack offers no events.** Its broker container has neither plugin, so `studio:up --docker` leaves `LATTICE_STUDIO_EVENTS_URL` unset and the browser polls. The compose runner of the harness does the same.
2. **The relay keeps no subscribed frame.** A refused or lost watch costs a fallback read, as the sketch's §5.3 says.

## Decisions taken alone, for the maintainer's review

1. **PM-Q19 (c) and PM-Q21 (a) with (b)** are built as their leanings, while they are open. The broker is given the app's own credential, which the service checks, and each subscribe frame carries the headers again.
2. **The broker's own users come first** (`auth_backends.1 = internal`), so a deployment's broker users need passwords no page can know. The first version of this pack called the stack's `guest` on loopback acceptable for development, which it was not, since any page a browser opens can reach loopback over a WebSocket. The section above removes it.
3. **A tab may read its own events topic only, not its principal's other tabs',** so one tab's watches never wake another.
4. **The broker's checks are served by the service on its own port,** under their secret, and a proxy must not route `/api/broker/`.
5. **Docker Engine on Linux puts the broker and the add-in proxy on the host's network,** rather than binding a listener for the broker's checks to every interface, so the service stays on loopback and no host firewall stands between them. Docker Desktop is told apart by `docker info`. Other engines on macOS or Windows, such as Colima, take the Desktop override, which has not been tried on them.
