// SPDX-License-Identifier: MPL-2.0
// The lowered scheme of each projection contract (SVA-Q62), read from the `projections` group of the latest finished surface compilation. The
// group holds `projections/manifest.json`, one entry for each scheme, and each scheme's compiled form, `mork_rdf`'s account of what it compiled.
// The browser reads the scheme's name, how many mappings the compiled form holds and its review findings from them, and never lowers a contract
// itself. A compiled form holds the mappings by name and the queries compiled from them and not the mappings' own terms. The job also holds the
// lowered scheme itself beside each compiled form, `{scheme}.mork.ttl`, which the manifest names, and the scheme drawn from it has its mappings with
// their terms and the compiled form's review findings on the mappings they concern. A job without that file, such as one compiled before the job
// held it, draws the scheme as the compiled form gives it, the mappings by name as the context paths nest them and no terms.

import { Graph, MORK, localName, type Term } from "@lattice/authoring-domain";
import type { Job } from "../rdf/report";
import { schemesOf, type Scheme, type MappingNode } from "../rdf/mapping";
import { freshness, type Freshness } from "../persistence/landing";
import type { SchemeBox } from "./drawing";

export const MANIFEST = "projections/manifest.json";
export const GROUP = "projections";

/** The findings a projection's compilation asks a reviewer to confirm (ADR-A41). */
export const REVIEW_CODES = ["DerivationReview", "ExpansionReview", "MappingReview"] as const;

export interface CompileFinding {
  code: string;
  severity: string;
  message: string;
  /** The mapping it is about, by its IRI. */
  about?: string;
}

export interface LoweredScheme {
  key: string;
  contract: string;
  kind: string;
  /** The scheme's IRI and its compiled form's path. */
  scheme: string;
  path: string;
  /** The mappings the compiled form names, each with the queries compiled from it. */
  mappings: Map<string, { queries: number; checks: number; parent?: string }>;
  findings: CompileFinding[];
  /** The lowered scheme as the job holds it, with each mapping's terms, where the job holds it and it reads. */
  lowered?: Scheme;
}

export interface Projections {
  schemes: LoweredScheme[];
}

const iri = (t: Term | undefined) => t?.value;

/** The first and rest of an RDF list that is named, as the compiled form's context paths are, or blank. */
function walk(g: Graph, head: Term): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  let node: Term | undefined = head;
  while (node && node.value !== "http://www.w3.org/1999/02/22-rdf-syntax-ns#nil" && !seen.has(node.value)) {
    seen.add(node.value);
    const first = g.object(node, "http://www.w3.org/1999/02/22-rdf-syntax-ns#first");
    if (first) out.push(first.value);
    node = g.object(node, "http://www.w3.org/1999/02/22-rdf-syntax-ns#rest");
  }
  return out;
}

/** What `mork_rdf` records of a scheme it compiled. */
export function readCompiled(text: string): Pick<LoweredScheme, "mappings" | "findings"> {
  const g = Graph.parse(text);
  const mappings = new Map<string, { queries: number; checks: number; parent?: string }>();
  const mapping = (m: string) => mappings.get(m) ?? (mappings.set(m, { queries: 0, checks: 0 }), mappings.get(m)!);
  for (const q of g.quads(null, MORK("confidenceOf"))) mapping(q.object.value);
  for (const q of g.ofType(MORK("CompiledQuery"))) {
    const from = iri(g.object(q, MORK("compiledFrom")));
    if (!from) continue;
    const m = mapping(from);
    if (g.value(q, MORK("queryKind")) === "check") m.checks++;
    else m.queries++;
    // A query's context path runs from the root to the mapping, so each mapping's parent is the one before it.
    const path = g.object(q, MORK("contextPath"));
    if (path) {
      const chain = walk(g, path);
      chain.forEach((n, i) => {
        const entry = mapping(n);
        if (i > 0 && entry.parent === undefined) entry.parent = chain[i - 1];
      });
    }
  }
  const findings: CompileFinding[] = g
    .ofType(MORK("CompileFinding"))
    .map((f) => ({
      index: Number(g.value(f, MORK("findingIndex")) ?? 0),
      finding: {
        code: g.value(f, MORK("findingCode")) ?? "",
        severity: localName(g.value(f, MORK("findingSeverity")) ?? "Info").replace(/Finding$/, ""),
        message: g.value(f, MORK("findingMessage")) ?? "",
        about: g.value(f, MORK("findingAbout")),
      },
    }))
    .sort((a, b) => a.index - b.index)
    .map((f) => f.finding);
  return { mappings, findings };
}

/** The lowered scheme a manifest entry names, or undefined where the job holds no such file or it does not read, which draws the scheme as before. */
function readLowered(job: Job, entry: { scheme: string; mork?: string }): Scheme | undefined {
  const file = entry.mork ? job.artefacts.find((a) => a.path === entry.mork && a.group === GROUP) : undefined;
  if (!file) return undefined;
  try {
    return schemesOf(Graph.parse(file.content)).find((s) => s.iri === entry.scheme);
  } catch {
    return undefined;
  }
}

