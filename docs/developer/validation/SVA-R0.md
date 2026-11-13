<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-R0, what the broker's Web MQTT carries to a tab

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-R0 of the [plan](../plans/studio-visual-authoring.md), from section 4.2 (rule 9) and section 4.3 of the [sketch](../sketches/studio-visual-authoring.md), run on 2026-11-13.

Every number below was observed on one machine, over the loopback interface, which has no loss and no delay of its own. A real network, TLS and a proxy in front of the broker would be slower and may lose more. Nothing here was measured in a browser.

## What was probed and why

Rule 9 of the sketch limits a run to frames of at most 48 KiB, at most 128 frames, with at most 4 pending runs a tab, and the flow of section 4.2 sends the frames over QoS 0 on a clean session from one publisher channel with no pacing. Section 4.3 says that whether the broker drops QoS 0 messages to a slow tab before 128 frames, and what its largest packet is, are facts to probe before the limits are fixed. PM-3a probed the HTTP backend in the same way.

The probes are `web_mqtt_frames.mjs` and `publish_frames.py` in `tools/testing/studio_harness/src/lattice_testing_studio_harness/`, described in `web_mqtt_probes.md` beside them. A subscriber connects over Web MQTT as the studio's app does (the principal as user, the events key as password, client id `studio:<name>:<tab>`, a clean session, MQTT 3.1.1, QoS 0, the app's will). A helper publishes numbered frames of random bytes to `amq.topic` over AMQP as the service's relay does, on the routing key of the subscriber's events topic, and reports the SHA-256 of each payload before it sends. The subscriber compares the SHA-256 of what it receives with that digest, so "arrived intact" means the bytes are equal. The stack was already running and was not stopped, restarted or reconfigured. The probes publish only to topics of a tab they make up.

| Experiment | Question |
|---|---|
| P0 | does the digest check catch a changed byte |
| P1 | what is the largest single packet the broker carries to a subscriber |
| P2 | does a burst to a prompt subscriber arrive whole |
| P3 | does a burst to a subscriber that stops reading arrive whole, and where does loss start |
| P4 | does order hold with two publisher channels |
| P5 | does a frame arrive twice |
| P6 | what does a tab that drops and reconnects miss |
| P7 | does pacing the publisher remove loss |

## Versions observed

| Item | Value | Read by |
|---|---|---|
| RabbitMQ | 4.4.0 | `rabbit_misc:version()` on the running node, through `rabbitmqctl eval` |
| Erlang/OTP | 27, ERTS 15.2.7.14 | `erlang:system_info(otp_release)` and `(version)` on the node. The toolchain is mise's Erlang 27.3.4.19, from the folder name |
| node | v22.23.4 | `process.version` in the probe |
| mqtt.js | 5.16.1 | `node_modules/mqtt/package.json` |
| ws | 8.22.1 | `node_modules/ws/package.json` |
| pika | 1.4.4 | `pika.__version__` under `mise exec -- python` |
| kernel | 6.18.44-fc-v445 | `uname -r` |
| CPU | Intel(R) Xeon(R) Processor @ 2.10GHz, 4 logical processors | `/proc/cpuinfo` and `nproc` |
| memory | 16086 MiB | `free -m` |

The Web MQTT listener was plain `ws://127.0.0.1:15675/ws`, with the broker's AMQP on 127.0.0.1:5673.

## Configuration in force

The stack's generated `rabbitmq.conf` sets the stream listener, the Web MQTT listener (`web_mqtt.tcp.ip` and `.port`), the broker's default user, the two authentication backends (the broker's own users first, then the service's HTTP checks), `mqtt.allow_anonymous = false` and `mqtt.listeners.tcp = none`. It sets none of the limits below, so each is the broker's default. `rabbitmqctl` reached the node, with only `eval` of reads, so each value is read from the running node's application environment.

| Setting | Value | Set or default | Read by |
|---|---|---|---|
| `rabbit` `max_message_size` (the AMQP message limit) | 16777216 B (16 MiB) | default | `application:get_env(rabbit, max_message_size)` on the node |
| `rabbitmq_mqtt` `max_packet_size_authenticated` | 16777216 B (16 MiB) | default | `application:get_all_env(rabbitmq_mqtt)` on the node |
| `rabbitmq_mqtt` `max_packet_size_unauthenticated` | 65536 B (64 KiB) | default | the same |
| `rabbitmq_mqtt` `mailbox_soft_limit` | 200 | default | the same |
| `rabbitmq_mqtt` `prefetch` | 10 | default | the same |
| `rabbitmq_mqtt` `topic_alias_maximum` | 16 | default | the same |
| `rabbitmq_web_mqtt` | `tcp_config` port 15675 on 127.0.0.1, `num_tcp_acceptors` 10, `cowboy_opts` empty, no frame or message size entry | the listener is set, the rest default | `application:get_all_env(rabbitmq_web_mqtt)` on the node |

What the Web MQTT handler applies as a maximum WebSocket frame was not read, since no setting for it appears in the plugin's environment. It is open. The observed 16 MiB delivery in P1 is a packet larger than `max_packet_size_authenticated` by the size of its MQTT header and topic, which this probe does not explain. Whether that limit applies to a packet the broker sends to a client is not determined.

## P0, the digest check

