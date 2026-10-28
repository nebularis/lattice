// SPDX-License-Identifier: MPL-2.0
// The graph model: list replacement and deterministic Turtle.

import { describe, expect, it } from "vitest";
import { DAL } from "./ns";
import { Graph, iri, literal } from "./graph";

describe("graph", () => {
  const ns = "https://example.org/lending#";
  const loan = ns + "LoanApplication";

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
});
