// SPDX-License-Identifier: MPL-2.0

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { Graph } from "@lattice/authoring-domain";
import type { HeldImport } from "./held";
import { importCounts, importGraph, importSummary, type ImportGraph } from "./importGraph";
import { split } from "./split";

const P = [
  "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
  "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
  "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
  "@prefix voc: <https://www.nebularis.org/neuro-semantic/lattice/vocabulary#> .",
  "@prefix ex: <https://example.org/ont/own#> .",
  "",
].join("\n");
const BASE = "https://example.org/ont/base";
const A = "https://example.org/ont/a";
const B = "https://example.org/ont/b";
const C = "https://example.org/ont/c";
const GONE = "https://example.org/ont/gone";

const g = (ttl: string) => Graph.parse(`${P}${ttl}\n`);
const held = (digest: string, iri: string, ttl: string, version?: string): HeldImport => ({
  digest,
  label: iri,
  ontology: iri,
  version,
  graph: g(`<${iri}> a owl:Ontology ${version ? `; owl:versionIRI <${version}> ` : ""}.\n${ttl}`),
});
const baseline = (head: string, body = "") => g(`<${BASE}> a owl:Ontology ${head} .\n${body}`);
const ids = (v: ImportGraph, kind: string) => v.edges.filter((e) => e.kind === kind).map((e) => `${e.source} > ${e.target}`);
const own = "own";

describe("the nodes", () => {
  it("draws the own ontology alone for a baseline that imports nothing", () => {
    const v = importGraph({ baseline: baseline(""), held: [] });
    expect(v.nodes).toEqual([{ id: own, kind: "own", label: "This workspace", iri: BASE }]);
    expect(v.edges).toEqual([]);
  });

  it("draws a held import and a missing import, and resolves an import by its ontology IRI and by its version IRI", () => {
    const v = importGraph({
      baseline: baseline(`; owl:imports <${A}>, <${B}/1.0>, <${GONE}>`),
      held: [held("da", A, ""), held("db", B, "", `${B}/1.0`)],
    });
    expect(v.nodes.map((n) => `${n.kind} ${n.id}`)).toEqual([`held held:da`, `held held:db`, `missing missing:${GONE}`, `own own`]);
    expect(ids(v, "imports")).toEqual([`own > held:da`, `own > held:db`, `own > missing:${GONE}`]);
  });

  it("follows an import of an import where the held import's graph is loaded, and draws none where it is not", () => {
    const withGraph = importGraph({ baseline: baseline(`; owl:imports <${A}>`), held: [held("da", A, ""), { digest: "db", label: B, ontology: B }, held("dc", C, "")] });
    expect(ids(withGraph, "imports")).toEqual([`own > held:da`]);
    const a = held("da", A, `<${A}> owl:imports <${B}>, <${GONE}> .`);
    const v = importGraph({ baseline: baseline(`; owl:imports <${A}>`), held: [a, { digest: "db", label: B, ontology: B }] });
    expect(ids(v, "imports")).toEqual([`held:da > held:db`, `held:da > missing:${GONE}`, `own > held:da`]);
  });

  it("draws a scheme of the vocabulary part and one of a held import, each with where it is declared", () => {
    const scheme = (iri: string, label: string) => `<${iri}> a skos:ConceptScheme ; skos:prefLabel "${label}" .`;
    const v = importGraph({
      baseline: baseline(`; owl:imports <${A}>`),
      held: [held("da", A, scheme("https://example.org/ont/a#S", "In the import"))],
      vocabulary: g(scheme("https://example.org/ont/own#V", "In the vocabulary") + `\n<https://example.org/ont/own#W> a voc:ConceptScheme .`),
      dependencies: [g(scheme("https://example.org/ont/dep#D", "In a dependency"))],
    });
    const schemes = v.nodes.filter((n) => n.kind === "scheme");
    expect(schemes.map((n) => [n.label, n.declaredIn, n.digest])).toEqual([
      ["In the import", "import", "da"],
      ["In a dependency", "dependency", undefined],
      ["In the vocabulary", "vocabulary", undefined],
      ["W", "vocabulary", undefined],
    ]);
    expect(importCounts(v)).toEqual({ ontologies: 1, held: 1, missing: 0, schemes: 4 });
    expect(importSummary(v)).toBe("1 ontology of the workspace, 1 import held, 0 missing, 4 schemes.");
  });

  it("says the counts of the example in the brief", () => {
    const v = importGraph({ baseline: baseline(`; owl:imports <${A}>, <${B}>, <${GONE}>`), held: [held("da", A, ""), held("db", B, "")], vocabulary: g(`<urn:s1> a skos:ConceptScheme . <urn:s2> a skos:ConceptScheme . <urn:s3> a skos:ConceptScheme .`) });
    expect(importSummary(v)).toBe("1 ontology of the workspace, 2 imports held, 1 missing, 3 schemes.");
  });
});

