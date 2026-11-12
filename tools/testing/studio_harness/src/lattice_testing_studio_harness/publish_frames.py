# SPDX-License-Identifier: MPL-2.0
"""AMQP publisher for the Web MQTT frame probes (SVA-R0).

It publishes numbered frames to the broker's `amq.topic` the way the studio's relay does, over one connection and one or more
channels, with no publisher confirms. It reads the broker URI from a file at run time and never prints it.

Protocol with `web_mqtt_frames.mjs`, one JSON object a line on standard output:

- `{"event": "ready"}` once connected, with every payload made, so the time of a burst is the time of sending alone
- on a line `go` on standard input, it publishes. With `--gate-after K` it stops after K frames and waits for a line `resume`
- `{"event": "done", ...}` with the counts, the seconds the publishing loop took, and the SHA-256 of every payload as `channel:seq`

A payload is a 16 byte header, the bytes `SVA0` then run, channel and seq as unsigned 32 bit big-endian integers, followed by
random bytes. Its total length is `--size`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
import time

import pika

HEADER = struct.Struct(">4sIII")


def say(**event: object) -> None:
    sys.stdout.write(json.dumps(event) + "\n")
    sys.stdout.flush()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--uri-file", required=True, help="a file holding the broker's AMQP URI")
    ap.add_argument("--routing-key", required=True)
    ap.add_argument("--count", type=int, required=True, help="frames for each channel")
    ap.add_argument("--size", type=int, required=True, help="bytes in each payload, header included")
    ap.add_argument("--run", type=int, default=0)
    ap.add_argument("--channels", type=int, default=1, help="channels on the one connection. Frames alternate between them")
    ap.add_argument("--pace-ms", type=float, default=0.0, help="a pause after each frame")
    ap.add_argument("--gate-after", type=int, default=0, help="wait for `resume` after this many frames in all, 0 for no wait")
    args = ap.parse_args()
    if args.size < HEADER.size:
        raise SystemExit("the size must be at least %d" % HEADER.size)

    with open(args.uri_file, encoding="utf-8") as f:
        uri = f.read().strip()
    params = pika.URLParameters(uri)
    params.heartbeat = 60
    params.blocked_connection_timeout = 120
    connection = pika.BlockingConnection(params)
    channels = [connection.channel() for _ in range(args.channels)]

    frames = []
    digests = {}
    for seq in range(args.count):
        for channel in range(args.channels):
            payload = HEADER.pack(b"SVA0", args.run, channel, seq) + os.urandom(args.size - HEADER.size)
            frames.append((channel, seq, payload))
            digests["%d:%d" % (channel, seq)] = hashlib.sha256(payload).hexdigest()
    say(event="ready")

    if sys.stdin.readline().strip() != "go":
        return 2
    sent, error = 0, None
    started = time.perf_counter()
    try:
        for channel, seq, payload in frames:
            if args.gate_after and sent == args.gate_after:
                say(event="gated", sent=sent)
                if sys.stdin.readline().strip() != "resume":
                    break
            channels[channel].basic_publish(exchange="amq.topic", routing_key=args.routing_key, body=payload)
            sent += 1
            if args.pace_ms:
                time.sleep(args.pace_ms / 1000.0)
    except Exception as exc:  # a refused or closed channel is a result, not a failure of the probe
        error = "%s: %s" % (type(exc).__name__, exc)
    loop_seconds = time.perf_counter() - started
    try:
        connection.close()
    except Exception as exc:
        error = error or "close %s: %s" % (type(exc).__name__, exc)
    total_seconds = time.perf_counter() - started
    say(event="done", sent=sent, loopSeconds=loop_seconds, totalSeconds=total_seconds, error=error, sha256=digests)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
