// @vitest-environment jsdom
// SPDX-License-Identifier: MPL-2.0
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { buildCatalogLookup } from "./catalog";
import { HeaderError, ontologyHeader, resolveImports } from "./imports";
import type { DroppedFile, ResolveInput } from "./imports";

const EX = "https://example.org/";

const ttl = (iri: string, imports: string[] = [], version?: string) =>
  `@prefix owl: <http://www.w3.org/2002/07/owl#> .\n<${iri}> a owl:Ontology ;\n` +
  (version ? `  owl:versionIRI <${version}> ;\n` : "") +
  (imports.length ? `  owl:imports ${imports.map((i) => `<${i}>`).join(", ")} ;\n` : "") +
  `  .\n`;

describe("ontologyHeader", () => {
  it("reads a Turtle header with a version IRI and imports", () => {
    expect(ontologyHeader(ttl(`${EX}a`, [`${EX}b`, `${EX}c`], `${EX}a/1.0`), "text/turtle")).toEqual({
      ontologyIri: `${EX}a`,
      versionIri: `${EX}a/1.0`,
      imports: [`${EX}b`, `${EX}c`],
    });
  });

  it("reads an RDF/XML header from rdf:about", () => {
    const xml = `<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:owl="http://www.w3.org/2002/07/owl#" xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#">
  <owl:Ontology rdf:about="${EX}x">
    <owl:versionIRI rdf:resource="${EX}x/2"/>
    <owl:imports rdf:resource="${EX}y"/>
    <owl:imports rdf:resource="${EX}z"/>
  </owl:Ontology>
  <owl:Class rdf:about="${EX}x#C"><rdfs:label>not read</rdfs:label></owl:Class>
</rdf:RDF>`;
    expect(ontologyHeader(xml, "application/rdf+xml")).toEqual({ ontologyIri: `${EX}x`, versionIri: `${EX}x/2`, imports: [`${EX}y`, `${EX}z`] });
  });

  it("resolves an empty or relative rdf:about and a relative import against xml:base", () => {
    const xml = (about: string) => `<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:owl="http://www.w3.org/2002/07/owl#" xml:base="${EX}base/">
  <owl:Ontology rdf:about="${about}"><owl:imports rdf:resource="../other"/></owl:Ontology></rdf:RDF>`;
    expect(ontologyHeader(xml(""), "application/rdf+xml")).toEqual({ ontologyIri: `${EX}base/`, imports: [`${EX}other`] });
    expect(ontologyHeader(xml("ont"), "application/rdf+xml").ontologyIri).toBe(`${EX}base/ont`);
  });

  it("gives no IRI and no imports for a document with no ontology", () => {
    expect(ontologyHeader("@prefix ex: <https://example.org/> . ex:a ex:p ex:b .", "text/turtle")).toEqual({ imports: [] });
    expect(
      ontologyHeader('<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"/>', "application/rdf+xml"),
    ).toEqual({ imports: [] });
  });

  it("throws HeaderError for text that does not parse", () => {
    expect(() => ontologyHeader("<a> <b> .", "text/turtle")).toThrow(HeaderError);
    expect(() => ontologyHeader("<rdf:RDF", "application/rdf+xml")).toThrow(HeaderError);
  });
});

const file = (path: string, text: string): DroppedFile => ({ path, text });
const input = (over: Partial<ResolveInput>): ResolveInput => ({
  roots: [],
  files: [],
  catalog: new Map(),
  held: new Map(),
  staged: new Set(),
  ...over,
});
const statuses = (plan: ReturnType<typeof resolveImports>) => Object.fromEntries(plan.nodes.map((n) => [n.iri, n.status]));

