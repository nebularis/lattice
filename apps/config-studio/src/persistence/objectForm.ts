// SPDX-License-Identifier: MPL-2.0
// The object the persistence simulator writes (SVA-P4, SVA-Q12). A form is derived from the aggregate's boundary shape, the node shape the compiled
// profile's payload contract names, and an object can be given instead as Turtle. Both give the object as lines of N-Triples, with the root and
// each owned member typed by the class their shape targets. A boundary shape that is not in the baseline has no form, and the author gives Turtle.
// Generating an object from the shape is SVA-P5, in objectGenerate.ts, which reads the limits each field and owned member carries here.

import { Graph, RDF, SH, namedNode, literal, type Term } from "@lattice/authoring-domain";
import { shapeTargets } from "../rdf/shapes";
import { ntLine, ntTerm, sortedLines } from "./simulator";

/** What the property shape states of the values of a field, as written, for the form to hold and the generator to keep within. */
export interface Limits {
  minCount?: number;
  maxCount?: number;
  nodeKind?: string;
  /** sh:in, where every listed value is an IRI for a reference or a literal for a literal field. */
  in?: string[];
  minInclusive?: string;
  maxInclusive?: string;
  minExclusive?: string;
  maxExclusive?: string;
  minLength?: number;
  maxLength?: number;
  pattern?: string;
  hasValue?: string;
}

export interface FieldSpec {
  path: string;
  label: string;
  /** An IRI is a reference, one to a line. A literal is typed by `datatype` where the shape states one. */
  kind: "iri" | "literal";
  datatype?: string;
  /** The class a reference is of, where the shape states one. */
  cls?: string;
  limits?: Limits;
}

export interface OwnedSpec {
  property: string;
  label: string;
  /** What a member is called, its class's name in words, for the buttons that add and remove one. */
  member: string;
  cls: string;
  /** How many members the property shape asks for, `sh:minCount` and `sh:maxCount`. */
  limits?: Pick<Limits, "minCount" | "maxCount">;
  fields: FieldSpec[];
  owned: OwnedSpec[];
}

export interface FormSpec {
  rootClass: string;
  fields: FieldSpec[];
  owned: OwnedSpec[];
}

export interface OwnedValues {
  id: string;
  fields: Record<string, string>;
  owned: Record<string, OwnedValues[]>;
}

export interface FormValues {
  fields: Record<string, string>;
  owned: Record<string, OwnedValues[]>;
}

export const EMPTY_FORM: FormValues = { fields: {}, owned: {} };

const lastOf = (iri: string) => iri.slice(Math.max(iri.lastIndexOf("#"), iri.lastIndexOf("/")) + 1);
const words = (name: string) => name.replace(/([a-z0-9])([A-Z])/g, "$1 $2").replace(/[-_]+/g, " ").toLowerCase();

const count = (g: Graph, ps: Term, predicate: string): number | undefined => {
  const text = g.value(ps, predicate);
  const n = Number(text);
  return text !== undefined && Number.isInteger(n) && n >= 0 ? n : undefined;
};

const countLimits = (g: Graph, ps: Term): Pick<Limits, "minCount" | "maxCount"> => {
  const minCount = count(g, ps, SH("minCount"));
  const maxCount = count(g, ps, SH("maxCount"));
  return { ...(minCount === undefined ? {} : { minCount }), ...(maxCount === undefined ? {} : { maxCount }) };
};

function limitsOf(g: Graph, ps: Term, reference: boolean): Limits | undefined {
  const limits: Limits = countLimits(g, ps);
  const nodeKind = g.value(ps, SH("nodeKind"));
  if (nodeKind !== undefined) limits.nodeKind = nodeKind;
  const list = g.object(ps, SH("in"));
  const members = list ? g.list(list) : undefined;
  if (members && members.length > 0 && members.every((t) => (reference ? t.termType === "NamedNode" : t.termType === "Literal"))) limits.in = members.map((t) => t.value);
  for (const name of ["minInclusive", "maxInclusive", "minExclusive", "maxExclusive", "pattern", "hasValue"] as const) {
    const v = g.value(ps, SH(name));
    if (v !== undefined) limits[name] = v;
  }
  for (const name of ["minLength", "maxLength"] as const) {
    const n = count(g, ps, SH(name));
    if (n !== undefined) limits[name] = n;
  }
  return Object.keys(limits).length > 0 ? limits : undefined;
}

