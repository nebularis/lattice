<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Probes of the broker's Web MQTT for content frames

Two files in this folder probe how the broker carries large and many MQTT messages to a browser tab over Web MQTT. They answer the questions of slice SVA-R0, and their findings are recorded in SVA-R0 (`docs/developer/validation/SVA-R0.md`, not yet written). They are not tests and not part of `check`. They measure, and fail on nothing but a probe that could not run.

| File | Does |
|---|---|
| `web_mqtt_frames.mjs` | connects a subscriber as the studio's app does (the principal as user, the events key as password, client id `studio:<name>:<tab>`, a clean session, MQTT 3.1.1, QoS 0, the app's will message), runs the experiments P1 to P7, and prints each run |
| `publish_frames.py` | publishes numbered frames of a given size to `amq.topic` over AMQP, as the service's relay does, and reports the SHA-256 of each. The node probe starts it |

The two sit in the harness's package folder because the harness has no folder for probes and a new kind of directory needs an accepted ADR. Nothing imports either file.

## Running them

The probes need a studio stack already running with events on (`LATTICE_STUDIO_EVENTS_URL` set, as `mise run studio:up` does), because they read `GET /api/session` for the Web MQTT address and the events key, and read the broker's AMQP URI from `.build/config-studio/infra/broker/amqp-uri`. They do not start, stop or change the stack. They publish only to topics of a tab they make up, so they reach nothing a real tab listens to. The URI and the key are read when a probe runs and never printed or written.

```bash
mise exec -- node tools/testing/studio_harness/src/lattice_testing_studio_harness/web_mqtt_frames.mjs --out /tmp/sva-r0.json
```

The packages `mqtt` and `ws` come from the repository's `node_modules`, and the publisher needs `pika` in the project environment. A full run takes about 30 to 45 minutes, mostly P3's stalls and its bisection.

| Option | Default | Means |
|---|---|---|
| `--only P1,P3` | all | the experiments to run |
| `--runs N` | 3 | runs of each case |
| `--stall-ms N` | 5000 | how long P3 and P7 stop the subscriber's reads |
| `--p7-frames N` | the smallest P3 burst of 48 KiB frames that lost any, or 128 where 128 lost | the burst P7 paces |
| `--base URL` | `http://127.0.0.1:8090` | the service |
| `--principal NAME` | `developer` | the local principal |
| `--uri-file FILE` | the stack's `amqp-uri` | where the broker's AMQP URI is read |
| `--log FILE` | the stack's RabbitMQ log | read only, for the lines a run adds |
| `--out FILE` | none | every run as JSON |

If the broker's `rabbitmqctl` can be reached through `mise`, the probe also reads the settings in force (the broker's version, the MQTT packet limits and mailbox limit, the AMQP message limit) and prints them first.

## How a slow subscriber is made

`mqtt.js` is given a `createWebsocket` hook that keeps the `ws` WebSocket it makes. P3 and P7 call `pause()` on that WebSocket's underlying `net.Socket` as the burst starts and `resume()` after the stall, which stops the process reading the socket. Each stalled run records the socket's `bytesRead` and the count of delivered messages at both ends of the stall, and the loopback socket's queues from `/proc/net/tcp`, to show the stall held.
