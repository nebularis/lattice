// SPDX-License-Identifier: MPL-2.0
// An object generated from the aggregate's boundary shape (SVA-P5, SVA-Q12 answered (c)). One small object, with the root, each owned member the shape
// requires and a value for each property it requires, and data at size stays BL-11. Generation is a pure function of the form's spec, the root and the
// sample world, with no randomness and no clock. A value is derived from the property's IRI and the node's path in the shape, a member's identifier is
// minted under its parent's as the form mints one, so generating twice gives the same object and a step built from it gives the same TriG. What a shape
// requires and the generator cannot give is left to the author, and the generator says which and why. A reference is taken from a node of its class in the
// sample world and never invented, so where the world holds none the reference is left.

import type { FieldSpec, FormSpec, FormValues, Limits, OwnedSpec, OwnedValues } from "./objectForm";
import { newMemberId } from "./objectForm";
import type { World } from "./simulator";

const XSD = "http://www.w3.org/2001/XMLSchema#";
const SH_LITERAL = "http://www.w3.org/ns/shacl#Literal";
const TYPE_LINE = /^<([^>]+)> <http:\/\/www\.w3\.org\/1999\/02\/22-rdf-syntax-ns#type> <([^>]+)> \.$/;

/** The most members or values one property is given, so that an object stays small. A shape that asks for more is given this many, and says so. */
export const MOST_PER_PROPERTY = 25;

/** The nodes of a class in the world, in the order of their IRIs. */
export type Instances = (cls: string) => readonly string[];

/** The nodes the world types by a class, as written in any of its graphs, never a subclass, since the world holds no schema. */
export function instancesIn(world: World): Instances {
  const byClass = new Map<string, Set<string>>();
  for (const lines of Object.values(world.graphs)) {
    for (const line of lines) {
      const m = TYPE_LINE.exec(line);
      if (m) byClass.set(m[2], (byClass.get(m[2]) ?? new Set()).add(m[1]));
    }
  }
  const sorted = new Map([...byClass].map(([cls, nodes]) => [cls, [...nodes].sort()] as const));
  return (cls) => sorted.get(cls) ?? [];
}

export interface Generated {
  form: FormValues;
  /** What the shape requires and was not given, each as a sentence for the author. */
  left: string[];
}

const lastOf = (iri: string) => iri.slice(Math.max(iri.lastIndexOf("#"), iri.lastIndexOf("/")) + 1);
const words = (name: string) => name.replace(/([a-z0-9])([A-Z])/g, "$1 $2").replace(/[-_]+/g, " ").toLowerCase();

