import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { parseBody, writePackage, writeSections, type WritableSection } from "./ooxml";
import { buildSnapshot } from "./snapshot";
import type { AuthoringTemplate, DocumentSnapshot } from "./types";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "../../../..");
const SAMPLES_DIR = path.join(REPO_ROOT, "contracts/authoring/samples");
const TEMPLATES_DIR = path.join(REPO_ROOT, "contracts/authoring/templates");

function load<T>(file: string): T {
  return JSON.parse(readFileSync(file, "utf-8")) as T;
}

// S8-02 --------------------------------------------------------------------------------------------

describe("round trip through writeSections, writePackage and parseBody (S8-02)", () => {
  for (const fileName of readdirSync(SAMPLES_DIR)) {
    const sampleId = fileName.replace(/\.json$/, "");

    it(`reproduces the ${sampleId} sample exactly`, () => {
      const sample = load<DocumentSnapshot>(path.join(SAMPLES_DIR, fileName));
      const template = load<AuthoringTemplate>(path.join(TEMPLATES_DIR, fileName));
      const headingBySectionKey = new Map(template.sections.map((section) => [section.sectionKey, section.heading]));
      const unmarkedBySectionKey = new Map<string, string[]>();
      for (const entry of sample.unmarked) {
        if (entry.sectionKey === null) {
          throw new Error("this test helper does not yet support a null-sectionKey unmarked entry");
        }
        const list = unmarkedBySectionKey.get(entry.sectionKey) ?? [];
        list.push(entry.text);
        unmarkedBySectionKey.set(entry.sectionKey, list);
      }

      const writable: WritableSection[] = sample.sections.map((section) => ({
        sectionKey: section.sectionKey,
        heading: headingBySectionKey.get(section.sectionKey) ?? section.sectionKey,
        elements: section.elements,
        unmarked: unmarkedBySectionKey.get(section.sectionKey) ?? [],
      }));

      const bodyXml = writeSections(writable);
      const packageXml = writePackage(bodyXml);
      const parsed = parseBody(packageXml);

      const { snapshot, warnings } = buildSnapshot(parsed, {
        documentId: sample.documentId,
        templateId: sample.templateId,
        title: sample.title,
        revision: null,
        variables: sample.variables,
      });

      expect(warnings).toEqual([]);
      expect(snapshot).toEqual(sample);
    });
  }
});

// S8-06 --------------------------------------------------------------------------------------------

describe("buildSnapshot: an undeclared variable (S8-06)", () => {
  it("adds the declaration as text, with a warning, and the snapshot still validates", () => {
    const xml =
      `<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" ` +
      `xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml">` +
      `<w:body>` +
      `<w:sdt><w:sdtPr><w:tag w:val="lat:s:commitment"/></w:sdtPr>` +
      `<w:sdtContent>` +
      `<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Commitment</w:t></w:r></w:p>` +
      `<w:sdt><w:sdtPr><w:tag w:val="lat:e:00000009-0000-4000-8000-000000000009"/></w:sdtPr>` +
      `<w:sdtContent><w:p>` +
      `<w:r><w:t xml:space="preserve">Pay </w:t></w:r>` +
      `<w:r><w:t xml:space="preserve">the sum of </w:t></w:r>` +
      `<w:sdt><w:sdtPr><w:tag w:val="lat:v:new-key"/></w:sdtPr>` +
      `<w:sdtContent><w:r><w:t>GBP 1</w:t></w:r></w:sdtContent></w:sdt>` +
      `<w:r><w:t>.</w:t></w:r>` +
      `</w:p></w:sdtContent></w:sdt>` +
      `</w:sdtContent></w:sdt>` +
      `</w:body></w:document>`;

    const parsed = parseBody(xml);
    expect(parsed.sections[0].elements[0].parts).toEqual([
      { kind: "literal", text: "Pay the sum of " },
      { kind: "variable", variableKey: "new-key", text: "GBP 1" },
      { kind: "literal", text: "." },
    ]);

    const { snapshot, warnings } = buildSnapshot(parsed, {
      documentId: "00000009-0000-4000-8000-000000000000",
      templateId: "facility-agreement",
      title: "t",
      revision: null,
      variables: [],
    });

    expect(snapshot.variables).toEqual([{ variableKey: "new-key", label: "new-key", valueType: "text" }]);
    expect(warnings.some((warning) => warning.includes("new-key"))).toBe(true);
  });
});
