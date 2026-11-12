// SPDX-License-Identifier: MPL-2.0
// Probes of the broker's Web MQTT for content frames (SVA-R0). A tab's subscriber listens over Web MQTT, connected as the studio's
// app connects (apps/config-studio/src/events.ts), while a helper publishes numbered frames over AMQP to `amq.topic`, as the
// service's relay does. Needs a running studio stack with events on. It changes nothing in the stack and writes no file unless
// `--out` names one. Neither the events password nor the broker's password is printed.
//
//   mise exec -- node tools/testing/studio_harness/src/lattice_testing_studio_harness/web_mqtt_frames.mjs [--only P1,P2,...]
//
// Options: --runs N (3), --base URL (http://127.0.0.1:8090), --principal NAME (developer), --out FILE (the runs as JSON),
// --uri-file FILE (the broker's AMQP URI, read at run time), --log FILE (the broker's log, read for lines a run adds),
// --stall-ms N (5000), --p3-counts A,B (128,512,2000) and --p3-small-counts (128,256,512,1000), the bursts P3 sends, --p7-frames N (the burst size P7 paces, default the smallest P3 burst that lost frames).

import { spawn, execFile } from "node:child_process";
import { readFileSync, writeFileSync, statSync, openSync, readSync, closeSync, existsSync } from "node:fs";
import { createHash, randomBytes } from "node:crypto";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { promisify } from "node:util";
import mqtt from "mqtt";
import WebSocket from "ws";

const run = promisify(execFile);
const here = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(here, "../../../../..");
const KIB = 1024;
const MIB = 1024 * KIB;

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, a, i, all) => (a.startsWith("--") ? [...acc, [a.slice(2), all[i + 1]?.startsWith("--") || all[i + 1] === undefined ? "true" : all[i + 1]]] : acc), []),
);
const RUNS = Number(args.runs ?? 3);
const BASE = args.base ?? "http://127.0.0.1:8090";
const PRINCIPAL = args.principal ?? "developer";
const URI_FILE = resolve(ROOT, args["uri-file"] ?? ".build/config-studio/infra/broker/amqp-uri");
const LOG_FILE = resolve(ROOT, args.log ?? ".build/config-studio/infra/rabbitmq/log/studio@localhost.log");
const STALL_MS = Number(args["stall-ms"] ?? 5000);
const ONLY = new Set((args.only ?? "P1,P2,P3,P4,P5,P6,P7").split(","));
const PUBLISHER = resolve(here, "publish_frames.py");
const results = [];

const log = (...m) => process.stderr.write(m.join(" ") + "\n");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const now = () => Number(process.hrtime.bigint()) / 1e6;
const topicName = (p) => Buffer.from(p, "utf8").toString("base64url");
const newTab = () => Array.from(randomBytes(12), (b) => "abcdefghijklmnopqrstuvwxyz0123456789"[b % 36]).join("");

async function session() {
  const res = await fetch(`${BASE}/api/session`, { headers: { "X-Lattice-Principal": PRINCIPAL } });
  const body = await res.json();
  if (!body.events || !body.eventsPassword) throw new Error("the studio offers no events: LATTICE_STUDIO_EVENTS_URL is not set");
  return { url: body.events, password: body.eventsPassword };
}

function ranges(numbers) {
  const out = [];
  for (const n of [...numbers].sort((a, b) => a - b)) {
    const last = out[out.length - 1];
    if (last && n === last[1] + 1) last[1] = n;
    else out.push([n, n]);
  }
  return out.map(([a, b]) => (a === b ? `${a}` : `${a}-${b}`)).join(",");
}

/** The bytes a log file has gained since `offset`, as lines. Read only. */
function logSince(offset) {
  try {
    const size = statSync(LOG_FILE).size;
    if (size <= offset) return [];
    const fd = openSync(LOG_FILE, "r");
    const buf = Buffer.alloc(size - offset);
    readSync(fd, buf, 0, buf.length, offset);
    closeSync(fd);
    return buf.toString("utf8").split("\n").filter(Boolean);
  } catch {
    return [];
  }
}
const logSize = () => (existsSync(LOG_FILE) ? statSync(LOG_FILE).size : 0);