The publisher flipped the last byte of frame 2 of 4 after taking its digest. The subscriber received 4 of 4 frames, counted 3 digests equal and 1 not equal, and the probe reported the check as caught. The first version of the publisher did not corrupt the frame it sent (a loop order error), and the check reported 4 equal, which is how the self-test was seen to work as a test. By reading the code, `once` in `web_mqtt_frames.mjs` keys a received frame by the channel and sequence in its header, takes the SHA-256 of the whole payload received, and counts it intact only when the publisher's digest for that key is equal. A frame with a damaged header counts as not equal too.

Across the 152 runs of the tables below, 254,478 frames arrived and every one had an equal digest, and no frame had a digest that differed.

## P1, the largest packet

One frame of each size, three runs each. The frame size is the whole MQTT payload including the 16 byte header the probe adds.

| Frame size (B) | Run | Received (of 1) | Digest equal | Arrived after (ms) | Publish loop (ms) | Publisher error |
| --- | --- | --- | --- | --- | --- | --- |
| 16384 | 1 | 1 | 1 | 2.4 | 0.2 | none |
| 16384 | 2 | 1 | 1 | 1.9 | 0.2 | none |
| 16384 | 3 | 1 | 1 | 1.9 | 0.2 | none |
| 49152 | 1 | 1 | 1 | 3.5 | 0.3 | none |
| 49152 | 2 | 1 | 1 | 2.8 | 0.2 | none |
| 49152 | 3 | 1 | 1 | 3 | 0.2 | none |
| 65536 | 1 | 1 | 1 | 4.2 | 0.2 | none |
| 65536 | 2 | 1 | 1 | 4 | 0.3 | none |
| 65536 | 3 | 1 | 1 | 3.3 | 0.2 | none |
| 262144 | 1 | 1 | 1 | 9.5 | 0.6 | none |
| 262144 | 2 | 1 | 1 | 10.9 | 0.6 | none |
| 262144 | 3 | 1 | 1 | 10 | 0.6 | none |
| 1048576 | 1 | 1 | 1 | 41.4 | 1.5 | none |
| 1048576 | 2 | 1 | 1 | 35.5 | 1.1 | none |
| 1048576 | 3 | 1 | 1 | 45.8 | 1 | none |
| 4194304 | 1 | 1 | 1 | 146.3 | 4.5 | none |
| 4194304 | 2 | 1 | 1 | 148.6 | 4.3 | none |
| 4194304 | 3 | 1 | 1 | 128.7 | 3.8 | none |
| 16776192 | 1 | 1 | 1 | 554.4 | 18.1 | none |
| 16776192 | 2 | 1 | 1 | 627.8 | 22.9 | none |
| 16776192 | 3 | 1 | 1 | 572 | 20.5 | none |
| 16777116 | 1 | 1 | 1 | 565.1 | 20.1 | none |
| 16777116 | 2 | 1 | 1 | 565.5 | 19.7 | none |
| 16777116 | 3 | 1 | 1 | 622.3 | 19.8 | none |
| 16777216 | 1 | 1 | 1 | 553 | 19 | none |
| 16777216 | 2 | 1 | 1 | 550.6 | 17.9 | none |
| 16777216 | 3 | 1 | 1 | 557 | 26.7 | none |
| 16778240 | 1 | 0 | 0 | none | 17.2 | channels closed by the broker: [1] |
| 16778240 | 2 | 0 | 0 | none | 22.4 | channels closed by the broker: [1] |
| 16778240 | 3 | 0 | 0 | none | 23.5 | (406, PRECONDITION_FAILED, over the AMQP message limit) |

Every size from 16 KiB to 16 MiB (16777216 B) arrived intact in 3 of 3 runs, the 16 MiB frame in 551 to 557 ms. The frame of 16 MiB + 1 KiB (16778240 B) never reached MQTT. The broker refused the AMQP publish and closed the publisher's channel, and the publisher reported it. The log has the line for each of these runs and each of the two smoke runs:

```
[error] operation basic.publish caused a channel exception precondition_failed: message size 16778240 is larger than configured max size 16777216
```

So the probe found no limit of Web MQTT below 16 MiB. It cannot find one above, since the AMQP message limit is the same value and was not changed.

## P2 and P4 with a prompt subscriber

A burst of 48 KiB frames to a subscriber that reads as they arrive. The P4 rows publish from two channels of one connection, each frame numbered per channel.

| Case | Run | Expected | Received | Missing | Duplicates | Out of order | Digest equal | Last frame at (ms) | Publish loop (ms) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P2 128 | 1 | 128 | 128 | 0 | 0 | 0 | 128 | 161 | 12.1 |
| P2 128 | 2 | 128 | 128 | 0 | 0 | 0 | 128 | 187.6 | 7.9 |
| P2 128 | 3 | 128 | 128 | 0 | 0 | 0 | 128 | 172.4 | 9.1 |
| P2 512 | 1 | 512 | 512 | 0 | 0 | 0 | 512 | 704.4 | 33.6 |
| P2 512 | 2 | 512 | 512 | 0 | 0 | 0 | 512 | 702.3 | 40.2 |
| P2 512 | 3 | 512 | 512 | 0 | 0 | 0 | 512 | 649 | 40.5 |
| P2 2000 | 1 | 2000 | 2000 | 0 | 0 | 0 | 2000 | 2851 | 175.6 |
| P2 2000 | 2 | 2000 | 2000 | 0 | 0 | 0 | 2000 | 2655.5 | 133.4 |
| P2 2000 | 3 | 2000 | 2000 | 0 | 0 | 0 | 2000 | 2564.5 | 129.8 |
| P4 two channels 128 | 1 | 256 | 256 | 0 | 0 | 0 | 256 | 329.2 | 13.6 |
| P4 two channels 128 | 2 | 256 | 256 | 0 | 0 | 0 | 256 | 366.3 | 15.4 |
| P4 two channels 128 | 3 | 256 | 256 | 0 | 0 | 0 | 256 | 342.6 | 14.2 |
| P4 two channels 512 | 1 | 1024 | 1024 | 0 | 0 | 0 | 1024 | 1333 | 62.4 |
| P4 two channels 512 | 2 | 1024 | 1024 | 0 | 0 | 0 | 1024 | 1637 | 58.2 |
| P4 two channels 512 | 3 | 1024 | 1024 | 0 | 0 | 0 | 1024 | 1569.9 | 102.3 |

