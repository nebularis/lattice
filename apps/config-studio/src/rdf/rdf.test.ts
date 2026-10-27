// SPDX-License-Identifier: MPL-2.0
// The studio's RDF layer against the vocabulary and samples the service serves, as staged by
// `mise run build:config-studio-assets` (tools/config_studio_stage.py).

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { beforeAll, describe, expect, it } from "vitest";
import { Baseline } from "./baseline";
import { KINDS, checkReferences, create, items, sectionsFor } from "./editors";
import { Graph, iri, literal } from "./graph";
import { CST, DAL, SH, SRF } from "./ns";
import { readJob } from "./report";
import { split } from "./split";
import { readPath, writePath } from "./path";
import { diffLines, tokenise } from "../lib/text";
import { Vocabulary } from "./vocabulary";

const assets = process.env.LATTICE_STUDIO_ASSETS ?? join(import.meta.dirname, "../../../../.build/config-studio");
const read = (name: string) => readFileSync(join(assets, name), "utf-8");

let vocab: Vocabulary;
beforeAll(() => {
  vocab = Vocabulary.parse(read("vocabulary.ttl"));
});

const kind = (type: string) => KINDS.find((k) => k.type === type)!;

describe("fields derived from the ontology", () => {
  it("offers a closed set's individuals, with their comments, for an object property", () => {
    const strategy = vocab.field(DAL("strategy"));
    expect(strategy.kind).toBe("choice");
    expect(strategy.single).toBe(true);
    expect(strategy.options.map((o) => o.iri)).toEqual(
      expect.arrayContaining([DAL("NamedGraphBoundary"), DAL("CompositePropertyBoundary"), DAL("NoBoundary")]),
    );
    expect(strategy.options.every((o) => o.comment.length > 0)).toBe(true);
  });

  it("picks a control from the range: number, switch, text, baseline class and property", () => {
    expect(vocab.field(DAL("metaShards")).kind).toBe("number");
    expect(vocab.field(DAL("includeSubclasses")).kind).toBe("boolean");
    expect(vocab.field(DAL("graphIriTemplate")).kind).toBe("text");
    expect(vocab.field(SRF("carrier")).kind).toBe("class");
    expect(vocab.field(SRF("promotesTo")).kind).toBe("property");
    expect(vocab.field(DAL("keyProperty")).kind).toBe("propertyList");
    expect(vocab.field(SRF("surfaceProfile")).kind).toBe("reference");
  });

  it("lets a non-functional srf: property take several values", () => {
    expect(vocab.field(SRF("indexForm")).single).toBe(false);
    expect(vocab.field(SRF("namingPolicy")).single).toBe(true);
  });

  it("gives a data access profile one section per dimension, each property placed once", () => {
    const sections = sectionsFor(kind(DAL("DataAccessProfile")), vocab);
    expect(sections.map((s) => s.title)).toContain("Concurrency");
    const concurrency = sections.find((s) => s.title === "Concurrency")!;
    expect(concurrency.fields[0].property).toBe(DAL("concurrencyProfile"));
    const all = sections.flatMap((s) => s.fields.map((f) => f.property));
    expect(new Set(all).size).toBe(all.length);
    expect(all).toContain(DAL("appliesTo"));
  });

  it("keeps the read path out of a contract's fields and gives it its own section", () => {
    const sections = sectionsFor(kind(SRF("IndexContract")), vocab);
    expect(sections.some((s) => s.path)).toBe(true);
    const all = sections.flatMap((s) => s.fields.map((f) => f.property));
    expect(all).not.toContain(SRF("readProperty"));
    expect(all).not.toContain(SRF("hasPathStep"));
  });
});

describe("importing a sample", () => {
  it("sorts the employment sample into baseline and surface, path steps and lists with their owner", () => {
    const parts = split(Graph.parse(read("samples/employment.ttl")));
    const contract = "https://example.org/lattice/surface/employment#job-family-index";
    expect(parts.surface.types(contract)).toContain(SRF("IndexContract"));
    expect(parts.baseline.has(contract)).toBe(false);
    expect(parts.baseline.has("https://example.org/lattice/surface/employment#RoleAssignment")).toBe(true);
    expect(parts.persistence.size).toBe(0);
    expect(parts.baseline.size + parts.surface.size).toBe(Graph.parse(read("samples/employment.ttl")).size);
  });

  it("sorts the lending sample's profile and key, with its RDF list, into persistence", () => {
    const parts = split(Graph.parse(read("samples/lending.ttl")));
    const key = "https://example.org/lending#LoanApplicationNumberPerBranch";
    const head = parts.persistence.object(key, DAL("keyProperty"))!;
    expect(parts.persistence.list(head)?.map((t) => t.value)).toEqual(["https://example.org/lending#applicationNumber"]);
    expect(new Baseline(parts.baseline).classes.has("https://example.org/lending#LoanApplication")).toBe(true);
  });
});