/** Unread bytes in the kernel's receive queue of a loopback socket by its local port, from /proc, and the broker side's unsent bytes. */
function queues(localPort, brokerPort) {
  try {
    const rows = readFileSync("/proc/net/tcp", "utf8").split("\n").slice(1);
    const hex = (n) => n.toString(16).toUpperCase().padStart(4, "0");
    const out = {};
    for (const r of rows) {
      const f = r.trim().split(/\s+/);
      if (f.length < 5) continue;
      const [la, lp] = f[1].split(":");
      const [ra, rp] = f[2].split(":");
      const [tx, rx] = f[4].split(":").map((h) => parseInt(h, 16));
      if (lp === hex(localPort) && rp === hex(brokerPort)) out.clientRecvQ = rx;
      if (lp === hex(brokerPort) && rp === hex(localPort)) out.brokerSendQ = tx;
      void la; void ra;
    }
    return out;
  } catch {
    return {};
  }
}

/** A tab's subscriber, connected as the app connects: the principal as user, the events key as password, `studio:<name>:<tab>`, a
 *  clean session, MQTT 3.1.1 (the library's default), QoS 0, and the will the app sets. */
async function open(sess, tab, opts = {}) {
  const name = topicName(PRINCIPAL);
  const base = `studio/u/${name}/${tab}`;
  const sub = { tab, base, routingKey: `studio.u.${name}.${tab}.events`, msgs: [], closed: null, errors: [], raw: null, lastAt: 0, onMessage: null };
  const client = mqtt.connect(sess.url, {
    username: PRINCIPAL,
    password: sess.password,
    clientId: `studio:${name}:${tab}`,
    clean: true,
    reconnectPeriod: 0,
    will: { topic: `${base}/watch`, payload: JSON.stringify({ type: "gone" }), qos: 0, retain: false },
    // Keeps the raw WebSocket, so a probe can stop reading its socket or drop it uncleanly.
    createWebsocket: (url, protocols, o) => (sub.raw = new WebSocket(url, protocols, o.wsOptions)),
  });
  sub.client = client;
  client.on("error", (e) => sub.errors.push(String(e.message ?? e)));
  client.on("close", () => (sub.closed ??= { at: now(), code: sub.rawCode ?? null }));
  client.once("connect", () => sub.raw.on("close", (code, reason) => ((sub.rawCode = code), (sub.rawReason = String(reason)))));
  client.on("message", (_t, payload) => {
    const at = now();
    sub.lastAt = at;
    const magic = payload.length >= 16 ? payload.toString("latin1", 0, 4) : "";
    const m = { at, bytes: payload.length, channel: magic === "SVA0" ? payload.readUInt32BE(8) : -1, seq: magic === "SVA0" ? payload.readUInt32BE(12) : -1, sha: createHash("sha256").update(payload).digest("hex") };
    sub.msgs.push(m);
    sub.onMessage?.(m, sub);
  });
  await new Promise((res, rej) => {
    client.once("connect", res);
    client.once("error", rej);
    client.once("close", () => rej(new Error("closed before CONNACK")));
  });
  await client.subscribeAsync(`${base}/events`, { qos: 0 });
  return sub;
}