## P3 and P4 with a subscriber that stops reading

The subscriber pauses its socket as the burst starts and resumes it 5000 ms later. A paused socket still reads until the stream's own buffer is full, so the table gives `bytesRead` at the start, 1000 ms in and at 5000 ms. A run is valid only when the last two are equal and no message was delivered during the stall. In all 107 stalled runs of P3, P4 and P7 they are equal, so every stalled run is valid. `bytesRead` stops at 98,742 to 98,747 B for 48 KiB frames (115,059 B in 2 runs) and at 66,793 to 66,824 B for 1 KiB frames. The unsent bytes in the broker's socket (from `/proc/net/tcp`) stay near 3.85 MB for bursts of 48 KiB frames, so the rest of a burst waited in the broker, which was not measured.

An earlier pass of the same default bursts, which sampled `bytesRead` only at the start and end, lost no frame in its 27 runs. It could not show that the reads had stopped, so it is not in the tables.

| Case | Frame (B) | Run | Expected | Received | Missing (seq) | bytesRead at start (B) | after 1 s (B) | at end of 5 s (B) | Reads stopped | Broker unsent (B) | Client unread (B) | Last frame at (ms) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P3 128 | 49152 | 1 | 128 | 128 | 0 | 302 | 98747 | 98747 | yes | 3852357 | 129162 | 5075.3 |
| P3 128 | 49152 | 2 | 128 | 128 | 0 | 302 | 98744 | 98744 | yes | 3852358 | 129161 | 5070.6 |
| P3 128 | 49152 | 3 | 128 | 128 | 0 | 302 | 98745 | 98745 | yes | 3852360 | 129165 | 5076.9 |
| P3 512 | 49152 | 1 | 512 | 512 | 0 | 302 | 98745 | 98745 | yes | 3852357 | 129163 | 5545.8 |
| P3 512 | 49152 | 2 | 512 | 512 | 0 | 302 | 98743 | 98743 | yes | 3852357 | 129163 | 5583.5 |
| P3 512 | 49152 | 3 | 512 | 512 | 0 | 302 | 98744 | 98744 | yes | 3852357 | 129163 | 5536.1 |
| P3 2000 | 49152 | 1 | 2000 | 2000 | 0 | 302 | 98745 | 98745 | yes | 3852357 | 129164 | 7381.2 |
| P3 2000 | 49152 | 2 | 2000 | 1952 | 48 (464-511) | 302 | 98745 | 98745 | yes | 3852355 | 129165 | 7406.6 |
| P3 2000 | 49152 | 3 | 2000 | 2000 | 0 | 302 | 98745 | 98745 | yes | 3852358 | 129162 | 7424.8 |
| P4 two channels stalled 128 | 49152 | 1 | 256 | 256 | 0 | 302 | 98744 | 98744 | yes | 3852357 | 129163 | 5272.9 |
| P4 two channels stalled 128 | 49152 | 2 | 256 | 256 | 0 | 302 | 98744 | 98744 | yes | 3852358 | 129163 | 5221.2 |
| P4 two channels stalled 128 | 49152 | 3 | 256 | 256 | 0 | 302 | 98745 | 98745 | yes | 3852358 | 129162 | 5235.2 |
| P4 two channels stalled 512 | 49152 | 1 | 1024 | 1024 | 0 | 302 | 98744 | 98744 | yes | 3852357 | 129163 | 6247.2 |
| P4 two channels stalled 512 | 49152 | 2 | 1024 | 1023 | 1 (ch0:400) | 302 | 98744 | 98744 | yes | 3852357 | 129163 | 6253 |
| P4 two channels stalled 512 | 49152 | 3 | 1024 | 1024 | 0 | 302 | 98743 | 98743 | yes | 3852357 | 129162 | 6258.3 |
| P3 1 KiB 128 | 1024 | 1 | 128 | 128 | 0 | 302 | 66824 | 66824 | yes | 0 | 70782 | 5018.5 |
| P3 1 KiB 128 | 1024 | 2 | 128 | 128 | 0 | 302 | 66821 | 66821 | yes | 0 | 70782 | 5021.3 |
| P3 1 KiB 128 | 1024 | 3 | 128 | 128 | 0 | 302 | 66815 | 66815 | yes | 0 | 70780 | 5021.1 |
| P3 1 KiB 256 | 1024 | 1 | 256 | 256 | 0 | 302 | 66813 | 66813 | yes | 95102 | 112991 | 5060.1 |
| P3 1 KiB 256 | 1024 | 2 | 256 | 256 | 0 | 302 | 66793 | 66793 | yes | 95085 | 113009 | 5038.8 |
| P3 1 KiB 256 | 1024 | 3 | 256 | 256 | 0 | 302 | 66795 | 66795 | yes | 95049 | 112997 | 5033.2 |
| P3 1 KiB 512 | 1024 | 1 | 512 | 512 | 0 | 302 | 66800 | 66800 | yes | 369611 | 113008 | 5081.7 |
| P3 1 KiB 512 | 1024 | 2 | 512 | 512 | 0 | 302 | 66821 | 66821 | yes | 369714 | 113007 | 5062.8 |
| P3 1 KiB 512 | 1024 | 3 | 512 | 512 | 0 | 302 | 66818 | 66818 | yes | 369681 | 113000 | 5074.3 |
| P3 1 KiB 1000 | 1024 | 1 | 1000 | 1000 | 0 | 302 | 66819 | 66819 | yes | 893041 | 112991 | 5128.9 |
| P3 1 KiB 1000 | 1024 | 2 | 1000 | 1000 | 0 | 302 | 66799 | 66799 | yes | 880704 | 125339 | 5118.9 |
| P3 1 KiB 1000 | 1024 | 3 | 1000 | 1000 | 0 | 302 | 66807 | 66807 | yes | 892996 | 113011 | 5122.8 |