describe("the baseline", () => {
  it("lists inherited properties of a class and the class hierarchy", () => {
    const baseline = Baseline.parse(readFileSync(join(import.meta.dirname, "../../../../contracts/config-studio/samples/lending-baseline.ttl"), "utf-8"));
    expect(baseline.propertiesOf("https://example.org/lending#Borrower").map((p) => p.iri)).toContain("https://example.org/lending#taxIdentifier");
    expect(baseline.roots().map((c) => c.iri)).toContain("https://example.org/lending#Party");
    expect(baseline.namespace).toBe("https://example.org/lending#");
    expect(baseline.schemes[0].concepts).toHaveLength(4);
  });
});

describe("editing", () => {
  const ns = "https://example.org/lending#";
  const loan = ns + "LoanApplication";

  it("makes a profile for a class through a class scope, reusing the scope for a second node", () => {
    const empty = Graph.empty();
    const first = create(empty, kind(DAL("DataAccessProfile")), "Loan application profile", ns, loan);
    const scope = first.graph.value(first.iri, DAL("appliesTo"))!;
    expect(first.graph.value(scope, DAL("targetClass"))).toBe(loan);
    const second = create(first.graph, kind(DAL("UniquenessConstraint")), "Application number", ns, loan);
    expect(second.graph.value(second.iri, DAL("appliesTo"))).toBe(scope);
    expect(second.graph.value(second.iri, DAL("constraintId"))).toBe("application-number");
    expect(second.graph.ofType(DAL("ClassScope"))).toHaveLength(1);
  });

  it("mints a distinct IRI for a repeated name", () => {
    const a = create(Graph.empty(), kind(DAL("ClassScope")), "scope", ns);
    const b = create(a.graph, kind(DAL("ClassScope")), "scope", ns);
    expect(b.iri).not.toBe(a.iri);
  });

  it("replaces an RDF list without leaving its old cells behind, and removes a node with its references", () => {
    const g = Graph.empty().edit((e) => {
      e.add(ns + "k", DAL("appliesTo"), iri(ns + "s"));
      e.add(ns + "s", DAL("targetClass"), iri(loan));
    });
    const once = g.edit((e) => e.setList(ns + "k", DAL("keyProperty"), [iri(ns + "a"), iri(ns + "b")]));
    const twice = once.edit((e) => e.setList(ns + "k", DAL("keyProperty"), [iri(ns + "c")]));
    expect(twice.size).toBe(g.size + 3);
    const removed = twice.edit((e) => e.remove(ns + "s"));
    expect(removed.has(ns + "s")).toBe(false);
    expect(removed.value(ns + "k", DAL("appliesTo"))).toBeUndefined();
  });

  it("writes the same Turtle whatever order the triples were added in, with lists inline", () => {
    const a = Graph.empty().edit((e) => {
      e.add(ns + "x", DAL("constraintId"), literal("k"));
      e.setList(ns + "x", DAL("keyProperty"), [iri(ns + "a")]);
    });
    const b = Graph.parse(a.toTurtle());
    expect(b.toTurtle()).toBe(a.toTurtle());
    expect(a.toTurtle()).toContain("dal:keyProperty (lending:a)");
    expect(a.toTurtle()).not.toContain("@prefix rdf:");
    expect(a.toTurtle()).toContain("@prefix dal:");
  });

  it("lists the lending sample's nodes by kind with a readable detail", () => {
    const parts = split(Graph.parse(read("samples/lending.ttl")));
    const list = items(parts.persistence, "persistence", new Baseline(parts.baseline), vocab);
    expect(list.map((i) => i.kind.title)).toEqual(["Data access profile", "Class scope", "Uniqueness constraint"]);
    expect(list[0].detail).toBe("applies to Loan application");
  });

  it("flags a baseline term the baseline lacks and a reference to nothing, never a vocabulary term", () => {
    const baseline = Baseline.parse(read("samples/lending.ttl"));
    const g = Graph.empty().edit((e) => {
      e.add(ns + "s", DAL("targetClass"), iri(ns + "Missing"));
      e.add(ns + "p", DAL("appliesTo"), iri(ns + "Nowhere"));
      e.add(ns + "c", SRF("closureBasis"), iri("http://www.w3.org/2004/02/skos/core#broader"));
      e.add(ns + "c", DAL("onViolation"), iri(DAL("Reject")));
    });
    const issues = checkReferences(g, baseline, vocab);
    expect(issues.map((i) => [i.severity, i.path])).toEqual([
      ["Warning", DAL("targetClass")],
      ["Warning", DAL("appliesTo")],
    ]);
  });
});