describe("resolveImports", () => {
  it("resolves each of the four ways, and reports the rest missing", () => {
    const plan = resolveImports(
      input({
        roots: ["root.ttl"],
        files: [file("root.ttl", ttl(`${EX}root`, [`${EX}cat`, `${EX}file`, `${EX}held`, `${EX}staged`, `${EX}none`])), file("c/cat.ttl", ttl(`${EX}cat`)), file("f/file.ttl", ttl(`${EX}file/ont`, [], `${EX}file`))],
        catalog: new Map([[`${EX}cat`, "c/cat.ttl"]]),
        held: new Map([[`${EX}held`, "sha256:abc"]]),
        staged: new Set([`${EX}staged`]),
      }),
    );
    expect(statuses(plan)).toEqual({
      [`${EX}root`]: "file",
      [`${EX}cat`]: "catalog",
      [`${EX}file`]: "file",
      [`${EX}held`]: "held",
      [`${EX}staged`]: "staged",
      [`${EX}none`]: "missing",
    });
    const byIri = new Map(plan.nodes.map((n) => [n.iri, n]));
    expect(byIri.get(`${EX}held`)?.digest).toBe("sha256:abc");
    expect(byIri.get(`${EX}file`)).toMatchObject({ path: "f/file.ttl", ontologyIri: `${EX}file/ont`, versionIri: `${EX}file` });
    expect(byIri.get(`${EX}none`)?.path).toBeUndefined();
    expect(plan.roots).toEqual([`${EX}root`]);
    expect(plan.problems).toEqual([]);
  });

  it("lets a catalog entry win over a dropped file that declares the IRI, and a file win over a held import", () => {
    const plan = resolveImports(
      input({
        roots: ["root.ttl"],
        files: [file("root.ttl", ttl(`${EX}root`, [`${EX}a`, `${EX}b`, `${EX}c`])), file("one/a.ttl", ttl(`${EX}a`)), file("two/a.ttl", ttl(`${EX}a`)), file("b.ttl", ttl(`${EX}b`)), file("c.ttl", ttl(`${EX}c`))],
        catalog: new Map([[`${EX}a`, "two/a.ttl"]]),
        held: new Map([[`${EX}b`, "d1"]]),
        staged: new Set([`${EX}b`, `${EX}c`]),
      }),
    );
    const byIri = new Map(plan.nodes.map((n) => [n.iri, n]));
    expect(byIri.get(`${EX}a`)).toMatchObject({ status: "catalog", path: "two/a.ttl" });
    expect(byIri.get(`${EX}b`)?.status).toBe("file");
    expect(byIri.get(`${EX}c`)?.status).toBe("file");
  });

  it("prefers a held import to a staged document", () => {
    const plan = resolveImports(input({ roots: ["r.ttl"], files: [file("r.ttl", ttl(`${EX}r`, [`${EX}x`]))], held: new Map([[`${EX}x`, "d"]]), staged: [`${EX}x`] }));
    expect(statuses(plan)[`${EX}x`]).toBe("held");
  });

  it("walks through resolved documents to their own imports", () => {
    const plan = resolveImports(
      input({ roots: ["r.ttl"], files: [file("r.ttl", ttl(`${EX}r`, [`${EX}a`])), file("a.ttl", ttl(`${EX}a`, [`${EX}b`])), file("b.ttl", ttl(`${EX}b`, [`${EX}gone`]))] }),
    );
    expect(statuses(plan)).toEqual({ [`${EX}r`]: "file", [`${EX}a`]: "file", [`${EX}b`]: "file", [`${EX}gone`]: "missing" });
    expect(plan.edges).toEqual([
      { from: `${EX}a`, to: `${EX}b` },
      { from: `${EX}b`, to: `${EX}gone` },
      { from: `${EX}r`, to: `${EX}a` },
    ]);
  });

  it("terminates on a cycle and does not call it a problem", () => {
    const plan = resolveImports(
      input({ roots: ["a.ttl"], files: [file("a.ttl", ttl(`${EX}a`, [`${EX}b`])), file("b.ttl", ttl(`${EX}b`, [`${EX}a`]))] }),
    );
    expect(plan.problems).toEqual([]);
    expect(plan.nodes.map((n) => [n.iri, n.importedBy])).toEqual([
      [`${EX}a`, [`${EX}b`]],
      [`${EX}b`, [`${EX}a`]],
    ]);
  });

  it("lists both importers of a diamond", () => {
    const plan = resolveImports(
      input({
        roots: ["top.ttl"],
        files: [file("top.ttl", ttl(`${EX}top`, [`${EX}l`, `${EX}r`])), file("l.ttl", ttl(`${EX}l`, [`${EX}base`])), file("r.ttl", ttl(`${EX}r`, [`${EX}base`])), file("base.ttl", ttl(`${EX}base`))],
      }),
    );
    expect(plan.nodes.find((n) => n.iri === `${EX}base`)?.importedBy).toEqual([`${EX}l`, `${EX}r`]);
  });

  it("reports a catalog entry whose file was not dropped, and still tries the later steps", () => {
    const base = { roots: ["r.ttl"], catalog: new Map([[`${EX}x`, "gone/x.ttl"]]) };
    const missing = resolveImports(input({ ...base, files: [file("r.ttl", ttl(`${EX}r`, [`${EX}x`]))] }));
    expect(statuses(missing)[`${EX}x`]).toBe("missing");
    expect(missing.problems).toMatchObject([{ kind: "catalog-file-not-dropped", iri: `${EX}x`, path: "gone/x.ttl" }]);
    const found = resolveImports(input({ ...base, files: [file("r.ttl", ttl(`${EX}r`, [`${EX}x`])), file("elsewhere.ttl", ttl(`${EX}x`))] }));
    expect(statuses(found)[`${EX}x`]).toBe("file");
    expect(found.problems.map((p) => p.kind)).toEqual(["catalog-file-not-dropped"]);
  });

  it("reports a catalog web location without fetching it", () => {
    const plan = resolveImports(input({ roots: ["r.ttl"], files: [file("r.ttl", ttl(`${EX}r`, [`${EX}w`]))], catalog: new Map([[`${EX}w`, "https://www.w3.org/ns/w"]]) }));
    expect(statuses(plan)[`${EX}w`]).toBe("missing");
    expect(plan.problems.map((p) => p.kind)).toEqual(["catalog-web-location"]);
  });

  it("reports a catalog entry whose file declares a different IRI", () => {
    const plan = resolveImports(input({ roots: ["r.ttl"], files: [file("r.ttl", ttl(`${EX}r`, [`${EX}x`])), file("x.ttl", ttl(`${EX}other`))], catalog: new Map([[`${EX}x`, "x.ttl"]]) }));
    expect(statuses(plan)[`${EX}x`]).toBe("catalog");
    expect(plan.problems).toMatchObject([{ kind: "catalog-iri-mismatch", iri: `${EX}x`, path: "x.ttl" }]);
  });

  it("reports a file that does not parse, a root that was not dropped and a root with no ontology", () => {
    const plan = resolveImports(
      input({
        roots: ["r.ttl", "nowhere.ttl", "plain.ttl"],
        files: [file("r.ttl", ttl(`${EX}r`, [`${EX}bad`])), file("bad.ttl", "<a> <b> ."), file("plain.ttl", "@prefix ex: <https://example.org/> . ex:a ex:p ex:b .")],
        catalog: new Map([[`${EX}bad`, "bad.ttl"]]),
      }),
    );
    expect(plan.problems.map((p) => p.kind)).toEqual(["root-not-dropped", "root-without-ontology", "unparseable"]);
  });

  it("reports two files that declare the same IRI and uses the first path", () => {
    const plan = resolveImports(input({ roots: ["r.ttl"], files: [file("r.ttl", ttl(`${EX}r`, [`${EX}x`])), file("z.ttl", ttl(`${EX}x`)), file("a.ttl", ttl(`${EX}x`))] }));
    expect(plan.nodes.find((n) => n.iri === `${EX}x`)?.path).toBe("a.ttl");
    expect(plan.problems.map((p) => p.kind)).toEqual(["ambiguous-declaration"]);
  });

  it("gives the same plan for any order of files and roots, and for a repeat", () => {
    const files = [
      file("top.ttl", ttl(`${EX}top`, [`${EX}l`, `${EX}r`, `${EX}ext`])),
      file("l.ttl", ttl(`${EX}l`, [`${EX}base`])),
      file("r.ttl", ttl(`${EX}r`, [`${EX}base`, `${EX}top`])),
      file("base.ttl", ttl(`${EX}base`, [], `${EX}base/1`)),
      file("dup1.ttl", ttl(`${EX}base`)),
    ];
    const permutations = [files, [...files].reverse(), [files[3], files[0], files[4], files[2], files[1]]];
    const plans = permutations.map((fs, i) =>
      resolveImports(input({ roots: i % 2 ? ["top.ttl", "l.ttl"] : ["l.ttl", "top.ttl"], files: fs, catalog: new Map([[`${EX}ext`, "https://example.net/ext"]]), held: new Map([[`${EX}x`, "d"]]) })),
    );
    expect(plans[1]).toEqual(plans[0]);
    expect(plans[2]).toEqual(plans[0]);
    expect(resolveImports(input({ roots: ["l.ttl", "top.ttl"], files, catalog: new Map([[`${EX}ext`, "https://example.net/ext"]]), held: new Map([[`${EX}x`, "d"]]) }))).toEqual(plans[0]);
  });
});