The bisection's own runs, between 512 and 2000 frames of 48 KiB.

| Case | Frame (B) | Run | Expected | Received | Missing (seq) | bytesRead at start (B) | after 1 s (B) | at end of 5 s (B) | Reads stopped | Broker unsent (B) | Client unread (B) | Last frame at (ms) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P3 bisection 1256 | 49152 | 1 | 1256 | 1256 | 0 | 302 | 98743 | 98743 | yes | 3852357 | 129162 | 6516.2 |
| P3 bisection 1256 | 49152 | 2 | 1256 | 1256 | 0 | 302 | 98744 | 98744 | yes | 3852357 | 129163 | 6448.9 |
| P3 bisection 1256 | 49152 | 3 | 1256 | 1256 | 0 | 302 | 98744 | 98744 | yes | 3852357 | 129162 | 6524.5 |
| P3 bisection 1628 | 49152 | 1 | 1628 | 1628 | 0 | 302 | 98745 | 98745 | yes | 3852357 | 129162 | 7083.1 |
| P3 bisection 1628 | 49152 | 2 | 1628 | 1627 | 1 (119) | 302 | 98744 | 98744 | yes | 3852357 | 129165 | 6974.9 |
| P3 bisection 1628 | 49152 | 3 | 1628 | 1628 | 0 | 302 | 98744 | 98744 | yes | 3852358 | 129162 | 6943.5 |
| P3 bisection 1442 | 49152 | 1 | 1442 | 1442 | 0 | 302 | 98744 | 98744 | yes | 3852357 | 129163 | 6709.5 |
| P3 bisection 1442 | 49152 | 2 | 1442 | 1441 | 1 (483) | 302 | 98744 | 98744 | yes | 3852358 | 129161 | 6698 |
| P3 bisection 1442 | 49152 | 3 | 1442 | 1442 | 0 | 302 | 98747 | 98747 | yes | 3852357 | 129162 | 6802.4 |
| P3 bisection 1349 | 49152 | 1 | 1349 | 1349 | 0 | 302 | 98744 | 98744 | yes | 3852357 | 129162 | 6624.8 |
| P3 bisection 1349 | 49152 | 2 | 1349 | 1349 | 0 | 302 | 98743 | 98743 | yes | 3852357 | 129162 | 6690.4 |
| P3 bisection 1349 | 49152 | 3 | 1349 | 1349 | 0 | 302 | 98745 | 98745 | yes | 3852357 | 129162 | 6631 |
| P3 bisection 1395 | 49152 | 1 | 1395 | 1395 | 0 | 302 | 98745 | 98745 | yes | 3852358 | 129165 | 6717.5 |
| P3 bisection 1395 | 49152 | 2 | 1395 | 1395 | 0 | 302 | 98744 | 98744 | yes | 3852357 | 129162 | 6687.7 |
| P3 bisection 1395 | 49152 | 3 | 1395 | 1395 | 0 | 302 | 98745 | 98745 | yes | 3852357 | 129162 | 6620.4 |
| P3 bisection 1418 | 49152 | 1 | 1418 | 1418 | 0 | 302 | 98743 | 98743 | yes | 3852357 | 129163 | 6640.4 |
| P3 bisection 1418 | 49152 | 2 | 1418 | 1418 | 0 | 302 | 98746 | 98746 | yes | 3852358 | 129165 | 6684.5 |
| P3 bisection 1418 | 49152 | 3 | 1418 | 1418 | 0 | 302 | 98744 | 98744 | yes | 3852358 | 129162 | 6801.2 |
| P3 bisection 1430 | 49152 | 1 | 1430 | 1430 | 0 | 302 | 98744 | 98744 | yes | 3852357 | 129162 | 6769.1 |
| P3 bisection 1430 | 49152 | 2 | 1430 | 1430 | 0 | 302 | 98745 | 98745 | yes | 3852357 | 129162 | 6726.1 |
| P3 bisection 1430 | 49152 | 3 | 1430 | 1430 | 0 | 302 | 98744 | 98744 | yes | 3852357 | 129161 | 6697.4 |
| P3 bisection 1436 | 49152 | 1 | 1436 | 1435 | 1 (637) | 302 | 98745 | 98745 | yes | 3852357 | 129163 | 6667.3 |
| P3 bisection 1436 | 49152 | 2 | 1436 | 1436 | 0 | 302 | 98745 | 98745 | yes | 3852357 | 129162 | 6686.4 |
| P3 bisection 1436 | 49152 | 3 | 1436 | 1436 | 0 | 302 | 98743 | 98743 | yes | 3852357 | 129163 | 6727 |
| P3 bisection 1433 | 49152 | 1 | 1433 | 1432 | 1 (447) | 302 | 98745 | 98745 | yes | 3852358 | 129162 | 6665.9 |
| P3 bisection 1433 | 49152 | 2 | 1433 | 1433 | 0 | 302 | 98744 | 98744 | yes | 3852357 | 129162 | 6744.1 |
| P3 bisection 1433 | 49152 | 3 | 1433 | 1433 | 0 | 302 | 98745 | 98745 | yes | 3852357 | 129161 | 6664.6 |
| P3 bisection 1431 | 49152 | 1 | 1431 | 1431 | 0 | 302 | 98744 | 98744 | yes | 3852357 | 129162 | 6656.2 |
| P3 bisection 1431 | 49152 | 2 | 1431 | 1431 | 0 | 302 | 98744 | 98744 | yes | 3852357 | 129162 | 6691.8 |
| P3 bisection 1431 | 49152 | 3 | 1431 | 1431 | 0 | 302 | 98744 | 98744 | yes | 3852357 | 129163 | 6747.1 |
| P3 bisection 1432 | 49152 | 1 | 1432 | 1432 | 0 | 302 | 98744 | 98744 | yes | 3852357 | 129165 | 6698.9 |
| P3 bisection 1432 | 49152 | 2 | 1432 | 1432 | 0 | 302 | 98743 | 98743 | yes | 3852357 | 129162 | 6661.9 |
| P3 bisection 1432 | 49152 | 3 | 1432 | 1432 | 0 | 302 | 98744 | 98744 | yes | 3852357 | 129162 | 6787.2 |

