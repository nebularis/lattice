// SPDX-License-Identifier: MPL-2.0
import { describe, expect, it } from "vitest";
import { NO_CHOICES, formatOf, readChoices, renderingOf, renderingsFor, withFormat, withRendering, writeChoices, CHOICES_KEY, familyOf, baseType } from "./media";

const memory = () => {
  const map = new Map<string, string>();
  return { map, getItem: (k: string) => map.get(k) ?? null, setItem: (k: string, v: string) => void map.set(k, v) };
};

describe("renderingsFor", () => {
  it("offers text, a table and a graph for each RDF media type, text first", () => {
    for (const type of ["text/turtle", "application/n-triples", "application/n-quads", "application/trig"]) expect(renderingsFor(type)).toEqual(["text", "table", "graph"]);
  });
  it("offers a tree first, then text, for JSON and for XML", () => {
    for (const type of ["application/json", "application/ld+json", "application/xml", "text/xml", "application/xslt+xml"]) expect(renderingsFor(type)).toEqual(["tree", "text"]);
  });
  it("offers text only for anything else", () => {
    for (const type of ["application/sparql-query", "text/plain", ""]) expect(renderingsFor(type)).toEqual(["text"]);
  });
  it("ignores parameters and case", () => {
    expect(baseType("Text/Turtle; charset=utf-8")).toBe("text/turtle");
    expect(familyOf("APPLICATION/JSON;charset=utf-8")).toBe("json");
  });
});

describe("the kept choice", () => {
  it("is the default where nothing is kept and the kept one for its media type only", () => {
    expect(renderingOf("text/turtle", NO_CHOICES)).toBe("text");
    const kept = withRendering(NO_CHOICES, "application/n-triples", "table");
    expect(renderingOf("application/n-triples", kept)).toBe("table");
    expect(renderingOf("text/turtle", kept)).toBe("text");
  });
  it("ignores a rendering the media type does not offer", () => {
    expect(renderingOf("application/json", withRendering(NO_CHOICES, "application/json", "graph"))).toBe("tree");
  });
  it("is written and read back, with the text format", () => {
    const store = memory();
    writeChoices(withFormat(withRendering(NO_CHOICES, "text/turtle", "graph"), "text/turtle", "ntriples"), store);
    const back = readChoices(store);
    expect(renderingOf("text/turtle", back)).toBe("graph");
    expect(formatOf("text/turtle", back)).toBe("ntriples");
    expect(formatOf("application/json", back)).toBe("turtle");
  });
  it("is read part by part, so a bad value is ignored and the rest holds", () => {
    const store = memory();
    store.map.set(CHOICES_KEY, JSON.stringify({ renderings: { "text/turtle": "table", "application/json": 7, "text/xml": "nonsense" }, formats: [] }));
    const back = readChoices(store);
    expect(back.renderings).toEqual({ "text/turtle": "table" });
    expect(back.formats).toEqual({});
  });
  it("is the default for text that is not JSON, not an object or a store that throws or is absent", () => {
    for (const raw of ["{not json", "[]", "3", "null"]) expect(readChoices({ getItem: () => raw, setItem: () => undefined })).toEqual(NO_CHOICES);
    const throwing = { getItem: () => { throw new Error("blocked"); }, setItem: () => { throw new Error("blocked"); } };
    expect(readChoices(throwing)).toEqual(NO_CHOICES);
    expect(() => writeChoices(NO_CHOICES, throwing)).not.toThrow();
    expect(readChoices(undefined)).toEqual(NO_CHOICES);
  });
});
