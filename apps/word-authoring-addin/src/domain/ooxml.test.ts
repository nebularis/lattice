import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { parseBody } from "./ooxml";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function wrapBareDocument(bodyXml: string): string {
  return (
    `<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" ` +
    `xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml">` +
    `<w:body>${bodyXml}</w:body></w:document>`
  );
}

// S8-03 ------------------------------------------------------------------------------------------

describe("parseBody against a hand-written Word-style fixture (S8-03)", () => {
  it("reads the expected model, ignoring tracked changes, bookmarks and proof marks", () => {
    const xml = readFileSync(path.join(__dirname, "fixtures", "word-like-facility.xml"), "utf-8");
    const expected = JSON.parse(readFileSync(path.join(__dirname, "fixtures", "word-like-facility.expected.json"), "utf-8"));

    const parsed = parseBody(xml);

    expect(parsed).toEqual(expected);
  });

  it("would fail if w:delText were read (self-probe target)", () => {
    const xml = readFileSync(path.join(__dirname, "fixtures", "word-like-facility.xml"), "utf-8");
    const parsed = parseBody(xml);
    const text = parsed.sections[0].elements[0].parts.map((part) => part.text).join("");
    expect(text).not.toContain("won't");
  });
});

// S8-04 --------------------------------------------------------------------------------------------

describe("parseBody: unmarked text and the zero-parts case (S8-04)", () => {
  it("collects unmarked paragraphs both inside and outside a section, and drops an empty element with a warning", () => {
    const xml = wrapBareDocument(
      `<w:p><w:r><w:t>Preamble text.</w:t></w:r></w:p>` +
        `<w:sdt><w:sdtPr><w:tag w:val="lat:s:definitions"/></w:sdtPr>` +
        `<w:sdtContent>` +
        `<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Definitions</w:t></w:r></w:p>` +
        `<w:p><w:r><w:t>Note: see the schedule.</w:t></w:r></w:p>` +
        `<w:sdt><w:sdtPr><w:tag w:val="lat:d:00000009-0000-4000-8000-000000000005"/></w:sdtPr>` +
        `<w:sdtContent><w:p/></w:sdtContent></w:sdt>` +
        `</w:sdtContent></w:sdt>`,
    );

    const parsed = parseBody(xml);

    expect(parsed.unmarked).toEqual([
      { sectionKey: null, text: "Preamble text." },
      { sectionKey: "definitions", text: "Note: see the schedule." },
    ]);
    expect(parsed.sections).toEqual([{ sectionKey: "definitions", elements: [] }]);
    expect(parsed.warnings.some((warning) => warning.includes("00000009-0000-4000-8000-000000000005"))).toBe(true);
  });
});

// S8-05 --------------------------------------------------------------------------------------------

describe("parseBody: an inline marker nested inside another (S8-05)", () => {
  it("reads the nested variable as literal text within the reference, with a warning", () => {
    const xml = wrapBareDocument(
      `<w:sdt><w:sdtPr><w:tag w:val="lat:s:definitions"/></w:sdtPr>` +
        `<w:sdtContent>` +
        `<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Definitions</w:t></w:r></w:p>` +
        `<w:sdt><w:sdtPr><w:tag w:val="lat:d:00000009-0000-4000-8000-000000000006"/></w:sdtPr>` +
        `<w:sdtContent><w:p>` +
        `<w:sdt><w:sdtPr><w:tag w:val="lat:r:00000009-0000-4000-8000-000000000007"/></w:sdtPr>` +
        `<w:sdtContent>` +
        `<w:r><w:t xml:space="preserve">outer </w:t></w:r>` +
        `<w:sdt><w:sdtPr><w:tag w:val="lat:v:some-key"/></w:sdtPr>` +
        `<w:sdtContent><w:r><w:t>inner</w:t></w:r></w:sdtContent></w:sdt>` +
        `</w:sdtContent></w:sdt>` +
        `</w:p></w:sdtContent></w:sdt>` +
        `</w:sdtContent></w:sdt>`,
    );

    const parsed = parseBody(xml);

    const element = parsed.sections[0].elements[0];
    expect(element.parts).toEqual([
      { kind: "reference", targetElementId: "00000009-0000-4000-8000-000000000007", text: "outer inner" },
    ]);
    expect(parsed.warnings.some((warning) => warning.includes("literal text"))).toBe(true);
  });
});

// Adjacent literal runs merge (used again, more fully, by S8-06 in snapshot.test.ts) --------------

describe("parseBody: adjacent literal runs", () => {
  it("merges two adjacent literal runs into one literal part", () => {
    const xml = wrapBareDocument(
      `<w:sdt><w:sdtPr><w:tag w:val="lat:s:commitment"/></w:sdtPr>` +
        `<w:sdtContent>` +
        `<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Commitment</w:t></w:r></w:p>` +
        `<w:sdt><w:sdtPr><w:tag w:val="lat:e:00000009-0000-4000-8000-000000000008"/></w:sdtPr>` +
        `<w:sdtContent><w:p>` +
        `<w:r><w:t xml:space="preserve">Pay </w:t></w:r>` +
        `<w:r><w:t>the sum.</w:t></w:r>` +
        `</w:p></w:sdtContent></w:sdt>` +
        `</w:sdtContent></w:sdt>`,
    );

    const parsed = parseBody(xml);

    expect(parsed.sections[0].elements[0].parts).toEqual([{ kind: "literal", text: "Pay the sum." }]);
  });
});