describe("job results", () => {
  it("reads status, findings in severity order, artefacts and gaps", () => {
    const job = "urn:lattice:studio:job:00000000-0000-4000-8000-000000000000";
    const g = Graph.empty().edit((e) => {
      e.add(job, CST("kind"), iri(CST("Compile")));
      e.add(job, CST("target"), iri(CST("Persistence")));
      e.add(job, CST("status"), iri(CST("Succeeded")));
      e.add(job, CST("conforms"), literal("false"));
      e.add(job, CST("report"), iri(job + "#report"));
      e.add(job + "#report", SH("result"), iri(job + "#r1"));
      e.add(job + "#r1", SH("resultSeverity"), iri(SH("Warning")));
      e.add(job + "#r1", SH("resultMessage"), literal("careful"));
      e.add(job + "#report", SH("result"), iri(job + "#r2"));
      e.add(job + "#r2", SH("resultSeverity"), iri(SH("Violation")));
      e.add(job + "#r2", SH("resultMessage"), literal("refused"));
      e.add(job + "#r2", CST("code"), literal("CrossAxisViolation"));
      e.add(job, CST("artefact"), iri(job + "#a"));
      e.add(job + "#a", CST("path"), literal("x/write.rq"));
      e.add(job + "#a", CST("group"), literal("x"));
      e.add(job + "#a", CST("content"), literal("SELECT * {}"));
    });
    const read = readJob(g, job);
    expect(read.status).toBe("Succeeded");
    expect(read.conforms).toBe(false);
    expect(read.issues.map((i) => [i.severity, i.source])).toEqual([
      ["Violation", "compiler"],
      ["Warning", "shacl"],
    ]);
    expect(read.artefacts[0].path).toBe("x/write.rq");
  });
});

describe("the read path", () => {
  const ns = "https://example.org/x#";
  const c = ns + "contract";

  it("writes one forward hop as srf:readProperty and more as ordered path steps, never both", () => {
    const one = writePath(Graph.empty(), c, [{ property: ns + "a", inverse: false }]);
    expect(one.value(c, SRF("readProperty"))).toBe(ns + "a");
    expect(one.objects(c, SRF("hasPathStep"))).toHaveLength(0);
    const steps = [
      { property: ns + "a", inverse: false },
      { property: ns + "b", inverse: true },
    ];
    const two = writePath(one, c, steps);
    expect(two.value(c, SRF("readProperty"))).toBeUndefined();
    expect(readPath(two, c)).toEqual(steps);
    const back = writePath(two, c, [{ property: ns + "a", inverse: false }]);
    expect(back.size).toBe(one.size);
  });

  it("writes a single inverse hop as a path step", () => {
    const g = writePath(Graph.empty(), c, [{ property: ns + "a", inverse: true }]);
    expect(g.value(c, SRF("readProperty"))).toBeUndefined();
    expect(readPath(g, c)).toEqual([{ property: ns + "a", inverse: true }]);
  });
});

describe("text", () => {
  it("diffs lines, keeping common ones", () => {
    expect(diffLines("a\nb\nc", "a\nc\nd").map((l) => l.op + l.text)).toEqual([" a", "-b", " c", "+d"]);
  });

  it("colours Turtle without losing a character", () => {
    const source = '@prefix ex: <https://example.org/> .\nex:a ex:b "c" ; # note\n  ex:d 42 .';
    const tokens = tokenise(source);
    expect(tokens.map((t) => t.text).join("")).toBe(source);
    expect(tokens.find((t) => t.kind === "comment")?.text).toBe("# note");
    expect(tokens.find((t) => t.kind === "iri")?.text).toBe("<https://example.org/>");
  });
});
