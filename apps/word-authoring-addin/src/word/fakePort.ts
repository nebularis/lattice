/**
 * A `DocumentPort` over an in-memory model, for Vitest and the Playwright harness (plan WA9
 * section "Files"). No Office.js dependency.
 */
import { parseBody, writePackage, writeSections, type WritableSection } from "../domain/ooxml";
import type { DocumentElement, Part } from "../domain/types";
import type { AuthoringMetadata, DocumentPort, InlineMark, MarkResult } from "./port";

const W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main";

interface FakeSection {
  heading: string;
  elements: DocumentElement[];
}

interface FakeSelection {
  elementId: string;
  start: number;
  end: number;
}

interface FakeUnmarkedSelection {
  sectionKey: string;
  text: string;
}

/** Extracts each section's `Heading1` paragraph text directly from a flat-OPC package, since the
 * parsed model (by design) drops it. A small amount of duplicated DOM-walking versus
 * `domain/ooxml.ts`, acceptable in a test double. */
function extractHeadings(packageXml: string): Map<string, string> {
  const headings = new Map<string, string>();
  const doc = new DOMParser().parseFromString(packageXml, "application/xml");
  const sdts = doc.getElementsByTagNameNS(W_NS, "sdt");
  for (const sdt of Array.from(sdts)) {
    const sdtPr = Array.from(sdt.childNodes).find(
      (node): node is Element => node.nodeType === 1 && (node as Element).localName === "sdtPr",
    );
    const tagEl = sdtPr
      ? Array.from(sdtPr.childNodes).find((node): node is Element => node.nodeType === 1 && (node as Element).localName === "tag")
      : undefined;
    const tagValue = tagEl?.getAttributeNS(W_NS, "val") ?? "";
    if (!tagValue.startsWith("lat:s:")) continue;
    const sectionKey = tagValue.slice("lat:s:".length);
    const firstParagraph = sdt.getElementsByTagNameNS(W_NS, "p")[0];
    if (firstParagraph) {
      headings.set(sectionKey, firstParagraph.textContent ?? "");
    }
  }
  return headings;
}

function locatePart(element: DocumentElement, start: number, end: number): { index: number; localStart: number; localEnd: number } | null {
  let offset = 0;
  for (let index = 0; index < element.parts.length; index += 1) {
    const part = element.parts[index];
    const partStart = offset;
    const partEnd = offset + part.text.length;
    if (start >= partStart && end <= partEnd) {
      return { index, localStart: start - partStart, localEnd: end - partStart };
    }
    offset = partEnd;
  }
  return null;
}

export class FakeWordPort implements DocumentPort {
  private readonly sections = new Map<string, FakeSection>();
  private readonly sectionOrder: string[] = [];
  private metadata: AuthoringMetadata | null = null;
  private selection: FakeSelection | null = null;
  private unmarkedSelection: FakeUnmarkedSelection | null = null;

  async readBodyOoxml(): Promise<string> {
    const writable: WritableSection[] = this.sectionOrder.map((sectionKey) => {
      const section = this.sections.get(sectionKey)!;
      return { sectionKey, heading: section.heading, elements: section.elements };
    });
    return writePackage(writeSections(writable));
  }

  async readMetadata(): Promise<AuthoringMetadata | null> {
    return this.metadata;
  }

  async writeMetadata(metadata: AuthoringMetadata): Promise<void> {
    this.metadata = metadata;
  }

  async insertOoxml(packageXml: string): Promise<void> {
    const parsed = parseBody(packageXml);
    const headings = extractHeadings(packageXml);
    for (const section of parsed.sections) {
      if (!this.sections.has(section.sectionKey)) {
        this.sectionOrder.push(section.sectionKey);
      }
      const heading = headings.get(section.sectionKey) ?? section.sectionKey;
      this.sections.set(section.sectionKey, { heading, elements: [...section.elements] });
    }
  }

  /** Harness-only: sets the simulated selection, in element-text offsets (plan WA9). */
  select(elementId: string, start: number, end: number): void {
    this.selection = { elementId, start, end };
    this.unmarkedSelection = null;
  }

  /** Harness-only: simulates selecting unmarked text within a section, for
   * `wrapSelectionAsElement` (plan WA9a). */
  selectUnmarked(sectionKey: string, text: string): void {
    this.unmarkedSelection = { sectionKey, text };
    this.selection = null;
  }