The bisection ran as the notes describe, between 512 frames (none lost) and 2000 (lost), and reported that loss starts above 1432 frames and by 1433. That is not a threshold. Loss is sporadic and one frame at a time in most runs, so counts above and below that point lose and lose nothing in turn (1433 lossy and 1436 lossy, 1430 to 1432 not, 1442 lossy and 1628 lossy, and a later pass found 3000 to 3875 not and 4000 lossy). The table gives the runs for that reason, and the bisection should be read as the runs it made.

A second pass pushed the bursts further.

| Case | Frame (B) | Run | Expected | Received | Missing (seq) | bytesRead at start (B) | after 1 s (B) | at end of 5 s (B) | Reads stopped | Broker unsent (B) | Client unread (B) | Last frame at (ms) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P3 2000 | 49152 | 1 | 2000 | 2000 | 0 | 302 | 98747 | 98747 | yes | 3852357 | 129162 | 7488.3 |
| P3 2000 | 49152 | 2 | 2000 | 2000 | 0 | 302 | 98744 | 98744 | yes | 3852358 | 129162 | 7416.9 |
| P3 2000 | 49152 | 3 | 2000 | 2000 | 0 | 302 | 98744 | 98744 | yes | 3852357 | 129162 | 7477.3 |
| P3 4000 | 49152 | 1 | 4000 | 4000 | 0 | 302 | 98747 | 98747 | yes | 3852357 | 129162 | 10014.4 |
| P3 4000 | 49152 | 2 | 4000 | 3981 | 19 (546-564) | 302 | 98747 | 98747 | yes | 3848261 | 130186 | 10058.3 |
| P3 4000 | 49152 | 3 | 4000 | 4000 | 0 | 302 | 98745 | 98745 | yes | 3852357 | 129166 | 10123.1 |
| P3 1 KiB 1000 | 1024 | 1 | 1000 | 1000 | 0 | 302 | 66798 | 66798 | yes | 893115 | 113002 | 5126.3 |
| P3 1 KiB 1000 | 1024 | 2 | 1000 | 1000 | 0 | 302 | 66799 | 66799 | yes | 893127 | 113001 | 5115.5 |
| P3 1 KiB 1000 | 1024 | 3 | 1000 | 1000 | 0 | 302 | 66800 | 66800 | yes | 893048 | 113004 | 5141 |
| P3 1 KiB 5000 | 1024 | 1 | 5000 | 5000 | 0 | 302 | 66805 | 66805 | yes | 3868672 | 112999 | 5577.2 |
| P3 1 KiB 5000 | 1024 | 2 | 5000 | 5000 | 0 | 302 | 66804 | 66804 | yes | 3868672 | 113001 | 5664.5 |
| P3 1 KiB 5000 | 1024 | 3 | 5000 | 5000 | 0 | 302 | 66799 | 66799 | yes | 3868672 | 113001 | 5585.9 |
| P3 1 KiB 20000 | 1024 | 1 | 20000 | 19998 | 2 (6248-6249) | 302 | 66808 | 66808 | yes | 3868672 | 113001 | 7431.6 |
| P3 1 KiB 20000 | 1024 | 2 | 20000 | 20000 | 0 | 302 | 66809 | 66809 | yes | 3857408 | 125333 | 7225.4 |
| P3 1 KiB 20000 | 1024 | 3 | 20000 | 19993 | 7 (5022-5028) | 302 | 66813 | 66813 | yes | 3868672 | 113005 | 7332.7 |
| P3 bisection 3000 | 49152 | 1 | 3000 | 3000 | 0 | 302 | 115059 | 115059 | yes | 3862598 | 102610 | 8700 |
| P3 bisection 3000 | 49152 | 2 | 3000 | 3000 | 0 | 302 | 98745 | 98745 | yes | 3852357 | 129163 | 8738.5 |
| P3 bisection 3000 | 49152 | 3 | 3000 | 3000 | 0 | 302 | 98744 | 98744 | yes | 3852357 | 129162 | 8742.6 |
| P3 bisection 3500 | 49152 | 1 | 3500 | 3500 | 0 | 302 | 98744 | 98744 | yes | 3852357 | 129163 | 9459.2 |
| P3 bisection 3500 | 49152 | 2 | 3500 | 3500 | 0 | 302 | 98744 | 98744 | yes | 3852357 | 129163 | 9468.4 |
| P3 bisection 3500 | 49152 | 3 | 3500 | 3500 | 0 | 302 | 98744 | 98744 | yes | 3852356 | 129164 | 9641.4 |
| P3 bisection 3750 | 49152 | 1 | 3750 | 3750 | 0 | 302 | 98745 | 98745 | yes | 3852357 | 129163 | 9857.5 |
| P3 bisection 3750 | 49152 | 2 | 3750 | 3750 | 0 | 302 | 98742 | 98742 | yes | 3852357 | 129162 | 9650.9 |
| P3 bisection 3750 | 49152 | 3 | 3750 | 3750 | 0 | 302 | 98743 | 98743 | yes | 3852357 | 129162 | 9861.2 |
| P3 bisection 3875 | 49152 | 1 | 3875 | 3875 | 0 | 302 | 98744 | 98744 | yes | 3852358 | 129162 | 10002.5 |
| P3 bisection 3875 | 49152 | 2 | 3875 | 3875 | 0 | 302 | 98745 | 98745 | yes | 3852360 | 129162 | 9922.7 |
| P3 bisection 3875 | 49152 | 3 | 3875 | 3875 | 0 | 302 | 98744 | 98744 | yes | 3852357 | 129163 | 10088.4 |

