// SPDX-License-Identifier: MPL-2.0
// A browser tab's subscriber for a test (SVA-R5). It connects over the broker's Web MQTT as the studio's app does
// (apps/config-studio/src/events.ts): the principal as user, the events key as password, the client id `studio:<name>:<tab>`, a clean
// session, QoS 0 and the app's will, and subscribes to the tab's events topic. It prints each message as one JSON line.
//
//   node tab_events.mjs --base URL --principal NAME --tab TAB
//
// Standard output, one JSON object a line: `{"event":"subscribed"}` once subscribed, `{"event":"message","at":ms,"cloudEvent":{...}}` for
// each message, `{"event":"closed"}` when the connection ends and `{"event":"error","message":...}`. It ends on a line `stop` on
// standard input, after a DISCONNECT, or when standard input closes. The events key is read from the service's session description inside
// this process and is never printed, and neither is an error message that holds it. The broker's certificate is the harness's own, made
// for the run and trusted by no one else, so the connection does not verify it. A browser's trust of a real certificate is out of scope.

import { createInterface } from "node:readline";
import mqtt from "mqtt";
import WebSocket from "ws";

const args = Object.fromEntries(process.argv.slice(2).map((a, i, all) => (a.startsWith("--") ? [a.slice(2), all[i + 1]] : null)).filter(Boolean));
const say = (o) => process.stdout.write(JSON.stringify(o) + "\n");
const topicName = (p) => Buffer.from(p, "utf8").toString("base64url");

const res = await fetch(`${args.base}/api/session`, { headers: { "X-Lattice-Principal": args.principal } });
const session = await res.json();
if (!session.events || !session.eventsPassword) {
  say({ event: "error", message: "the studio offers no events" });
  process.exit(2);
}
const key = session.eventsPassword;
const scrub = (text) => String(text).split(key).join("***");
const name = topicName(args.principal);
const base = `studio/u/${name}/${args.tab}`;
const start = Date.now();

const client = mqtt.connect(session.events, {
  username: args.principal,
  password: key,
  clientId: `studio:${name}:${args.tab}`,
  clean: true,
  reconnectPeriod: 0,
  rejectUnauthorized: false,
  will: { topic: `${base}/watch`, payload: JSON.stringify({ type: "gone" }), qos: 0, retain: false },
  createWebsocket: (url, protocols, o) => new WebSocket(url, protocols, { ...o.wsOptions, rejectUnauthorized: false }),
});
client.on("error", (e) => say({ event: "error", message: scrub(e.message ?? e) }));
client.on("close", () => say({ event: "closed" }));
client.on("message", (_topic, payload) => {
  let cloudEvent = null;
  try {
    cloudEvent = JSON.parse(payload.toString("utf8"));
  } catch {
    cloudEvent = { unparsed: payload.length };
  }
  say({ event: "message", at: Date.now() - start, cloudEvent });
});
client.on("connect", async () => {
  try {
    await client.subscribeAsync(`${base}/events`, { qos: 0 });
    say({ event: "subscribed" });
  } catch (e) {
    say({ event: "error", message: scrub(e.message ?? e) });
  }
});

const finish = () => client.end(false, {}, () => process.exit(0));
const input = createInterface({ input: process.stdin });
input.on("line", (line) => line.trim() === "stop" && finish());
input.on("close", finish);
