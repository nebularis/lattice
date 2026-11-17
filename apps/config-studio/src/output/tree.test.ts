// @vitest-environment jsdom
// SPDX-License-Identifier: MPL-2.0
import { describe, expect, it } from "vitest";
import { parseJsonTree, parseXmlTree, prettyJson, type ParsedTree, type TreeNode } from "./tree";

const root = (parsed: ParsedTree): TreeNode => {
  if (!parsed.ok) throw new Error(parsed.message);
  return parsed.root;
};

describe("parseJsonTree", () => {
  const tree = root(parseJsonTree('{"name":"Ada","age":36,"ok":true,"gone":null,"tags":["a","b"],"nested":{"x":1.5},"empty":[]}'));
  const child = (label: string) => tree.children.find((c) => c.label === label)!;
  it("has a node for each key of an object, in the order written, with its value's kind", () => {
    expect(tree.kind).toBe("object");
    expect(tree.summary).toBe("7 keys");
    expect(tree.children.map((c) => c.label)).toEqual(["name", "age", "ok", "gone", "tags", "nested", "empty"]);
    expect(child("name")).toMatchObject({ kind: "string", value: '"Ada"' });
    expect(child("age")).toMatchObject({ kind: "number", value: "36" });
    expect(child("ok")).toMatchObject({ kind: "boolean", value: "true" });
    expect(child("gone")).toMatchObject({ kind: "null", value: "null" });
    expect(child("nested").children[0]).toMatchObject({ kind: "number", value: "1.5" });
  });
  it("has each item of an array with its index and a summary of its size", () => {
    expect(child("tags")).toMatchObject({ kind: "array", summary: "2 items" });
    expect(child("tags").children.map((c) => c.label)).toEqual(["0", "1"]);
    expect(child("empty")).toMatchObject({ kind: "array", summary: "0 items", children: [] });
  });
  it("gives each node a path that is unique", () => {
    const ids: string[] = [];
    const walk = (n: TreeNode) => (ids.push(n.id), n.children.forEach(walk));
    walk(tree);
    expect(new Set(ids).size).toBe(ids.length);
  });
  it("reads a scalar at the top, and says why a text is not JSON", () => {
    expect(root(parseJsonTree("3"))).toMatchObject({ kind: "number" });
    const bad = parseJsonTree('{"a": ');
    expect(bad.ok).toBe(false);
    expect(!bad.ok && bad.message.length).toBeGreaterThan(0);
  });
});

describe("prettyJson", () => {
  it("indents by two and reports a text that is not JSON", () => {
    expect(prettyJson('{"a":[1,2]}')).toEqual({ ok: true, text: '{\n  "a": [\n    1,\n    2\n  ]\n}' });
    expect(prettyJson("{").ok).toBe(false);
  });
});

describe("parseXmlTree", () => {
  const xml = '<?xml version="1.0"?><p:policy xmlns:p="urn:example:p" xmlns="urn:example:d" id="7">Intro <p:holder name="Ada"/>tail<![CDATA[ more ]]><!-- skipped --><item>1</item></p:policy>';
  const tree = root(parseXmlTree(xml));
  it("has the element with its attributes first, namespace declarations among them, and its prefix as written", () => {
    expect(tree).toMatchObject({ kind: "element", label: "p:policy" });
    const attributes = tree.children.filter((c) => c.kind === "attribute").map((c) => [c.label, c.value]);
    expect(attributes).toContainEqual(["id", "7"]);
    expect(attributes).toContainEqual(["xmlns:p", "urn:example:p"]);
    expect(attributes).toContainEqual(["xmlns", "urn:example:d"]);
  });
  it("keeps text and elements in the order written, mixed, and drops comments and blank text", () => {
    const rest = tree.children.filter((c) => c.kind !== "attribute");
    expect(rest.map((c) => [c.kind, c.label ?? c.value])).toEqual([["text", "Intro"], ["element", "p:holder"], ["text", "tail"], ["text", "more"], ["element", "item"]]);
    expect(rest[1].children[0]).toMatchObject({ kind: "attribute", label: "name", value: "Ada" });
    expect(rest[4].children[0]).toMatchObject({ kind: "text", value: "1" });
  });
  it("says why a text is not well formed, and never throws", () => {
    const bad = parseXmlTree("<a><b></a>");
    expect(bad.ok).toBe(false);
    expect(!bad.ok && bad.message.length).toBeGreaterThan(0);
    expect(parseXmlTree("").ok).toBe(false);
  });
});
