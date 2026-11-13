<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Probes of the broker's Web MQTT for content frames

Two files in this folder probe how the broker carries large and many MQTT messages to a browser tab over Web MQTT. They answer the questions of slice SVA-R0, and their findings are recorded in the Validation Pack SVA-R0 ([`docs/developer/validation/SVA-R0.md`](../../../../../docs/developer/validation/SVA-R0.md)). They are not tests and not part of `check`. They measure, and fail on nothing but a probe that could not run.

| File | Does |
|---|---|
| `web_mqtt_frames.mjs` | connects a subscriber as the studio's app does (the principal as user, the events key as password, client id `studio:<name>:<tab>`, a clean session, MQTT 3.1.1, QoS 0, the app's will message), runs the experiments P0 to P7, and prints each run |
| `publish_frames.py` | publishes numbered frames of a given size to `amq.topic` over AMQP, as the service's relay does, and reports the SHA-256 of each. The node probe starts it |

The two sit in the harness's package folder because the harness has no folder for probes and a new kind of directory needs an accepted ADR. Nothing imports either file.

## Running them

The probes need a studio stack already running with events on (`LATTICE_STUDIO_EVENTS_URL` set, as `mise run studio:up` does), because they read `GET /api/session` for the Web MQTT address and the events key, and read the broker's AMQP URI from `.build/config-studio/infra/broker/amqp-uri`. They do not start, stop or change the stack. They publish only to topics of a tab they make up, so they reach nothing a real tab listens to. The URI and the key are read when a probe runs and never printed or written.

```bash
mise exec -- node tools/testing/studio_harness/src/lattice_testing_studio_harness/web_mqtt_frames.mjs --out /tmp/sva-r0.json
```

The packages `mqtt` and `ws` come from the repository's `node_modules`, and the publisher needs `pika` in the project environment. A full run at three runs a case takes about 25 minutes, mostly P3's stalls and its bisection and P7's pacing. Run one experiment at a time with `--only` to keep a failure in one from losing the others, and write each to its own `--out`, since a run writes its file only when it ends.

| Option | Default | Means |
|---|---|---|
| `--only P1,P3` | all | the experiments to run. P0 is a self-test, see below |
| `--runs N` | 3 | runs of each case |
| `--stall-ms N` | 5000 | how long P3 and P7 stop the subscriber's reads |
| `--p3-counts A,B,C` | 128,512,2000 | the bursts of 48 KiB frames P3 sends. Giving it also leaves out the stalled two-channel runs of P4 |
| `--p3-small-counts A,B,C` | 128,256,512,1000 | the bursts of 1 KiB frames P3 sends |
| `--budget-min N` | 15 | the wall time P3 gives its bisections. A bisection that has not met it stops and records the bracket it reached, with `converged` false |
| `--p7-frames N` | the smallest P3 burst of 48 KiB frames that lost any in the same process, or 128 where 128 lost | the burst P7 paces. Run alone, P7 has no P3 results to read, so give it this option (SVA-R0 used 2000) |
| `--base URL` | `http://127.0.0.1:8090` | the service |
| `--principal NAME` | `developer` | the local principal |
| `--uri-file FILE` | the stack's `amqp-uri` | where the broker's AMQP URI is read |
| `--log FILE` | the stack's RabbitMQ log | read only, for the lines a run adds |
| `--out FILE` | none | every run as JSON |

If the broker's `rabbitmqctl` can be reached through `mise`, the probe also reads the settings in force (the broker's version and Erlang's, the MQTT packet limits and mailbox limit, the AMQP message limit, the Web MQTT settings) and prints them first, with no write. It uses `mise where erlang` for Erlang's `bin` folder and the stack's own unpacked RabbitMQ under `.build/config-studio/infra`, and names the node from the log file's name.

## What each experiment does

| Experiment | Does |
|---|---|
| P0 | publishes 4 frames, the publisher flipping a byte of frame 2 after taking its digest, and expects the subscriber to count 3 digests equal and 1 not. It shows that "arrived intact" is a comparison of SHA-256 of the bytes received with that of the bytes the publisher meant to send, and fails the process (exit code 1) if it does not |
| P1 | one frame of 16 KiB up to 16 MiB + 1 KiB, to find the largest packet the broker carries to a subscriber. Above 16 MiB the AMQP publish is refused by the broker's AMQP message limit, so the Web MQTT limit is not reached by this probe, and the publisher reports the refused channel |
| P2 | a burst to a prompt subscriber, 128, 512 and 2000 frames of 48 KiB |
| P3 | a burst to a subscriber whose reads are stopped for the stall, 48 KiB frames and 1 KiB frames, then a bisection between the largest burst of each that lost nothing and the smallest that lost some. Where loss is sporadic, as SVA-R0 found, the bisection's result is not a threshold, because bursts above and below it lose and lose nothing in turn. Read the runs, not the bisection's result |
| P4 | two publisher channels at once, prompt and stalled, with order checked on each channel |
| P5 | duplicates, counted in every run |
| P6 | an unclean drop of the subscriber's socket and a second connection with the same client id and a clean session, with the publisher paced (P6a) or holding after 10 frames until the second subscription is made (P6b) |
| P7 | the stalled burst of P7's frame count published with a pause of 0, 1, 5 and 20 ms after each frame |

## How a slow subscriber is made

`mqtt.js` is given a `createWebsocket` hook that keeps the `ws` WebSocket it makes. P3 and P7 call `pause()` on that WebSocket's underlying `net.Socket` as the burst starts and `resume()` after the stall, which stops the process reading the socket once the stream's own buffer is full. A paused Node socket still reads up to that buffer, about 96 KiB of 48 KiB frames or 64 KiB of 1 KiB frames, and no more. Each stalled run therefore records the socket's `bytesRead` at three points, at the start, 1 second in (`bytesReadSettled`) and at the end of the stall, with the count of delivered messages at the start and end, and the loopback socket's queues from `/proc/net/tcp` at the end. The run is valid only where `bytesRead` is the same at 1 second and at the end and no message was delivered during the stall (`readsStopped`). The line the probe prints says INVALID otherwise, and such a run does not count.

## What counts as lost

The publisher takes the SHA-256 of every payload before it sends and reports it at the end. A frame counts as received only if a message with its channel and sequence arrived, and as intact only if the SHA-256 of the bytes received equals the publisher's. `received` counts distinct frames, so a duplicate is counted apart, in `dup`. A frame is missing if none arrived by the time the subscriber had been quiet for `idleMs` (2 seconds, 3 seconds for P1) after the publisher finished and the stall ended. A broker that delivers later than that would show a missing frame that is only late, and P3's last frame arrives within 11 seconds of the start of the burst in every run of SVA-R0.

The broker's log lines a run adds are kept when they carry a warning, an error or a word about a drop, a packet or a limit. Normal connection lines are not kept.