describe("binds", () => {
  const vocab = `
ex:SectorContract a voc:SchemeContract ; voc:constrainsProperty ex:sector .
ex:RegionContract a voc:SchemeContract ; voc:constrainsProperty ex:region ; voc:boundScheme ex:Continents .
ex:Orphan a voc:SchemeContract ; voc:constrainsProperty ex:undeclared .
ex:b1 a voc:SchemeBinding ; voc:forContract ex:SectorContract ; voc:bindsScheme ex:Sectors .
ex:b2 a voc:SchemeBinding ; voc:forContract ex:RegionContract ; voc:bindsScheme ex:Emea .
ex:b3 a voc:SchemeBinding ; voc:forContract ex:Orphan ; voc:bindsScheme ex:Sectors .
ex:Sectors a skos:ConceptScheme . ex:Emea a skos:ConceptScheme . ex:Continents a skos:ConceptScheme .`;

  it("draws an edge from the ontology that declares the contract's property to each scheme a binding names, labelled with the contract", () => {
    const v = importGraph({ baseline: baseline("", "ex:sector a owl:ObjectProperty . ex:region a owl:ObjectProperty ."), held: [], vocabulary: g(vocab) });
    const binds = v.edges.filter((e) => e.kind === "binds").map((e) => `${e.source} > ${e.target.replace("scheme:https://example.org/ont/own#", "")} ${e.label}`);
    expect(binds).toEqual(["own > Continents ex:RegionContract", "own > Emea ex:RegionContract", "own > Sectors ex:SectorContract"]);
  });

  it("draws it from the held import that declares the property, and none where no loaded graph declares it", () => {
    const v = importGraph({ baseline: baseline(`; owl:imports <${A}>`), held: [held("da", A, "ex:sector a owl:DatatypeProperty .")], vocabulary: g(vocab) });
    expect(v.edges.filter((e) => e.kind === "binds").map((e) => `${e.source} ${e.label}`)).toEqual(["held:da ex:SectorContract"]);
  });
});