  /** Harness-only: the current in-memory model, as `ParsedDocument`-shaped sections. */
  model(): { sections: { sectionKey: string; heading: string; elements: DocumentElement[] }[] } {
    return {
      sections: this.sectionOrder.map((sectionKey) => ({ sectionKey, ...this.sections.get(sectionKey)! })),
    };
  }

  private findElement(elementId: string): DocumentElement | null {
    for (const sectionKey of this.sectionOrder) {
      const section = this.sections.get(sectionKey)!;
      const found = section.elements.find((element) => element.elementId === elementId);
      if (found) return found;
    }
    return null;
  }

  async readSelection(): Promise<{ text: string; elementId: string | null }> {
    if (!this.selection) {
      return { text: "", elementId: null };
    }
    const element = this.findElement(this.selection.elementId);
    if (!element) {
      return { text: "", elementId: null };
    }
    const text = element.parts.map((part) => part.text).join("").slice(this.selection.start, this.selection.end);
    return { text, elementId: this.selection.elementId };
  }

  async wrapSelectionAsElement(kind: "clause" | "definition", elementId: string): Promise<MarkResult> {
    if (!this.unmarkedSelection) {
      return { ok: false, reason: "outside-section" };
    }
    const section = this.sections.get(this.unmarkedSelection.sectionKey);
    if (!section) {
      return { ok: false, reason: "outside-section" };
    }
    const element: DocumentElement = {
      elementId,
      kind,
      definedTerm: null,
      parts: [{ kind: "literal", text: this.unmarkedSelection.text }],
    };
    section.elements.push(element);
    this.unmarkedSelection = null;
    return { ok: true };
  }

  async markSelection(mark: InlineMark): Promise<MarkResult> {
    if (!this.selection) {
      return { ok: false, reason: "no-selection" };
    }
    const element = this.findElement(this.selection.elementId);
    if (!element) {
      return { ok: false, reason: "outside-element" };
    }
    return this.applyMark(element, this.selection.start, this.selection.end, mark);
  }

  async markOccurrence(elementId: string, text: string, occurrence: number, mark: InlineMark): Promise<boolean> {
    const element = this.findElement(elementId);
    if (!element) return false;
    const elementText = element.parts.map((part) => part.text).join("");
    let from = 0;
    let found = -1;
    for (let count = 0; count <= occurrence; count += 1) {
      found = elementText.indexOf(text, from);
      if (found === -1) return false;
      from = found + 1;
    }
    const result = this.applyMark(element, found, found + text.length, mark);
    return result.ok;
  }

  private applyMark(element: DocumentElement, start: number, end: number, mark: InlineMark): MarkResult {
    const located = locatePart(element, start, end);
    if (!located) {
      return { ok: false, reason: "spans-parts" };
    }
    const part = element.parts[located.index];
    if (part.kind !== "literal") {
      return { ok: false, reason: "already-marked" };
    }
    const before = part.text.slice(0, located.localStart);
    const marked = part.text.slice(located.localStart, located.localEnd);
    const after = part.text.slice(located.localEnd);

    if (mark.kind === "term") {
      element.definedTerm = marked;
      return { ok: true };
    }

    const replacement: Part =
      mark.kind === "variable"
        ? { kind: "variable", variableKey: mark.variableKey, text: marked }
        : { kind: "reference", targetElementId: mark.targetElementId, text: marked };

    const newParts: Part[] = [];
    if (before.length > 0) newParts.push({ kind: "literal", text: before });
    newParts.push(replacement);
    if (after.length > 0) newParts.push({ kind: "literal", text: after });

    element.parts.splice(located.index, 1, ...newParts);
    return { ok: true };
  }

  async unmarkSelection(): Promise<MarkResult> {
    if (!this.selection) {
      return { ok: false, reason: "no-selection" };
    }
    const element = this.findElement(this.selection.elementId);
    if (!element) {
      return { ok: false, reason: "outside-element" };
    }
    const located = locatePart(element, this.selection.start, this.selection.end);
    if (!located) {
      return { ok: false, reason: "spans-parts" };
    }
    const part = element.parts[located.index];
    if (part.kind === "literal") {
      return { ok: false, reason: "outside-element" };
    }
    element.parts.splice(located.index, 1, { kind: "literal", text: part.text });
    return { ok: true };
  }
}
