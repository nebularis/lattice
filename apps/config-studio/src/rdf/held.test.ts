// SPDX-License-Identifier: MPL-2.0

import { Graph } from "@lattice/authoring-domain";
import { describe, expect, it } from "vitest";
import { heldByIri, heldView, missingImports, ontologyList, shortIri, shortLabel, type HeldImport } from "./held";
import { resolveImports } from "./imports";

const P = "@prefix owl: <http://www.w3.org/2002/07/owl#> . @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n";
const A = "https://example.org/ont/a";
const B = "https://example.org/ont/b";
const C = "https://example.org/ont/c";
const BASE = "https://example.org/ont/base";

const baseline = (imports: string[]) =>
  Graph.parse(`${P}<${BASE}> a owl:Ontology${imports.length ? ` ; owl:imports ${imports.map((i) => `<${i}>`).join(", ")}` : ""} .\n<${BASE}#X> a owl:Class .\n`);

const heldA: HeldImport = { digest: "d-a", label: "a", ontology: A, version: `${A}/1.0`, graph: Graph.parse(`${P}<${A}> a owl:Ontology ; owl:versionIRI <${A}/1.0> .`) };

describe("heldByIri", () => {
  it("finds a held import by its ontology IRI and by its version IRI", () => {
    const map = heldByIri([heldA]);
    expect(map.get(A)).toBe("d-a");
    expect(map.get(`${A}/1.0`)).toBe("d-a");
  });

  it("gives no IRI for a held import that declares nothing", () => {
    expect(heldByIri([{ digest: "d-x", label: "x" }]).size).toBe(0);
  });

  it("feeds resolveImports, which then reports the import as held and not missing", () => {
    const plan = resolveImports({ roots: ["base.ttl"], files: [{ path: "base.ttl", text: baseline([A, `${A}/1.0`, B]).toTurtle() }], catalog: new Map(), held: heldByIri([heldA]), staged: [] });
    expect(plan.nodes.filter((n) => !plan.roots.includes(n.iri)).map((n) => [n.iri, n.status])).toEqual([[A, "held"], [`${A}/1.0`, "held"], [B, "missing"]]);
  });
});

describe("missingImports", () => {
  it("reports an import that no held import declares, and none that one does", () => {
    expect(missingImports(baseline([A, B]), [heldA])).toEqual([{ iri: B, importedBy: [BASE] }]);
  });

  it("reports an import of a held import that is missing, naming the held ontology", () => {
    const withImport: HeldImport = { ...heldA, graph: Graph.parse(`${P}<${A}> a owl:Ontology ; owl:imports <${C}> .`) };
    expect(missingImports(baseline([A]), [withImport])).toEqual([{ iri: C, importedBy: [A] }]);
  });

  it("gathers every importer of one missing import, sorted", () => {
    const withImport: HeldImport = { ...heldA, graph: Graph.parse(`${P}<${A}> a owl:Ontology ; owl:imports <${C}> .`) };
    expect(missingImports(baseline([A, C]), [withImport])).toEqual([{ iri: C, importedBy: [A, BASE] }]);
  });

  it("reads no import of a held import whose graph is not loaded", () => {
    expect(missingImports(baseline([A]), [{ ...heldA, graph: undefined }])).toEqual([]);
  });

  it("names a held import that declares no ontology by its label", () => {
    const anonymous: HeldImport = { digest: "d-z", label: "z.ttl", graph: Graph.parse(`${P}<${A}#t> a owl:Class .`) };
    expect(missingImports(baseline([]), [anonymous])).toEqual([]);
  });

  it("states nothing for a baseline with no owl:Ontology", () => {
    const bare = Graph.parse(`${P}<${BASE}#X> a owl:Class .`);
    expect(missingImports(bare, [])).toEqual([]);
  });

  it("does not count the baseline's own IRI as missing", () => {
    expect(missingImports(baseline([BASE]), [])).toEqual([]);
  });
});

describe("ontologyList", () => {
  it("lists the workspace's own ontology, then held imports by label, then missing imports by IRI", () => {
    const list = ontologyList(baseline([A, C, B]), [heldA, { digest: "d-0", label: "0 first", ontology: "https://example.org/ont/zero" }]);
    expect(list.map((e) => (e.kind === "own" ? `own ${e.ontology}` : e.kind === "held" ? `held ${e.label}` : `missing ${e.iri}`))).toEqual([
      `own ${BASE}`,
      "held 0 first",
      "held a",
      `missing ${B}`,
      `missing ${C}`,
    ]);
  });

  it("says nothing about an ontology when the baseline declares none", () => {
    expect(ontologyList(Graph.parse(`${P}<${BASE}#X> a owl:Class .`), [])).toEqual([{ kind: "own", ontology: undefined, version: undefined }]);
  });

  it("carries the version IRI of the baseline", () => {
    const g = Graph.parse(`${P}<${BASE}> a owl:Ontology ; owl:versionIRI <${BASE}/2> .`);
    expect(ontologyList(g, [])[0]).toEqual({ kind: "own", ontology: BASE, version: `${BASE}/2` });
  });
});

describe("determinism", () => {
  it("gives the same view for held imports and baseline statements in any order", () => {
    const others: HeldImport[] = [
      { digest: "d-b", label: "b", ontology: B, graph: Graph.parse(`${P}<${B}> a owl:Ontology ; owl:imports <${C}> .`) },
      heldA,
      { digest: "d-q", label: "q", ontology: "https://example.org/ont/q" },
    ];
    const reference = JSON.stringify([...heldView(baseline([A, B, C]), others).heldByIri], null, 1) + JSON.stringify(heldView(baseline([A, B, C]), others).ontologyList);
    for (const order of [[0, 1, 2], [2, 1, 0], [1, 2, 0], [2, 0, 1]]) {
      const shuffled = order.map((i) => others[i]);
      const view = heldView(baseline([C, B, A]), shuffled);
      expect(JSON.stringify([...view.heldByIri], null, 1) + JSON.stringify(view.ontologyList)).toBe(reference);
    }
  });
});

describe("shortening", () => {
  it("cuts a long IRI in the middle and leaves a short one whole", () => {
    expect(shortIri("https://example.org/ont/a")).toBe("example.org/ont/a");
    const long = `https://example.org/${"x".repeat(80)}/end`;
    const short = shortIri(long);
    expect(short.length).toBe(44);
    expect(short).toContain("…");
    expect(short.endsWith("/end")).toBe(true);
  });

  it("cuts a label to 200 characters", () => {
    expect(shortLabel("a".repeat(500)).length).toBe(200);
    expect(shortLabel("short")).toBe("short");
  });
});