Summed over the stalled runs of one channel and 48 KiB frames, 27 runs of 1256 frames or fewer lost nothing, and 6 of 33 runs of 1433 frames or more lost frames (4 lost one frame, 1 lost 19 consecutive frames and 1 lost 48). With 1 KiB frames, 15 of 15 runs of 1000 frames or fewer and 3 of 3 runs of 5000 lost nothing, and 2 of 3 runs of 20000 lost 2 and 7 consecutive frames. With two channels of 512 frames (1024 in all), 1 of 3 runs lost a frame, and two channels of 128 lost none in 3 runs. The broker's log had no line about a drop for any run, so a lost frame is silent there.

## P5, duplicates, and the order of P4

Counted in every run of the tables.

| Experiment | Runs | Frames published | Frames received | Duplicates | Out of order | Digest differs |
|---|---|---|---|---|---|---|
| P1 one frame | 30 | 30 | 27 | 0 | 0 | 0 |
| P2 prompt | 9 | 7920 | 7920 | 0 | 0 | 0 |
| P4 two channels, prompt | 6 | 3840 | 3840 | 0 | 0 | 0 |
| P3 stalled | 81 | 198933 | 198853 | 0 | 0 | 0 |
| P4 two channels, stalled | 6 | 3840 | 3839 | 0 | 0 | 0 |
| P7 paced | 20 | 40000 | 39999 | 0 | 0 | 0 |

The 27 frames received in P1 are the 27 the broker accepted over AMQP. The 3 of 16 MiB + 1 KiB were published and refused, so they count as not received. A frame lost is always a hole in a channel's sequence, never a repeat and never a swap.

## P6, a tab that drops and comes back

The first subscriber's socket was destroyed with no DISCONNECT at its 5th frame (P6a, paced at 25 ms) or its 3rd (P6b, where the publisher held after 10 frames until the second subscription was made). A second subscriber then connected with the same client id and a clean session.

| Case | Run | Frames sent | Dropped after frame | Subscriber 1 got | Subscriber 2 got | Subscriber 2 subscribed at (ms) | In both | In neither |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P6a paced | 1 | 20 | 5 | 0-4 | 5-19 | 124.3 | none | none |
| P6a paced | 2 | 20 | 5 | 0-4 | 5-19 | 125.2 | none | none |
| P6a paced | 3 | 20 | 5 | 0-4 | 5-19 | 120.4 | none | none |
| P6b gated | 1 | 20 | 3 | 0-2 | 10-19 | 23.2 | none | 3-9 |
| P6b gated | 2 | 20 | 3 | 0-2 | 10-19 | 20.8 | none | 3-9 |
| P6b gated | 3 | 20 | 3 | 0-2 | 10-19 | 17 | none | 3-9 |