/** The projections a finished surface compilation holds, or undefined where it holds none, as a configuration with no projection does not. */
export function readProjections(job: Job): Projections | undefined {
  const manifest = job.artefacts.find((a) => a.path === MANIFEST && a.group === GROUP);
  if (!manifest) return undefined;
  let entries: { key: string; contract: string; kind: string; scheme: string; path: string; mork?: string }[];
  try {
    entries = JSON.parse(manifest.content) as typeof entries;
  } catch {
    return undefined;
  }
  const schemes: LoweredScheme[] = [];
  for (const e of entries) {
    const file = job.artefacts.find((a) => a.path === e.path && a.group === GROUP);
    if (!file) continue;
    try {
      schemes.push({ key: e.key, contract: e.contract, kind: e.kind, scheme: e.scheme, path: e.path, ...readCompiled(file.content), lowered: readLowered(job, e) });
    } catch {
      // A compiled form that cannot be read is left out, and its contract says it has no scheme.
    }
  }
  return { schemes };
}

/** What the compiled form says of a mapping: the queries and checks compiled from it, and the review findings about it. */
function compiledNote(s: LoweredScheme, mapping: string): string[] {
  const v = s.mappings.get(mapping);
  const about = s.findings.filter((f) => f.about === mapping && REVIEW_CODES.includes(f.code as never));
  return [v?.queries ? `${v.queries} ${v.queries === 1 ? "query" : "queries"}` : "", v?.checks ? `${v.checks} ${v.checks === 1 ? "check" : "checks"}` : "", ...about.map((f) => f.code)].filter(Boolean);
}

/**
 * The scheme as the mapping canvas draws one. Where the job holds the lowered scheme, it is that scheme in full, each mapping with the terms it writes
 * and under it what compiled from it and the review findings on it (`annotate`). Where it does not, it is what the compiled form holds: each mapping
 * by the name the lowering gave it, how they nest and what each compiled to (`describe`), with no terms.
 */
export function schemeOf(s: LoweredScheme): { scheme: Scheme; describe?: (mapping: string) => string; annotate?: (mapping: string) => string } {
  const prefix = `scheme_${s.key}_`;
  const label = (m: string) => {
    const name = localName(m);
    return name.startsWith(prefix) ? name.slice(prefix.length) : name;
  };
  if (s.lowered) {
    const named = <T extends { label: string; iri: string }>(n: T): T => ({ ...n, label: n.label === localName(n.iri) ? label(n.iri) : n.label });
    const scheme: Scheme = { ...s.lowered, label: localName(s.scheme), mappings: s.lowered.mappings.map(named), sources: s.lowered.sources.map(named) };
    return { scheme, annotate: (m) => compiledNote(s, m).join(", ") };
  }
  const children = new Map<string, string[]>();
  for (const [m, v] of s.mappings) if (v.parent) children.set(v.parent, [...(children.get(v.parent) ?? []), m]);
  const ordered: MappingNode[] = [];
  const visit = (m: string, depth: number) => {
    ordered.push({
      iri: m, label: label(m), kind: depth === 0 ? "Datum" : "DataMapping", parent: s.mappings.get(m)?.parent,
      targets: { tbox: [], rbox: [], inverse: [], abox: [] }, isTemplate: false, depth, row: ordered.length,
    });
    for (const c of (children.get(m) ?? []).sort()) visit(c, depth + 1);
  };
  const roots = [...s.mappings.keys()].filter((m) => !s.mappings.get(m)!.parent).sort();
  roots.forEach((r) => visit(r, 0));
  const describe = (m: string) => compiledNote(s, m).join(", ") || "nothing compiled from it";
  return { scheme: { iri: s.scheme, label: localName(s.scheme), labelled: true, mappings: ordered, sources: [] }, describe };
}

/** The review findings of a scheme by their codes, each with how many. */
export function reviewCounts(s: LoweredScheme): [string, number][] {
  const counts = new Map<string, number>();
  for (const f of s.findings) if ((REVIEW_CODES as readonly string[]).includes(f.code)) counts.set(f.code, (counts.get(f.code) ?? 0) + 1);
  return [...counts].sort((a, b) => a[0].localeCompare(b[0]));
}

/** What a compilation was sent against and what the workspace holds now: the surface part and the baseline, as the persistence canvas marks its picture. */
export function staleMark(compiled: string | undefined, now: string): Freshness {
  return freshness(compiled, now);
}

/** The box of each projection's lowered scheme, for a compilation, or for none. */
export function boxesFor(projections: Projections | "none" | "refused", freshness: Freshness): (contract: string) => SchemeBox | undefined {
  const stale = freshness === "out-of-date";
  return (contract) => {
    if (projections === "none") return { contract, title: "Lowered scheme", lines: ["no compilation yet"], state: "none", stale: false };
    if (projections === "refused") return { contract, title: "Lowered scheme", lines: ["the latest compilation was refused"], state: "none", stale: false };
    const found = projections.schemes.find((s) => s.contract === contract);
    if (!found) return { contract, title: "Lowered scheme", lines: ["not in the latest compilation"], state: "absent", stale };
    const reviews = reviewCounts(found);
    const count = found.lowered?.mappings.length ?? found.mappings.size;
    return {
      contract, title: localName(found.scheme), state: "ready", stale,
      lines: [`${count} ${count === 1 ? "mapping" : "mappings"}`, ...(reviews.length ? reviews.map(([code, n]) => `${code} × ${n}`) : ["no review findings"])],
    };
  };
}