function fieldOf(g: Graph, ps: Term, path: string): FieldSpec {
  const datatype = g.value(ps, SH("datatype"));
  const cls = g.objects(ps, SH("class")).find((c) => c.termType === "NamedNode")?.value;
  const nodeKind = g.value(ps, SH("nodeKind"));
  const reference = cls !== undefined || nodeKind === SH("IRI");
  const kind = reference && datatype === undefined ? "iri" : "literal";
  const limits = limitsOf(g, ps, kind === "iri");
  return { path, label: words(lastOf(path)), kind, ...(datatype === undefined ? {} : { datatype }), ...(cls === undefined ? {} : { cls }), ...(limits ? { limits } : {}) };
}

/** The form a node shape gives, its properties with a plain path in the order of their IRIs, a property that points at a node shape being an owned member. */
function specOf(g: Graph, shape: Term, seen: Set<string>): { fields: FieldSpec[]; owned: OwnedSpec[] } {
  const fields: FieldSpec[] = [];
  const owned: OwnedSpec[] = [];
  const properties = g.objects(shape, SH("property")).map((ps) => ({ ps, path: g.object(ps, SH("path")) })).filter((e): e is { ps: Term; path: Term } => e.path?.termType === "NamedNode");
  properties.sort((a, b) => (a.path.value < b.path.value ? -1 : a.path.value > b.path.value ? 1 : 0));
  for (const { ps, path } of properties) {
    const node = g.objects(ps, SH("node"))[0];
    if (node && !seen.has(node.value)) {
      const cls = shapeTargets(g, node)[0];
      if (cls !== undefined) {
        const limits = countLimits(g, ps);
        owned.push({ property: path.value, label: words(lastOf(path.value)), member: words(lastOf(cls)), cls, ...(Object.keys(limits).length > 0 ? { limits } : {}), ...specOf(g, node, new Set([...seen, node.value])) });
        continue;
      }
    }
    fields.push(fieldOf(g, ps, path.value));
  }
  return { fields, owned };
}

/** The form for the boundary shape `shape` of the baseline `graph`, or undefined when the baseline holds no such shape. */
export function formSpec(graph: Graph, shape: string | null, rootClass: string): FormSpec | undefined {
  if (shape === null || !graph.has(shape)) return undefined;
  return { rootClass, ...specOf(graph, namedNode(shape), new Set([shape])) };
}

// --- from values to lines ------------------------------------------------------------------------------------------------------