In P6a nothing was lost. The second subscriber got every frame from 5 on, its subscription having been made 120 to 125 ms after the burst began, before the next frame was sent, so a reconnect that finishes between two frames costs nothing here. In P6b the publisher sent frames 3 to 9 while no subscription existed, and neither subscriber received them. A frame sent while a tab has no subscription is dropped, as the sketch's section 4.3 case 4 says.

## P7, pacing the publisher

2000 frames of 48 KiB, stalled for 5000 ms, five runs of each pace. Pace 0 is the control and is P3's burst again. The pace is a sleep of that many ms after each frame, so the loop took longer than the pace times 2000 (the publish loop column).

| Pace (ms) | Run | Expected | Received | Missing (seq) | bytesRead start / after 1 s / end (B) | Reads stopped | Publish loop (ms) | Last frame at (ms) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 1 | 2000 | 2000 | 0 | 302 / 98744 / 98744 | yes | 157.2 | 7680 |
| 0 | 2 | 2000 | 2000 | 0 | 302 / 115059 / 115059 | yes | 152.9 | 7608.5 |
| 0 | 3 | 2000 | 2000 | 0 | 302 / 98744 / 98744 | yes | 123 | 7439.8 |
| 0 | 4 | 2000 | 2000 | 0 | 302 / 98745 / 98745 | yes | 119.9 | 7544.1 |
| 0 | 5 | 2000 | 1999 | 1 (1091) | 302 / 98745 / 98745 | yes | 124.8 | 7497.3 |
| 1 | 1 | 2000 | 2000 | 0 | 302 / 98744 / 98744 | yes | 2452.2 | 7632.9 |
| 1 | 2 | 2000 | 2000 | 0 | 302 / 98743 / 98743 | yes | 2491.2 | 7595.9 |
| 1 | 3 | 2000 | 2000 | 0 | 302 / 98745 / 98745 | yes | 2470.7 | 7637.6 |
| 1 | 4 | 2000 | 2000 | 0 | 302 / 98746 / 98746 | yes | 2433.4 | 7576.4 |
| 1 | 5 | 2000 | 2000 | 0 | 302 / 98744 / 98744 | yes | 2449.4 | 7420 |
| 5 | 1 | 2000 | 2000 | 0 | 302 / 98747 / 98747 | yes | 10601.1 | 10598.2 |
| 5 | 2 | 2000 | 2000 | 0 | 302 / 98744 / 98744 | yes | 10593.1 | 10590.2 |
| 5 | 3 | 2000 | 2000 | 0 | 302 / 98744 / 98744 | yes | 10568.4 | 10565.3 |
| 5 | 4 | 2000 | 2000 | 0 | 302 / 98743 / 98743 | yes | 10594.5 | 10591.8 |
| 5 | 5 | 2000 | 2000 | 0 | 302 / 98744 / 98744 | yes | 10591.1 | 10588.5 |
| 20 | 1 | 2000 | 2000 | 0 | 302 / 98744 / 98744 | yes | 40810.2 | 40793.2 |
| 20 | 2 | 2000 | 2000 | 0 | 302 / 98747 / 98747 | yes | 40841 | 40823 |
| 20 | 3 | 2000 | 2000 | 0 | 302 / 98746 / 98746 | yes | 40874.2 | 40856.4 |
| 20 | 4 | 2000 | 2000 | 0 | 302 / 98746 / 98746 | yes | 40869.2 | 40851.9 |
| 20 | 5 | 2000 | 2000 | 0 | 302 / 98744 / 98744 | yes | 40833.6 | 40816 |

## What this means for the limits

| Limit of rule 9 | Verdict | Rows |
|---|---|---|
| a frame of at most 48 KiB | supported, with no ceiling found by the broker | P1 rows 16384 to 16777216, runs 1 to 3 |
| at most 128 frames a run, about 6 MiB | supported, with a margin of 8 in frames and in bytes | P2 128, P3 128, P4 two channels 128 prompt and stalled, and the first loss at P4 two channels stalled 512 run 2 |
| QoS 0 on a clean session | supported where a run stays within the limits, and the loss it allows is the one the sketch describes | P3 128, P3 2000 run 2, P6b runs 1 to 3 |
| one publisher channel with no pacing | supported to 128 frames, and pacing as a remedy left open | P4 rows, P5 table, P7 pace 0 run 5 and the paced rows |
| at most 4 pending runs a tab | supported on loopback, with a margin of 2 at the worst case | P2 512, P3 512, P4 two channels stalled 512 |

**A frame of at most 48 KiB.** Frames of 16 KiB, 48 KiB, 64 KiB, 256 KiB, 1 MiB, 4 MiB and up to 16 MiB arrived intact in 3 of 3 runs each (P1), so the broker's Web MQTT does not set a limit near 48 KiB. The probe could not go above 16 MiB. The limit is therefore the design's, set by what a tab holds and renders, and the broker's evidence permits it to stay at 48 KiB or to rise. No value is recommended from this evidence, and 48 KiB can stay.

**At most 128 frames a run, about 6 MiB.** In every run of 128 frames of 48 KiB, prompt, stalled for 5000 ms, or on two channels, all frames arrived intact, in order and once (P2 128, P3 128, P4 128). The smallest backlog that lost a frame was 1024 frames in all, two channels of 512, which is 48 MiB and 8 times the limit (P4 stalled 512, run 2). On one channel the first loss was at 1433 frames, about 67 MiB. The limit is supported with a wide margin on loopback. Keep 128 frames and 6 MiB. A rise to 256 frames would still be a quarter of the smallest backlog that lost, but the evidence gives no reason to take it.