// The real LATTICE files, read from disk. The dropped root is the repository's ontology/ folder.
// The page URL is read as text, since the jsdom environment replaces URL and fileURLToPath refuses its objects.
const here = dirname(decodeURIComponent(import.meta.url.replace(/^file:\/\//, "")));
const repoRoot = `${resolve(here, "../../../..")}/`;
const read = (relative: string): string | undefined => {
  try {
    return readFileSync(`${repoRoot}ontology/${relative}`, "utf8");
  } catch {
    return undefined;
  }
};
const LATTICE = "https://www.nebularis.org/neuro-semantic/";

// Drops the catalog and the roots, then adds each file the plan says the catalog names, until the
// plan asks for no more.
function dropFor(roots: string[], startCatalog = "catalog-v001.xml"): { files: Map<string, string>; run: (files: Map<string, string>) => ReturnType<typeof resolveImports> } {
  const run = (files: Map<string, string>) => {
    const { lookup } = buildCatalogLookup(
      new Map([...files].filter(([p]) => p.endsWith(".xml"))),
      startCatalog,
    );
    return resolveImports({
      roots,
      files: [...files].map(([path, text]) => ({ path, text })),
      catalog: lookup,
      held: new Map(),
      staged: new Set(),
    });
  };
  const files = new Map<string, string>();
  for (const path of ["catalog-v001.xml", startCatalog, ...roots]) files.set(path, read(path)!);
  for (let again = true; again; ) {
    again = false;
    for (const problem of run(files).problems) {
      if (problem.kind !== "catalog-file-not-dropped" || !problem.path) continue;
      const text = read(problem.path);
      if (text !== undefined) {
        files.set(problem.path, text);
        again = true;
      }
    }
  }
  return { files, run };
}

describe("LATTICE's own catalog", () => {
  const roots = ["foundation/spec/foundation.ttl", "persistence/spec/persistent-foundation.ttl", "ledger/spec/ledger.ttl"];

  it("resolves every import in a LATTICE namespace through the catalog", () => {
    const { files, run } = dropFor(roots);
    const plan = run(files);
    const own = plan.nodes.filter((n) => n.iri.startsWith(LATTICE));
    expect(own.length).toBeGreaterThan(3);
    for (const node of plan.nodes.filter((n) => n.iri.startsWith(LATTICE) && n.importedBy.length > 0)) {
      expect(node.status, node.iri).toBe("catalog");
    }
    expect(plan.problems.filter((p) => p.iri?.startsWith(LATTICE))).toEqual([]);
    const importedLattice = new Set(plan.edges.filter((e) => e.to.startsWith(LATTICE)).map((e) => e.to));
    expect(importedLattice.has(`${LATTICE}lattice/foundation/0.21.1`)).toBe(true);
    expect(importedLattice.has(`${LATTICE}lattice/persistence/0.22.1`)).toBe(true);
  });

  it("finds the chain from a per-directory stub catalog", () => {
    const { files, run } = dropFor(["persistence/spec/persistent-foundation.ttl"], "persistence/spec/catalog-v001.xml");
    const plan = run(files);
    expect(plan.nodes.find((n) => n.iri === `${LATTICE}lattice/foundation/0.21.1`)?.status).toBe("catalog");
  });

  it("expects an import outside LATTICE to be missing", () => {
    const { files, run } = dropFor(roots);
    const external = run(files).nodes.filter((n) => !n.iri.startsWith(LATTICE) && n.importedBy.length > 0);
    expect(external.length).toBeGreaterThan(0);
    expect(external.every((n) => n.status === "missing")).toBe(true);
  });

  it("reports a removed file as a problem for its catalog entry, with the import missing", () => {
    const only = ["persistence/spec/persistent-foundation.ttl"];
    const { files, run } = dropFor(only);
    files.delete("foundation/spec/foundation.ttl");
    const plan = run(files);
    const iri = `${LATTICE}lattice/foundation/0.21.1`;
    expect(plan.nodes.find((n) => n.iri === iri)?.status).toBe("missing");
    expect(plan.problems).toContainEqual(expect.objectContaining({ kind: "catalog-file-not-dropped", iri, path: "foundation/spec/foundation.ttl" }));
    expect(plan.nodes.find((n) => n.iri === `${LATTICE}lattice/persistence/0.22.1`)?.status).toBe("catalog");
  });
});