/** The AMQP helper as a child: resolves with its handle once it has made every payload and connected. */
function startPublisher(sub, o) {
  const argv = ["exec", "--", "python", PUBLISHER, "--uri-file", URI_FILE, "--routing-key", sub.routingKey, "--count", String(o.count), "--size", String(o.size),
    "--channels", String(o.channels ?? 1), "--pace-ms", String(o.paceMs ?? 0), "--run", String(o.runId ?? 0)];
  if (o.gateAfter) argv.push("--gate-after", String(o.gateAfter));
  const child = spawn("mise", argv, { cwd: ROOT, stdio: ["pipe", "pipe", "pipe"] });
  const h = { child, done: null, stderr: "", waiters: [] };
  let buf = "";
  const events = [];
  child.stdout.on("data", (d) => {
    buf += d;
    let i;
    while ((i = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, i);
      buf = buf.slice(i + 1);
      try {
        const e = JSON.parse(line);
        events.push(e);
        if (e.event === "done") h.done = e;
        h.waiters = h.waiters.filter((w) => !w(e));
      } catch { /* a stray line from the tool is not an event */ }
    }
  });
  child.stderr.on("data", (d) => (h.stderr += d));
  h.exited = new Promise((r) => child.on("exit", r));
  h.wait = (event) => new Promise((res, rej) => {
    const hit = events.find((e) => e.event === event);
    if (hit) return res(hit);
    h.waiters.push((e) => (e.event === event ? (res(e), true) : false));
    child.on("exit", () => rej(new Error(`the publisher ended before "${event}": ${h.stderr.slice(-300)}`)));
  });
  h.send = (line) => child.stdin.write(line + "\n");
  return h;
}

/** One run: connect, publish `count` frames of `size` bytes from `channels` channels, optionally stalling the subscriber's reads. */
async function once(sess, label, o) {
  const tab = newTab();
  const offset = logSize();
  const sub = await open(sess, tab);
  const pub = startPublisher(sub, o);
  await pub.wait("ready");
  const expected = o.count * (o.channels ?? 1);
  const rec = { label, ...o, expected, received: 0 };
  let stall = null;
  const t0 = now();
  if (o.stallMs) {
    const sock = sub.raw._socket;
    sock.pause();
    stall = { bytesReadAtStart: sock.bytesRead, msgsAtStart: sub.msgs.length };
  }
  pub.send("go");
  let resumedAt = o.stallMs ? t0 + o.stallMs : t0;
  if (o.stallMs) {
    await sleep(o.stallMs);
    const sock = sub.raw._socket;
    stall.bytesReadAtEnd = sock.bytesRead;
    stall.msgsAtEnd = sub.msgs.length;
    stall.queues = queues(sock.localPort, Number(new URL(sess.url).port));
    sock.resume();
    resumedAt = now();
  }
  const idleMs = o.idleMs ?? 2000;
  const deadline = now() + (o.timeoutMs ?? 60000);
  for (;;) {
    await sleep(25);
    const t = now();
    if (sub.closed) break;
    if (pub.done && sub.msgs.length >= expected) break;
    if (pub.done && t >= resumedAt && t - Math.max(sub.lastAt, resumedAt, pub.doneAt ?? (pub.doneAt = t)) > idleMs) break;
    if (t > deadline) { rec.timedOut = true; break; }
  }
  await Promise.race([pub.exited, sleep(5000)]);
  const done = pub.done ?? { sha256: {}, sent: 0, error: `no "done" from the publisher: ${pub.stderr.slice(-300)}` };
  const seen = new Set();
  const last = {};
  let dup = 0, outOfOrder = 0, shaOk = 0, shaBad = 0;
  for (const m of sub.msgs) {
    const key = `${m.channel}:${m.seq}`;
    if (seen.has(key)) dup++; else seen.add(key);
    if (last[m.channel] !== undefined && m.seq < last[m.channel]) outOfOrder++;
    last[m.channel] = Math.max(last[m.channel] ?? -1, m.seq);
    if (done.sha256[key] === m.sha) shaOk++; else shaBad++;
  }
  const missing = [];
  for (const key of Object.keys(done.sha256)) if (!seen.has(key)) missing.push(key);
  const missingByChannel = {};
  for (const key of missing) { const [c, s] = key.split(":").map(Number); (missingByChannel[c] ??= []).push(s); }
  const lines = logSince(offset).filter((l) => /mqtt|web_mqtt|packet|drop|error|warn|closing|exceed|too large/i.test(l));
  Object.assign(rec, {
    received: seen.size, messages: sub.msgs.length, dup, outOfOrder, shaOk, shaBad,
    missingCount: missing.length, missing: Object.entries(missingByChannel).map(([c, s]) => (o.channels > 1 ? `ch${c}:` : "") + ranges(s)).join(" "),
    firstMs: sub.msgs.length ? +(sub.msgs[0].at - t0).toFixed(1) : null,
    lastMs: sub.msgs.length ? +(sub.msgs[sub.msgs.length - 1].at - t0).toFixed(1) : null,
    publishMs: done.loopSeconds !== undefined ? +(done.loopSeconds * 1000).toFixed(1) : null,
    publishedFrames: done.sent, publisherError: done.error ?? null,
    closed: sub.closed ? { code: sub.rawCode ?? null, reason: sub.rawReason ?? null, afterMs: +(sub.closed.at - t0).toFixed(1) } : null,
    clientErrors: sub.errors, stall, brokerLog: lines.slice(0, 6).map((l) => l.slice(0, 300)), brokerLogLines: lines.length,
  });
  try { sub.closed ? null : await sub.client.endAsync(); } catch { /* already gone */ }
  results.push(rec);
  const verdict = `${rec.received}/${expected}`;
  log(`  ${label} ${JSON.stringify(o)} -> received ${verdict}, missing [${rec.missing}], dup ${dup}, outOfOrder ${outOfOrder}, sha ok ${shaOk}, last ${rec.lastMs} ms, publish ${rec.publishMs} ms${rec.closed ? `, CLOSED ${JSON.stringify(rec.closed)}` : ""}${rec.publisherError ? `, publisher: ${rec.publisherError}` : ""}${stall ? `, stall bytesRead ${stall.bytesReadAtStart}->${stall.bytesReadAtEnd}, msgs ${stall.msgsAtStart}->${stall.msgsAtEnd}` : ""}`);
  return rec;
}