const IRI = /^[A-Za-z][A-Za-z0-9+.\-]*:[^\s<>"{}|\\^`]*$/;

const linesOf = (text: string | undefined): string[] => (text ?? "").split("\n").map((l) => l.trim()).filter((l) => l !== "");

export type Triples = { lines: string[] } | { problem: string };

function fieldLines(subject: string, field: FieldSpec, text: string | undefined, out: string[]): string | undefined {
  for (const value of linesOf(text)) {
    if (field.kind === "iri") {
      if (!IRI.test(value)) return `${field.label} holds ${JSON.stringify(value)}, which is not an IRI. Give one IRI to a line.`;
      out.push(ntLine(subject, field.path, `<${value}>`));
    } else out.push(ntLine(subject, field.path, ntTerm(literal(value, field.datatype ? namedNode(field.datatype) : undefined))));
  }
  return undefined;
}

function ownedLines(subject: string, specs: readonly OwnedSpec[], values: Record<string, OwnedValues[]>, out: string[]): string | undefined {
  for (const spec of specs) {
    for (const member of values[spec.property] ?? []) {
      if (!IRI.test(member.id)) return `The ${spec.member} has the identifier ${JSON.stringify(member.id)}, which is not an IRI.`;
      out.push(ntLine(subject, spec.property, `<${member.id}>`), ntLine(member.id, RDF("type"), `<${spec.cls}>`));
      for (const f of spec.fields) {
        const problem = fieldLines(member.id, f, member.fields[f.path], out);
        if (problem) return problem;
      }
      const problem = ownedLines(member.id, spec.owned, member.owned, out);
      if (problem) return problem;
    }
  }
  return undefined;
}

/** The object a form gives for `root`, as sorted lines of N-Triples. */
export function formTriples(spec: FormSpec, values: FormValues, root: string): Triples {
  const out: string[] = [ntLine(root, RDF("type"), `<${spec.rootClass}>`)];
  for (const f of spec.fields) {
    const problem = fieldLines(root, f, values.fields[f.path], out);
    if (problem) return { problem };
  }
  const problem = ownedLines(root, spec.owned, values.owned, out);
  return problem ? { problem } : { lines: sortedLines(out) };
}

/** The object a text of Turtle gives, as sorted lines of N-Triples. A blank node is refused, since a payload holds none. */
export function turtleTriples(text: string, root: string): Triples {
  if (text.trim() === "") return { problem: "The Turtle is empty." };
  let g: Graph;
  try {
    g = Graph.parse(text);
  } catch (e) {
    return { problem: `The Turtle does not parse. ${e instanceof Error ? e.message : String(e)}` };
  }
  const lines: string[] = [];
  for (const q of g.quads()) {
    if (q.subject.termType === "BlankNode" || q.object.termType === "BlankNode") return { problem: "The Turtle holds a blank node, and a payload holds none. Give each node an IRI." };
    lines.push(`${ntTerm(q.subject)} ${ntTerm(q.predicate)} ${ntTerm(q.object)} .`);
  }
  if (!lines.some((l) => l.startsWith(`<${root}> `))) return { problem: "The Turtle says nothing of the root." };
  return { lines: sortedLines(lines) };
}

// --- from lines to values ------------------------------------------------------------------------------------------------------

/** The text of a field's values in `g` for `subject`, one to a line in the order of their text. */
function textOf(g: Graph, subject: string, field: FieldSpec): string {
  return g
    .objects(subject, field.path)
    .map((o) => o.value)
    .sort()
    .join("\n");
}

function ownedValuesOf(g: Graph, subject: string, specs: readonly OwnedSpec[]): Record<string, OwnedValues[]> {
  const out: Record<string, OwnedValues[]> = {};
  for (const spec of specs) {
    const members = g.objects(subject, spec.property).filter((o) => o.termType === "NamedNode").map((o) => o.value).sort();
    if (members.length > 0) {
      out[spec.property] = members.map((id) => ({
        id,
        fields: Object.fromEntries(spec.fields.map((f) => [f.path, textOf(g, id, f)])),
        owned: ownedValuesOf(g, id, spec.owned),
      }));
    }
  }
  return out;
}

/** The form's values for the aggregate that `lines` hold for `root`, so that a replace starts from what the world stores. */
export function formValues(spec: FormSpec, lines: readonly string[], root: string): FormValues {
  const g = Graph.parse(lines.join("\n"));
  return { fields: Object.fromEntries(spec.fields.map((f) => [f.path, textOf(g, root, f)])), owned: ownedValuesOf(g, root, spec.owned) };
}

/** The identifier a new owned member gets, the parent's followed by what the member is and a number that no sibling has. */
export function newMemberId(parent: string, spec: OwnedSpec, siblings: readonly OwnedValues[]): string {
  const taken = new Set(siblings.map((s) => s.id));
  for (let n = 1; ; n++) {
    const id = `${parent}-${words(lastOf(spec.cls)).replace(/\s+/g, "-")}-${n}`;
    if (!taken.has(id)) return id;
  }
}