describe("uses", () => {
  it("is derived from a predicate and from a type, and never repeats a stated import in either direction", () => {
    const a = held("da", A, "<https://example.org/ont/a#P> a owl:ObjectProperty . <https://example.org/ont/a#K> a owl:Class .");
    const b = held("db", B, "<https://example.org/ont/b#Q> a owl:ObjectProperty . <https://example.org/ont/b#L> a owl:Class .");
    const base = baseline(
      `; owl:imports <${B}>`,
      `<${BASE}#Thing> a owl:Class . <${BASE}#x> a <https://example.org/ont/a#K> ; <https://example.org/ont/a#P> <${BASE}#Thing> ; <https://example.org/ont/b#Q> <${BASE}#Thing> .`,
    );
    const v = importGraph({ baseline: base, held: [a, b] });
    expect(ids(v, "imports")).toEqual(["own > held:db"]);
    expect(ids(v, "uses")).toEqual(["own > held:da"]);
    const back = importGraph({ baseline: baseline(`; owl:imports <${A}>`, `<${BASE}#x> a <https://example.org/ont/b#L> .`), held: [{ ...a, graph: a.graph!.merge(g(`<${A}#K> a <https://example.org/ont/b#L> .`)) }, b] });
    expect(ids(back, "uses")).toEqual(["held:da > held:db", "own > held:db"]);
  });

  it("is derived from subclass, domain and range statements, and never joins a node to itself", () => {
    const a = held("da", A, "<https://example.org/ont/a#K> a owl:Class .");
    const base = baseline("", `<${BASE}#T> a owl:Class ; rdfs:subClassOf <https://example.org/ont/a#K> . <${BASE}#p> a owl:ObjectProperty ; rdfs:domain <${BASE}#T> ; rdfs:range <${BASE}#T> .`);
    const v = importGraph({ baseline: base, held: [a] });
    expect(ids(v, "uses")).toEqual(["own > held:da"]);
    expect(v.edges.filter((e) => e.source === e.target)).toEqual([]);
  });

  it("is drawn to a scheme from a document that names a concept or the scheme, and not where a binding already joins them", () => {
    const vocab = g(`ex:S a skos:ConceptScheme . ex:T a skos:ConceptScheme . ex:c a skos:Concept ; skos:inScheme ex:S . ex:d a skos:Concept ; skos:inScheme ex:T .`);
    const base = baseline("", `ex:thing a owl:Class . ex:p a owl:ObjectProperty . ex:i a ex:thing ; ex:p ex:c ; ex:q ex:T .`);
    const v = importGraph({ baseline: base, held: [], vocabulary: vocab });
    expect(ids(v, "uses").map((s) => s.replace(/https:\/\/example.org\/ont\/own#/g, ""))).toEqual(["own > scheme:S", "own > scheme:T"]);
    const bound = importGraph({
      baseline: base,
      held: [],
      vocabulary: vocab.merge(g(`ex:K a voc:SchemeContract ; voc:constrainsProperty ex:p . ex:bb a voc:SchemeBinding ; voc:forContract ex:K ; voc:bindsScheme ex:S .`)),
    });
    expect(ids(bound, "uses").map((s) => s.replace(/https:\/\/example.org\/ont\/own#/g, ""))).toEqual(["own > scheme:T"]);
    expect(ids(bound, "binds")).toHaveLength(1);
  });
});

describe("the same drawing for any order", () => {
  it("gives equal nodes and edges for shuffled triples and shuffled held imports", () => {
    const a = held("da", A, `<${A}> owl:imports <${GONE}> . <https://example.org/ont/a#K> a owl:Class . ex:sector a owl:DatatypeProperty .`);
    const b = held("db", B, "<https://example.org/ont/b#L> a owl:Class .");
    const body = `<${BASE}#x> a <https://example.org/ont/a#K> , <https://example.org/ont/b#L> .`;
    const vocab = `ex:K a voc:SchemeContract ; voc:constrainsProperty ex:sector . ex:bb a voc:SchemeBinding ; voc:forContract ex:K ; voc:bindsScheme ex:S . ex:S a skos:ConceptScheme .`;
    const shuffled = (graph: Graph, seed: number) => {
      const quads = graph.quads();
      const order = quads.map((_, i) => i).sort((x, y) => ((x * 7919 + seed) % 31) - ((y * 7919 + seed) % 31) || x - y);
      return Graph.of(order.map((i) => quads[i]), graph.prefixes);
    };
    const run = (seed: number, flip: boolean) =>
      importGraph({
        baseline: shuffled(baseline(`; owl:imports <${A}>`, body), seed),
        held: (flip ? [b, a] : [a, b]).map((h) => ({ ...h, graph: shuffled(h.graph!, seed + 1) })),
        vocabulary: shuffled(g(vocab), seed + 2),
      });
    const first = JSON.stringify(run(1, false));
    for (const [seed, flip] of [[2, true], [5, false], [11, true]] as const) expect(JSON.stringify(run(seed, flip))).toBe(first);
    expect(JSON.parse(first).edges.map((e: { kind: string }) => e.kind)).toEqual(["binds", "imports", "imports", "uses"]);
  });
});

describe("the facility sample", () => {
  it("draws its ontology and its six schemes, with five binds edges from the contracts, and no import or uses edge", () => {
    const samples = join(__dirname, "../../../../contracts/config-studio/samples");
    const read = (name: string) => Graph.parse(readFileSync(join(samples, name), "utf-8"));
    const parts = split(read("lending-baseline.ttl").merge(read("facility-baseline.ttl")).merge(read("facility-vocabulary.ttl")));
    const v = importGraph({ baseline: parts.baseline, held: [], vocabulary: parts.vocabulary });
    const ex = "https://example.org/lending#";
    expect(v.nodes.map((n) => `${n.kind} ${n.id.replace(ex, "ex:")} | ${n.label} | ${n.declaredIn ?? n.iri}`)).toEqual([
      "own own | Lending | https://example.org/lending",
      "scheme scheme:ex:OutcomeScheme | Decision outcomes | vocabulary",
      "scheme scheme:ex:RegionAmericas | Countries of the Americas | vocabulary",
      "scheme scheme:ex:RegionContinents | Continents | vocabulary",
      "scheme scheme:ex:RegionEmea | Regions of Europe, the Middle East and Africa | vocabulary",
      "scheme scheme:ex:SectorScheme2026 | Sector classification, 2026 edition | vocabulary",
      "scheme scheme:ex:SectorScheme2027 | Sector classification, 2027 edition | vocabulary",
    ]);
    expect(v.edges.map((e) => `${e.kind} ${e.source} > ${e.target.replace(ex, "ex:")} ${e.label}`)).toEqual([
      "binds own > scheme:ex:RegionAmericas ex:RegionContract",
      "binds own > scheme:ex:RegionContinents ex:RegionContract",
      "binds own > scheme:ex:RegionEmea ex:RegionContract",
      "binds own > scheme:ex:SectorScheme2026 ex:SectorContract",
      "binds own > scheme:ex:SectorScheme2027 ex:SectorContract",
    ]);
  });
});