async function repeat(sess, label, o, n = RUNS) {
  const out = [];
  for (let i = 1; i <= n; i++) out.push(await once(sess, `${label} run ${i}`, { ...o, runId: i }));
  return out;
}

async function p1(sess) {
  log("P1 largest packet");
  const sizes = [16 * KIB, 48 * KIB, 64 * KIB, 256 * KIB, MIB, 4 * MIB, 16 * MIB - KIB, 16 * MIB - 100, 16 * MIB, 16 * MIB + KIB];
  for (const size of sizes) await repeat(sess, `P1 ${size}`, { count: 1, size, idleMs: 3000, timeoutMs: 90000 });
}

async function p2(sess) {
  log("P2 burst to a prompt subscriber, P4 order, P5 duplicates");
  for (const count of [128, 512, 2000]) await repeat(sess, `P2 ${count}`, { count, size: 48 * KIB });
  for (const count of [128, 512]) await repeat(sess, `P4 two channels ${count}`, { count, size: 48 * KIB, channels: 2 });
}

async function p3(sess) {
  log("P3 burst to a slow subscriber");
  const counts = (name, fallback) => String(args[name] ?? fallback).split(",").map(Number);
  const big = counts("p3-counts", "128,512,2000");
  const small = counts("p3-small-counts", "128,256,512,1000");
  for (const count of big) await repeat(sess, `P3 ${count}`, { count, size: 48 * KIB, stallMs: STALL_MS });
  if (!args["p3-counts"]) for (const count of [128, 512]) await repeat(sess, `P4 two channels stalled ${count}`, { count, size: 48 * KIB, channels: 2, stallMs: STALL_MS });
  // The same bursts with small frames, which tells a limit in frames from one in bytes.
  for (const count of small) await repeat(sess, `P3 1 KiB ${count}`, { count, size: KIB, stallMs: STALL_MS });
  for (const [size, tried] of [[48 * KIB, big], [KIB, small]]) {
    const lossyAt = (c) => results.some((r) => r.label.startsWith(`P3 ${size === KIB ? "1 KiB " : ""}${c} `) && (r.missingCount > 0 || r.closed));
    const hi = tried.find(lossyAt);
    const lo = tried.filter((c) => hi !== undefined && c < hi).pop();
    if (hi === undefined || lo === undefined) log(`  bisection of ${size} B frames skipped, ${hi === undefined ? "no burst lost a frame" : "the smallest burst already lost frames"}`);
    else await bisect(sess, size, lo, hi);
  }
}