/** FNV-1a over the UTF-8 of a text, 32 bits, so that a value is a function of the property and the node's path. */
function hashOf(text: string): number {
  let h = 0x811c9dc5;
  for (const b of new TextEncoder().encode(text)) {
    h ^= b;
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h;
}

type Value = { values: string[] } | { reason: string };

// --- numbers --------------------------------------------------------------------------------------------------------------------

const INTEGERS: Record<string, [number, number]> = {
  integer: [-Infinity, Infinity],
  long: [-Infinity, Infinity],
  int: [-2147483648, 2147483647],
  short: [-32768, 32767],
  byte: [-128, 127],
  nonNegativeInteger: [0, Infinity],
  positiveInteger: [1, Infinity],
  nonPositiveInteger: [-Infinity, 0],
  negativeInteger: [-Infinity, -1],
  unsignedLong: [0, Infinity],
  unsignedInt: [0, 4294967295],
  unsignedShort: [0, 65535],
  unsignedByte: [0, 255],
};
const DECIMALS = new Set(["decimal", "double", "float"]);

/** A bound as a number scaled by `scale`, rounded to the whole scaled number it is within a rounding error of, or undefined where it is not a number. */
function scaled(text: string, scale: number): number | undefined {
  const n = Number(text);
  return text.trim() === "" || !Number.isFinite(n) ? undefined : n * scale;
}

const nearest = (x: number) => (Math.abs(x - Math.round(x)) < 1e-6 ? Math.round(x) : x);

/** The least and greatest whole number, at `scale`, that the limits and the datatype's own range allow, or a reason when a bound cannot be read. */
function range(limits: Limits | undefined, own: [number, number], scale: number): { lo: number; hi: number } | { reason: string } {
  let lo = own[0] * scale;
  let hi = own[1] * scale;
  const bounds: [keyof Limits, (x: number) => void][] = [
    ["minInclusive", (x) => (lo = Math.max(lo, Math.ceil(nearest(x))))],
    ["minExclusive", (x) => (lo = Math.max(lo, Math.floor(nearest(x)) + 1))],
    ["maxInclusive", (x) => (hi = Math.min(hi, Math.floor(nearest(x))))],
    ["maxExclusive", (x) => (hi = Math.min(hi, Math.ceil(nearest(x)) - 1))],
  ];
  for (const [name, apply] of bounds) {
    const text = limits?.[name];
    if (typeof text !== "string") continue;
    const x = scaled(text, scale);
    if (x === undefined) return { reason: `sh:${name} is ${JSON.stringify(text)}, which is not a number` };
    apply(x);
  }
  return lo > hi ? { reason: "no number satisfies the bounds the shape states" } : { lo, hi };
}

function numbers(limits: Limits | undefined, local: string, seed: number, n: number): Value {
  const integer = local in INTEGERS;
  const scale = integer ? 1 : 100;
  const r = range(limits, integer ? INTEGERS[local] : [-Infinity, Infinity], scale);
  if ("reason" in r) return r;
  const base = integer ? 1 + (seed % 900) : 100 * (1 + (seed % 900)) + ((seed >>> 10) % 100);
  const start = Math.min(Math.max(base, r.lo), r.hi);
  const values: string[] = [];
  for (let i = 0; i < n && start + i <= r.hi; i++) {
    const v = start + i;
    values.push(integer ? String(v) : `${v < 0 ? "-" : ""}${Math.trunc(Math.abs(v) / 100)}.${String(Math.abs(v) % 100).padStart(2, "0")}`);
  }
  return { values };
}

// --- strings, dates, booleans ---------------------------------------------------------------------------------------------------

/** The text a pattern matches when it is a literal text between optional anchors, and undefined for any pattern that needs a regular expression to satisfy. */
function literalPattern(pattern: string): string | undefined {
  const text = pattern.replace(/^\^/, "").replace(/\$$/, "");
  return text !== "" && !/[\\^$.|?*+()[\]{}]/.test(text) ? text : undefined;
}

function strings(limits: Limits | undefined, path: string, seed: number, n: number): Value {
  const min = limits?.minLength ?? 0;
  const max = limits?.maxLength ?? Infinity;
  if (min > max) return { reason: "its minimum length is above its maximum length" };
  const values: string[] = [];
  for (let i = 0; i < n; i++) {
    let v = `${lastOf(path)}-${(seed >>> 0).toString(16).padStart(8, "0").slice(0, 6)}${i === 0 ? "" : `-${i + 1}`}`;
    if (v.length < min) v = v.padEnd(min, "0");
    if (v.length > max) v = v.slice(0, max);
    values.push(v);
  }
  return { values: [...new Set(values)] };
}

function dates(limits: Limits | undefined, local: string, seed: number, n: number): Value {
  const time = local === "dateTime" ? "T09:00:00Z" : "";
  if (limits?.minExclusive !== undefined || limits?.maxExclusive !== undefined) return { reason: "an exclusive bound on a date is for the author to satisfy" };
  const values: string[] = [];
  for (let i = 0; i < n; i++) {
    const month = String(1 + (seed % 12)).padStart(2, "0");
    const day = String(1 + ((seed >>> 4) + i) % 28).padStart(2, "0");
    let v = `2026-${month}-${day}${time}`;
    if (i === 0 && limits?.minInclusive !== undefined && v < limits.minInclusive) v = limits.minInclusive;
    if (i === 0 && limits?.maxInclusive !== undefined && v > limits.maxInclusive) v = limits.maxInclusive;
    values.push(v);
  }
  const within = values.filter((v) => (limits?.minInclusive === undefined || v >= limits.minInclusive) && (limits?.maxInclusive === undefined || v <= limits.maxInclusive));
  return within.length > 0 ? { values: [...new Set(within)] } : { reason: "no date satisfies the bounds the shape states" };
}

/** The values of a literal field, as many as `n`, or fewer where the shape leaves room for fewer, or a reason the generator gives none. */
function literalValues(f: FieldSpec, nodePath: string, n: number): Value {
  const limits = f.limits;
  const seed = hashOf(`${f.path}\u0000${nodePath}`);
  if (limits?.hasValue !== undefined) return { values: [limits.hasValue] };
  if (limits?.in) {
    const list = [...new Set(limits.in)].sort();
    return { values: Array.from({ length: Math.min(n, list.length) }, (_, i) => list[(seed + i) % list.length]) };
  }
  if (limits?.pattern !== undefined) {
    const text = literalPattern(limits.pattern);
    return text === undefined ? { reason: "its sh:pattern is a regular expression, and a value for it is given by hand" } : { values: [text] };
  }
  if (f.datatype === undefined) return limits?.nodeKind === SH_LITERAL ? strings(limits, f.path, seed, n) : { reason: "the shape states no datatype, and the value could be a literal or a reference" };
  if (!f.datatype.startsWith(XSD)) return { reason: `the generator has no value for the datatype ${f.datatype}` };
  const local = f.datatype.slice(XSD.length);
  if (local === "string" || local === "normalizedString" || local === "token") return strings(limits, f.path, seed, n);
  if (local in INTEGERS || DECIMALS.has(local)) return numbers(limits, local, seed, n);
  if (local === "boolean") return { values: [...new Set(Array.from({ length: n }, (_, i) => ((seed + i) % 2 === 0 ? "true" : "false")))] };
  if (local === "date" || local === "dateTime") return dates(limits, local, seed, n);
  if (local === "anyURI") return { values: Array.from({ length: n }, (_, i) => `urn:example:${lastOf(f.path)}-${(seed >>> 0).toString(16).padStart(8, "0").slice(0, 6)}${i === 0 ? "" : `-${i + 1}`}`) };
  return { reason: `the generator has no value for the datatype ${local}` };
}

/** The IRIs of a reference field, from its `sh:in`, its `sh:hasValue`, or the nodes of its class in the world. */
function referenceValues(f: FieldSpec, n: number, instances: Instances, exclude: ReadonlySet<string>): Value {
  const limits = f.limits;
  if (limits?.hasValue !== undefined) return { values: [limits.hasValue] };
  if (limits?.in) return { values: [...new Set(limits.in)].sort().slice(0, n) };
  if (f.cls === undefined) return { reason: "the shape names no class to take a reference from" };
  const found = instances(f.cls).filter((x) => !exclude.has(x));
  if (found.length >= n) return { values: found.slice(0, n) };
  return { values: found, reason: `the sample world holds ${found.length === 0 ? "no" : `only ${found.length}`} ${words(lastOf(f.cls))}` };
}

// --- the walk ---------------------------------------------------------------------------------------------------------------------

interface Context {
  instances: Instances;
  exclude: ReadonlySet<string>;
  left: string[];
}

/** How many a property shape asks for, capped, with the reason when it asks for what no number satisfies or for more than the cap. */
function wanted(limits: { minCount?: number; maxCount?: number } | undefined): { n: number; reason?: string } {
  const min = limits?.minCount ?? 0;
  if (limits?.maxCount !== undefined && limits.maxCount < min) return { n: 0, reason: `it asks for at least ${min} and at most ${limits.maxCount}` };
  return min > MOST_PER_PROPERTY ? { n: MOST_PER_PROPERTY, reason: `it asks for ${min}, and a generated object holds at most ${MOST_PER_PROPERTY}` } : { n: min };
}

function fieldText(f: FieldSpec, label: string, nodePath: string, ctx: Context): string | undefined {
  const { n, reason: asked } = wanted(f.limits);
  if (asked !== undefined && n === 0) {
    ctx.left.push(`The ${f.label} of ${label} is left for you, ${asked}.`);
    return undefined;
  }
  if (n === 0) return undefined;
  const made = f.kind === "iri" ? referenceValues(f, n, ctx.instances, ctx.exclude) : literalValues(f, nodePath, n);
  const values = "values" in made ? made.values : [];
  const reason = "reason" in made ? made.reason : values.length < n ? `the shape leaves room for ${values.length}` : asked;
  if (values.length < n || asked !== undefined) {
    const why = reason ?? "";
    ctx.left.push(values.length === 0 ? `The ${f.label} of ${label} is left for you, ${why}.` : `The ${f.label} of ${label} has ${values.length} of the ${f.limits?.minCount ?? n} values the shape asks for, and the rest is left for you, ${why}.`);
  }
  return values.length > 0 ? values.join("\n") : undefined;
}

function walk(spec: { fields: readonly FieldSpec[]; owned: readonly OwnedSpec[] }, id: string, label: string, nodePath: string, ctx: Context): { fields: Record<string, string>; owned: Record<string, OwnedValues[]> } {
  const fields: Record<string, string> = {};
  for (const f of spec.fields) {
    const text = fieldText(f, label, nodePath, ctx);
    if (text !== undefined) fields[f.path] = text;
  }
  const owned: Record<string, OwnedValues[]> = {};
  for (const o of spec.owned) {
    const { n, reason } = wanted(o.limits);
    if (reason !== undefined) ctx.left.push(`The ${o.label} of ${label} has ${n} ${o.member}${n === 1 ? "" : "s"}, ${reason}.`);
    const members: OwnedValues[] = [];
    for (let i = 0; i < n; i++) {
      const memberId = newMemberId(id, o, members);
      const memberLabel = n === 1 ? `the ${o.member} of ${label}` : `${o.member} ${i + 1} of ${label}`;
      const inner = walk(o, memberId, memberLabel, `${nodePath}/${o.property}#${i + 1}`, ctx);
      members.push({ id: memberId, fields: inner.fields, owned: inner.owned });
    }
    if (members.length > 0) owned[o.property] = members;
  }
  return { fields, owned };
}

/** The small object a boundary shape gives for `root`, and what it requires that was left for the author. */
export function generateObject(spec: FormSpec, root: string, instances: Instances): Generated {
  const ctx: Context = { instances, exclude: new Set([root]), left: [] };
  const made = walk(spec, root, `the ${words(lastOf(spec.rootClass))}`, "", ctx);
  return { form: { fields: made.fields, owned: made.owned }, left: ctx.left };
}
