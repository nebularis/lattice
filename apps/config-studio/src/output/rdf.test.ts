// SPDX-License-Identifier: MPL-2.0
import { describe, expect, it } from "vitest";
import { Graph } from "@lattice/authoring-domain";
import { declaredPrefixes, filterRows, graphModel, parseRdf, prefixesOf, shorten, tableRows, termText, toNTriplesText, toTurtleText, type Parsed } from "./rdf";

const NT = `
<https://example.org/data/loan-1> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://example.org/lending#LoanApplication> .
<https://example.org/data/loan-1> <https://example.org/lending#amount> "250000"^^<http://www.w3.org/2001/XMLSchema#integer> .
<https://example.org/data/loan-1> <https://example.org/lending#note> "a \\"quoted\\" note"@en .
<https://example.org/data/loan-1> <https://example.org/lending#applicant> _:p .
_:p <https://example.org/lending#name> "Ada" .
_:p <https://example.org/lending#employer> _:e .
_:e <https://example.org/lending#name> "Example Ltd" .
`;

const ok = (parsed: Parsed) => {
  if (!parsed.ok) throw new Error(parsed.message);
  return parsed;
};

describe("parseRdf", () => {
  it("reads each RDF media type and keeps the prefixes the text declares", () => {
    const ttl = ok(parseRdf("@prefix ex: <https://example.org/> .\nex:a ex:p ex:b .\n", "text/turtle"));
    expect(ttl.quads).toHaveLength(1);
    expect(ttl.prefixes).toEqual({ ex: "https://example.org/" });
    expect(ok(parseRdf(NT, "application/n-triples")).quads).toHaveLength(7);
    const nq = ok(parseRdf("<https://example.org/a> <https://example.org/p> <https://example.org/b> <https://example.org/g> .\n", "application/n-quads"));
    expect(nq.quads[0].graph.value).toBe("https://example.org/g");
    const trig = ok(parseRdf("@prefix ex: <https://example.org/> .\nex:g { ex:a ex:p ex:b . }\n", "application/trig"));
    expect(trig.quads[0].graph.value).toBe("https://example.org/g");
  });
  it("gives the parser's message for a text that does not parse, and never throws", () => {
    const bad = parseRdf("<https://example.org/a> <https://example.org/p> .\n", "application/n-triples");
    expect(bad.ok).toBe(false);
    expect(!bad.ok && bad.message).toMatch(/line 1/i);
    expect(parseRdf("not turtle at all {", "text/turtle").ok).toBe(false);
    expect(parseRdf("x", "application/json").ok).toBe(false);
  });
});

describe("terms", () => {
  const prefixes = prefixesOf({}, { lend: "https://example.org/lending#" });
  it("compacts an IRI under the longest namespace and writes one that no prefix covers in angle brackets", () => {
    expect(shorten("https://example.org/lending#Loan", prefixes)).toBe("lend:Loan");
    expect(shorten("http://www.w3.org/ns/shacl#conforms", prefixes)).toBe("sh:conforms");
    expect(shorten("https://elsewhere.example/x/y", prefixes)).toBe("<https://elsewhere.example/x/y>");
    expect(shorten("https://example.org/lending#a b", prefixes)).toBe("<https://example.org/lending#a b>");
  });
  it("writes each kind of term", () => {
    const quads = ok(parseRdf(NT, "application/n-triples")).quads;
    const objects = quads.map((q) => termText(q.object, prefixes));
    expect(objects).toContain('"250000"^^xsd:integer');
    expect(objects).toContain('"a \\"quoted\\" note"@en');
    expect(objects).toContain('"Ada"');
    expect(objects.some((o) => o.startsWith("_:"))).toBe(true);
  });
});

describe("table", () => {
  const prefixes = prefixesOf({}, { lend: "https://example.org/lending#" });
  it("has one row for each triple, sorted by subject, predicate and object, and has a graph for quads", () => {
    const rows = tableRows(ok(parseRdf(NT, "application/n-triples")).quads, prefixes);
    expect(rows).toHaveLength(7);
    const keys = rows.map((r) => `${r.subject}\u0000${r.predicate}\u0000${r.object}`);
    expect(keys).toEqual([...keys].sort());
    expect(rows[0].subject < rows[rows.length - 1].subject).toBe(true);
    expect(rows.every((r) => r.graph === "")).toBe(true);
    const quads = ok(parseRdf("<https://example.org/a> <https://example.org/p> <https://example.org/b> <https://example.org/g> .\n", "application/n-quads")).quads;
    expect(tableRows(quads, {})[0].graph).toBe("<https://example.org/g>");
  });
  it("narrows by text in any column and keeps every row for a blank filter", () => {
    const rows = tableRows(ok(parseRdf(NT, "application/n-triples")).quads, prefixes);
    expect(filterRows(rows, "  ")).toBe(rows);
    expect(filterRows(rows, "ada")).toHaveLength(1);
    expect(filterRows(rows, "LEND:NAME")).toHaveLength(2);
    expect(filterRows(rows, "loan-1")).toHaveLength(4);
    expect(filterRows(rows, "no such text")).toHaveLength(0);
  });
  it("is the same for any order of the triples and for a repeat", () => {
    const lines = NT.trim().split("\n");
    const base = tableRows(ok(parseRdf(lines.join("\n"), "application/n-triples")).quads, prefixes);
    const permutations = [[...lines].reverse(), [...lines.slice(3), ...lines.slice(0, 3)], [...lines, ...lines]];
    for (const order of permutations) expect(tableRows(ok(parseRdf(order.join("\n"), "application/n-triples")).quads, prefixes)).toEqual(base);
    expect(tableRows(ok(parseRdf(lines.join("\n"), "application/n-triples")).quads, prefixes)).toEqual(base);
  });
});