**QoS 0 on a clean session.** In the stalled runs, loss appeared only at backlogs of 1024 frames or more of 48 KiB, or 20000 frames of 1 KiB, and was silent, with no line in the broker's log. Within 128 frames nothing was lost even with the reads stopped for 5000 ms, so the sketch's design (a loss found at the deadline, a run offered again) holds for runs of the limit's size. P6b shows what a tab that is away misses, every frame sent while it has no subscription, which is the sketch's case 4. Whether QoS 1 or a persistent session would keep those frames was not probed and is open. The cause of the sporadic loss at large backlogs was not determined. `mailbox_soft_limit` bounds what a QoS 0 subscriber's connection holds and is 200 by default, and these probes do not show whether it is the cause.

**One publisher channel with no pacing.** No frame arrived twice or out of order in any run, on one channel or two (P4, P5). Unpaced 128 frames lost nothing. At 2000 frames, 1 of 5 unpaced runs lost a frame and none of 15 paced runs did (P7), but at a pace of 1 ms the 2000 frames were all published within the 5000 ms stall, so that run held the same backlog as the control, and the difference between 1 of 5 and 0 of 15 is too small to say that pacing helps. Pacing is not needed at 128 frames and is left open as a remedy for larger runs.

**At most 4 pending runs a tab.** This limit is the service's, with a `429`, and the broker does not see it. What the probes bear on is the worst case, four runs of 128 frames delivered to one tab together, which is 512 frames and 24 MiB. 512 frames on one channel arrived whole in 3 of 3 prompt runs and 3 of 3 stalled runs (P2 512, P3 512). Two channels of 128 (256 frames) lost nothing in 3 of 3 stalled runs, and two channels of 512 (1024 frames) lost one frame in 1 of 3 (P4 two channels stalled 512, run 2). So the worst case sits within the range that lost nothing, with a margin of 2 to the smallest backlog that lost, which is a smaller margin than the 128-frame limit has alone. Keep 4. If the margin matters on a real network, lower this limit before the frame limit.

These are findings for one machine and the loopback interface. A slower tab, a network that adds delay, a TLS terminator or a proxy that buffers or has its own frame limit could lose at smaller backlogs, and none of that was probed.

## What could not be determined, and what would

1. **The largest packet Web MQTT carries.** The AMQP message limit (16 MiB) stopped the publisher first. Raising `max_message_size` is a broker change, which this slice does not make, and would answer it. Publishing over MQTT would meet `max_packet_size_authenticated` instead.
2. **Why a packet of 16 MiB was delivered with a limit of 16 MiB on packets.** Reading the plugin's code, or a run with the setting lowered, would say whether the limit applies to a packet the broker sends.
3. **The Web MQTT frame limit.** Its value was not in the plugin's environment. A run with a frame larger than a candidate, or the plugin's code, would answer it.
4. **The cause of the sporadic loss, and its rate.** A run with `mqtt.mailbox_soft_limit` raised would show whether it is the setting, and the broker's debug log or the connection process's mailbox length would show a drop directly. The rate (about 1 run in 6 at 1433 frames or more) rests on 33 runs and would need tens of runs a count to give a threshold.
5. **QoS 1 and a persistent session.** The subscriber of these scripts is QoS 0 and clean, as the app is. A variant would show whether either keeps the frames P3 and P6 lost.
6. **A real network, TLS and a proxy.** The probes ran over plain `ws` on loopback with no browser. A run of the same scripts against the stack's `wss` listener, through the proxy a deployment uses, and a browser's own client would answer this.
7. **A longer stall, several tabs, and the broker's memory.** The stall was 5000 ms, one tab at a time, and the broker's memory was not measured. A burst of 94 MiB (2000 frames) waited in the broker's memory during the stall, by inference from the socket's queues.

## The one command

With the studio stack running with events on, from the repository root.

```bash
mise exec -- node tools/testing/studio_harness/src/lattice_testing_studio_harness/web_mqtt_frames.mjs --out /tmp/sva-r0.json
```

It takes about 25 minutes and writes its file when it ends. `--only P1` runs one experiment, and P7 alone needs `--p7-frames 2000`. The options are in `web_mqtt_probes.md`.

## Deviations and what was changed in the probes

The probe scripts had not been run to completion and needed these changes.

- **A refused publish was not reported.** A broker closes the publisher's channel asynchronously, so the publisher reported no error for the 16 MiB + 1 KiB frame. It now processes events after its loop and reports a closed channel.
- **No self-test of the digest check.** P0 and the publisher's `--corrupt-seq` were added, and the first version of the self-test's corruption was applied after the frame was queued, which the check caught by reporting 4 equal digests.
- **The stall could not show reads had stopped.** `bytesRead` rose by about 98 KB between the start and end of a stall, the stream's buffer filling. A sample at 1000 ms, and a `readsStopped` verdict, were added.
- **A bisection could run without limit.** `--budget-min` bounds it, and it records `converged` false where it stops.
- **P7 had no control.** A pace of 0 was added.
- **The log filter kept ordinary connection lines.** It now keeps warnings, errors and words about drops, packets and limits.

The slice board and the status record were not touched by this pack, and nothing was committed.