/** Between a burst that lost nothing (`lo`) and one that lost some (`hi`), halve until they are adjacent. Each step is RUNS runs, and a step
 *  counts as lossy when any run of it lost a frame. */
async function bisect(sess, size, lo, hi) {
  const lossy = (runs) => runs.some((r) => r.missingCount > 0 || r.closed);
  const first = results.filter((r) => r.label.startsWith(`P3 ${size === KIB ? "1 KiB " : ""}${hi} `));
  const base = results.filter((r) => r.label.startsWith(`P3 ${size === KIB ? "1 KiB " : ""}${lo} `));
  if (!base.length || !first.length || lossy(base) || !lossy(first)) { log(`  bisection of ${size} B frames between ${lo} and ${hi} skipped, the ends are not lossless and lossy`); return; }
  log(`P3 bisection of ${size} B frames between ${lo} (none lost) and ${hi} (lost)`);
  while (hi - lo > 1) {
    const mid = Math.floor((lo + hi) / 2);
    const runs = await repeat(sess, `P3 bisect ${size === KIB ? "1 KiB " : "48 KiB "}${mid}`, { count: mid, size, stallMs: STALL_MS });
    if (lossy(runs)) hi = mid; else lo = mid;
  }
  log(`  loss starts above ${lo} frames and by ${hi} frames, for ${size} B frames`);
  results.push({ label: `P3 bisection result ${size} B`, lastLossless: lo, firstLossy: hi, size });
}

async function p6(sess) {
  log("P6 reconnect");
  for (let i = 1; i <= RUNS; i++) await reconnect(sess, `P6a paced run ${i}`, { count: 20, size: 48 * KIB, paceMs: 25, runId: i }, 4, null);
  for (let i = 1; i <= RUNS; i++) await reconnect(sess, `P6b gated run ${i}`, { count: 20, size: 48 * KIB, gateAfter: 10, runId: i }, 2, 10);
}

/** Subscriber 1 is dropped uncleanly (the socket destroyed, no DISCONNECT) on its `dropAt`th frame, then a second connects with the same
 *  client id and a clean session. With `gate`, the publisher holds after that many frames until the second subscriber is subscribed. */
async function reconnect(sess, label, o, dropAt, gate) {
  const tab = newTab();
  const sub1 = await open(sess, tab);
  const pub = startPublisher(sub1, o);
  await pub.wait("ready");
  let sub2 = null, reopened = null, subscribedAt = null;
  const t0 = now();
  sub1.onMessage = (_m, s) => {
    if (s.msgs.length === dropAt + 1 && !reopened) {
      s.raw.terminate();
      reopened = (async () => {
        sub2 = await open(sess, tab);
        subscribedAt = now() - t0;
        if (gate) pub.send("resume");
      })();
    }
  };
  pub.send("go");
  const deadline = now() + 30000;
  while (!(pub.done && reopened) && now() < deadline) await sleep(25);
  await reopened;
  await sleep(2000);
  const seqs = (s) => (s ? s.msgs.map((m) => m.seq) : []);
  const first = seqs(sub1), second = seqs(sub2);
  const both = first.filter((s) => second.includes(s));
  const rec = {
    label, ...o, dropAfterFrames: dropAt + 1, firstSubscriberGot: ranges(first), secondSubscriberGot: ranges(second), inBoth: ranges(both),
    secondSubscriberSubscribedAtMs: subscribedAt === null ? null : +subscribedAt.toFixed(1), publishedFrames: pub.done?.sent ?? null,
    notDeliveredToEither: ranges([...Array(o.count).keys()].filter((s) => !first.includes(s) && !second.includes(s))),
    firstChannelClosed: sub1.closed ? { code: sub1.rawCode ?? null } : null,
  };
  results.push(rec);
  log(`  ${label}: subscriber 1 got ${rec.firstSubscriberGot}, subscriber 2 (subscribed ${rec.secondSubscriberSubscribedAtMs} ms) got ${rec.secondSubscriberGot}, in both ${rec.inBoth || "none"}, neither ${rec.notDeliveredToEither || "none"}`);
  try { await sub2?.client.endAsync(); } catch { /* gone */ }
}