describe("graph", () => {
  const prefixes = prefixesOf({}, { lend: "https://example.org/lending#" });
  const model = graphModel(ok(parseRdf(NT, "application/n-triples")).quads, prefixes);
  it("makes a node of each IRI or blank node and none of a literal, which is a row inside its subject's node", () => {
    expect(model.nodes.map((n) => n.label).filter((l) => !l.startsWith("_:"))).toEqual(["<https://example.org/data/loan-1>"]);
    expect(model.nodes).toHaveLength(3);
    expect(model.nodes.filter((n) => n.blank)).toHaveLength(2);
    const loan = model.nodes.find((n) => n.id === "https://example.org/data/loan-1")!;
    expect(loan.types).toEqual(["lend:LoanApplication"]);
    expect(loan.rows.map((r) => r.predicate)).toEqual(["lend:amount", "lend:note"]);
    expect(loan.rows[0].value).toBe('"250000"^^xsd:integer');
    expect(model.nodes.some((n) => n.label === '"Ada"')).toBe(false);
  });
  it("makes an edge labelled with its predicate for each triple between two nodes, and none for a type", () => {
    expect(model.edges.map((e) => e.label).sort()).toEqual(["lend:applicant", "lend:employer"]);
    expect(model.edges.every((e) => model.nodes.some((n) => n.id === e.source) && model.nodes.some((n) => n.id === e.target))).toBe(true);
  });
  it("reads a link from a node to itself as a row", () => {
    const m = graphModel(ok(parseRdf("<https://example.org/a> <https://example.org/p> <https://example.org/a> .\n", "application/n-triples")).quads, {});
    expect(m.edges).toHaveLength(0);
    expect(m.nodes[0].rows).toEqual([{ predicate: "<https://example.org/p>", value: "this node" }]);
  });
  it("merges the graphs of a dataset", () => {
    const m = graphModel(ok(parseRdf("<https://example.org/a> <https://example.org/p> <https://example.org/b> <https://example.org/g1> .\n<https://example.org/a> <https://example.org/p> <https://example.org/b> <https://example.org/g2> .\n", "application/n-quads")).quads, {});
    expect(m.edges).toHaveLength(1);
  });
  it("is the same for any order of the triples and for a repeat", () => {
    const lines = NT.trim().split("\n");
    for (const order of [[...lines].reverse(), [...lines.slice(2), ...lines.slice(0, 2)], [...lines, ...lines]]) {
      expect(graphModel(ok(parseRdf(order.join("\n"), "application/n-triples")).quads, prefixes)).toEqual(model);
    }
  });
});

describe("text", () => {
  const parsed = ok(parseRdf(NT, "application/n-triples"));
  const prefixes = prefixesOf(parsed.prefixes);
  it("is Turtle from the graph's own writer, which Turtle parsing reads back to the same triples", () => {
    const turtle = toTurtleText(parsed.quads, prefixes);
    expect(turtle).toContain("a ");
    expect(Graph.parse(turtle).size).toBe(7);
  });
  it("is N-Triples, one sorted line for each distinct triple, which parses back to the same triples", () => {
    const nt = toNTriplesText([...parsed.quads, ...parsed.quads]);
    const lines = nt.trimEnd().split("\n");
    expect(lines).toHaveLength(7);
    expect(lines).toEqual([...lines].sort());
    expect(ok(parseRdf(nt, "application/n-triples")).quads).toHaveLength(7);
  });
  it("is the same for any order of the triples", () => {
    expect(toNTriplesText([...parsed.quads].reverse())).toBe(toNTriplesText(parsed.quads));
    expect(toTurtleText([...parsed.quads].reverse(), prefixes)).toBe(toTurtleText(parsed.quads, prefixes));
  });
});

describe("declaredPrefixes", () => {
  it("reads the prefixes the writer put at the head of its Turtle, including ones it made up, and stops at the first statement", () => {
    const parsed = ok(parseRdf(NT, "application/n-triples"));
    const turtle = toTurtleText(parsed.quads, prefixesOf(parsed.prefixes));
    const declared = declaredPrefixes(turtle);
    expect(declared.lending).toBe("https://example.org/lending#");
    expect(declared.xsd).toBe("http://www.w3.org/2001/XMLSchema#");
    expect(declaredPrefixes("<a> <b> <c> .\n@prefix late: <urn:late#> .\n")).toEqual({});
    expect(declaredPrefixes("")).toEqual({});
  });
});
