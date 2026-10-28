// SPDX-License-Identifier: MPL-2.0
import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { readMarkup, writeMarkup } from "./markup";
import type { DocumentSnapshot } from "./types";

const samples = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../contracts/document/samples");

const doc = (over: Partial<DocumentSnapshot> = {}): DocumentSnapshot => ({
  schemaVersion: "0.1.0",
  documentId: "00000003-0000-4000-8000-000000000000",
  templateId: "facility-agreement",
  title: "T",
  sections: [],
  variables: [],
  unmarked: [],
  ...over,
});

describe("markup", () => {
  const files = readdirSync(samples).filter((name) => name.endsWith(".xml"));

  it("finds the contract samples", () => {
    expect(files.length).toBeGreaterThan(0);
  });

  it.each(files)("reads %s and writes it back exactly", (name) => {
    const text = readFileSync(path.join(samples, name), "utf8");
    expect(writeMarkup(readMarkup(text))).toBe(text);
  });

  it("escapes text and attributes and reads them back", () => {
    const original = doc({
      title: 'A & B <C> "D"',
      sections: [
        {
          sectionKey: "definitions",
          elements: [
            {
              elementId: "00000003-0000-4000-8000-000000000001",
              kind: "definition",
              definedTerm: 'Say "hi" & <go>',
              parts: [
                { kind: "literal", text: 'a < b && "c" > d' },
                { kind: "variable", variableKey: "fee", text: "<1 & 2>" },
                { kind: "literal", text: "\r\n" },
              ],
            },
          ],
        },
      ],
    });
    const xml = writeMarkup(original);
    expect(xml).toContain('term="Say &quot;hi&quot; &amp; &lt;go&gt;"');
    expect(xml).toContain('a &lt; b &amp;&amp; "c" &gt; d');
    expect(xml).toContain("&#13;\n</definition>");
    expect(readMarkup(xml)).toEqual(original);
  });

  it("merges adjacent literal parts and drops empty ones", () => {
    const xml = writeMarkup(
      doc({
        sections: [
          {
            sectionKey: "s",
            elements: [
              {
                elementId: "00000003-0000-4000-8000-000000000001",
                kind: "clause",
                definedTerm: null,
                parts: [
                  { kind: "literal", text: "a" },
                  { kind: "literal", text: "" },
                  { kind: "literal", text: "b" },
                  { kind: "reference", targetElementId: "00000003-0000-4000-8000-000000000002", text: "T" },
                  { kind: "literal", text: "c" },
                ],
              },
            ],
          },
        ],
      }),
    );
    expect(xml).toContain('>ab<ref target="00000003-0000-4000-8000-000000000002">T</ref>c</clause>');
  });

  it("keeps unmarked text inside and outside sections, and mixed content exactly", () => {
    const original = doc({
      sections: [
        {
          sectionKey: "s",
          elements: [
            {
              elementId: "00000003-0000-4000-8000-000000000001",
              kind: "clause",
              definedTerm: null,
              parts: [{ kind: "literal", text: "  spaced\n  text  " }],
            },
          ],
        },
        { sectionKey: "empty", elements: [] },
      ],
      unmarked: [
        { sectionKey: "s", text: "inside & out", position: 1 },
        { sectionKey: null, text: "outside <the> sections", position: 2 },
      ],
    });
    const xml = writeMarkup(original);
    expect(xml).toContain("<unmarked>inside &amp; out</unmarked>");
    expect(xml).toContain("    <unmarked>outside &lt;the&gt; sections</unmarked>");
    expect(readMarkup(xml)).toEqual(original);
    expect(writeMarkup(readMarkup(xml))).toBe(xml);
  });

  it("keeps unmarked text between elements and between sections where it was", () => {
    const clause = (n: number) => ({
      elementId: `00000003-0000-4000-8000-00000000000${n}`,
      kind: "clause" as const,
      definedTerm: null,
      parts: [{ kind: "literal" as const, text: `c${n}` }],
    });
    const original = doc({
      sections: [
        { sectionKey: "a", elements: [clause(1), clause(2)] },
        { sectionKey: "b", elements: [clause(3)] },
      ],
      unmarked: [
        { sectionKey: null, text: "before all", position: 0 },
        { sectionKey: "a", text: "first", position: 0 },
        { sectionKey: "a", text: "between", position: 1 },
        { sectionKey: "a", text: "last", position: 2 },
        { sectionKey: null, text: "between sections", position: 1 },
        { sectionKey: null, text: "after all", position: 2 },
      ],
    });
    const xml = writeMarkup(original);
    const order = ["before all", "first", ">c1<", "between<", ">c2<", "last", "between sections", ">c3<", "after all"].map((needle) => xml.indexOf(needle));
    expect(order).toEqual([...order].sort((x, y) => x - y));
    expect(order).not.toContain(-1);
    const read = readMarkup(xml);
    expect(read.unmarked.slice().sort((x, y) => x.text.localeCompare(y.text))).toEqual(
      original.unmarked.slice().sort((x, y) => x.text.localeCompare(y.text)),
    );
    expect(writeMarkup(read)).toBe(xml);
  });

  it("puts unmarked text with no position last", () => {
    const xml = writeMarkup(doc({ sections: [{ sectionKey: "a", elements: [] }], unmarked: [{ sectionKey: "a", text: "t" }] }));
    expect(readMarkup(xml).unmarked).toEqual([{ sectionKey: "a", text: "t", position: 0 }]);
  });

  it("reads character references, CDATA and single-quoted attributes, and refuses a DOCTYPE", () => {
    const xml = writeMarkup(doc({ title: "x" })).replace("<title>x</title>", "<title><![CDATA[<x>]]>&#x41;&apos;</title>");
    expect(readMarkup(xml).title).toBe("<x>A'");
    expect(() => readMarkup('<!DOCTYPE d [<!ENTITY e "x">]>' + xml)).toThrow(/DOCTYPE/);
    expect(() => readMarkup("<document/>")).toThrow(/root/);
  });
});