async function p7(sess) {
  log("P7 publisher pacing");
  const lossy = results.filter((r) => r.label?.startsWith("P3 ") && !r.label.includes("bisect") && r.size === 48 * KIB && r.missingCount > 0);
  const at128 = results.some((r) => r.label?.startsWith("P3 128 ") && r.missingCount > 0);
  const frames = Number(args["p7-frames"] ?? (at128 ? 128 : Math.min(...lossy.map((r) => r.count), Infinity)));
  if (!Number.isFinite(frames)) { log("  no burst of 48 KiB frames lost any, so there is nothing to pace"); results.push({ label: "P7 not run", reason: "no loss in P3 to pace" }); return; }
  log(`  pacing ${frames} frames of 48 KiB${at128 ? "" : " (P3 lost none at 128, so this goes beyond the brief)"}`);
  for (const paceMs of [1, 5, 20]) await repeat(sess, `P7 ${frames} pace ${paceMs} ms`, { count: frames, size: 48 * KIB, paceMs, stallMs: STALL_MS });
}

async function configuration() {
  const cfg = { node: process.version, mqttjs: JSON.parse(readFileSync(resolve(ROOT, "node_modules/mqtt/package.json"), "utf8")).version, ws: JSON.parse(readFileSync(resolve(ROOT, "node_modules/ws/package.json"), "utf8")).version, platform: `${process.platform} ${process.arch}` };
  try {
    const home = (await run("mise", ["where", "erlang"], { cwd: ROOT })).stdout.trim();
    const ctl = resolve(ROOT, ".build/config-studio/infra/rabbitmq_server-4.4.0/sbin/rabbitmqctl");
    const node = /([^/]+)\.log$/.exec(LOG_FILE)?.[1];
    const expr = "{rabbit_misc:version(), erlang:system_info(otp_release), erlang:system_info(version), application:get_env(rabbit, max_message_size), [P || {K, _} = P <- application:get_all_env(rabbitmq_mqtt), lists:member(K, [mailbox_soft_limit, max_packet_size_authenticated, max_packet_size_unauthenticated, prefetch, topic_alias_maximum])], application:get_all_env(rabbitmq_web_mqtt)}.";
    const { stdout } = await run(ctl, ["-n", node, "eval", expr], { env: { ...process.env, PATH: `${home}/bin:${process.env.PATH}` }, timeout: 60000 });
    cfg.broker = stdout.split("\n").filter((l) => !l.startsWith("warning:")).join(" ").replace(/\s+/g, " ").trim();
  } catch (e) {
    cfg.broker = `not read: ${String(e.message).slice(0, 120)}`;
  }
  log("configuration", JSON.stringify(cfg));
  results.push({ label: "configuration", ...cfg });
}

const sess = await session();
await configuration();
if (ONLY.has("P1")) await p1(sess);
if (ONLY.has("P2") || ONLY.has("P4") || ONLY.has("P5")) await p2(sess);
if (ONLY.has("P3")) await p3(sess);
if (ONLY.has("P6")) await p6(sess);
if (ONLY.has("P7")) await p7(sess);
if (args.out) writeFileSync(resolve(args.out), JSON.stringify(results, null, 1));
const bad = results.filter((r) => r.shaBad > 0 || r.publisherError);
log(`done, ${results.length} records, ${bad.length} with a bad digest or a publisher error`);
process.exit(0);
