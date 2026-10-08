/**
 * Parses and writes the `w:body` of a Word document into/from the LATTICE element model (plan
 * WA8 section "OOXML rules"). `parseBody` accepts a flat-OPC package (what
 * `document.body.getOoxml()` returns) or a bare `w:document` root. `writeSections` and
 * `writeTemplate` produce body XML; `writePackage` wraps it as a flat-OPC package suitable for
 * `insertOoxml`.
 */
import { decode, encode, title, TAG_APPEARANCE, TAG_COLOUR, type TagKind } from "./tags";
import type { DocumentElement, ElementKind, Part, Section, Unmarked } from "./types";
import { newUuid } from "./uuid";
import { escapeXml, parseXmlDocument } from "./xml";

const W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main";
const PKG_NS = "http://schemas.microsoft.com/office/2006/xmlPackage";

const SKIPPED_RUN_CHILDREN = new Set([
  "del",
  "delText",
  "instrText",
  "rPr",
  "pPr",
  "proofErr",
  "bookmarkStart",
  "bookmarkEnd",
  "commentRangeStart",
  "commentRangeEnd",
  "footnoteReference",
]);

const DESCEND_RUN_CHILDREN = new Set(["hyperlink", "ins", "smartTag", "fldSimple", "customXml", "r"]);

export interface ParsedDocument {
  sections: Section[];
  unmarked: Unmarked[];
  warnings: string[];
}

export interface WritableSection {
  sectionKey: string;
  heading: string;
  elements: DocumentElement[];
  /** Plain paragraphs to write after the elements, read back as `Unmarked` entries for this
   * section. Defaults to none. */
  unmarked?: string[];
}

// --- parsing -------------------------------------------------------------------------------------

function isElement(node: Node): node is Element {
  return node.nodeType === 1;
}

function wChildren(parent: Element, localName: string): Element[] {
  const result: Element[] = [];
  for (const child of Array.from(parent.childNodes)) {
    if (isElement(child) && child.namespaceURI === W_NS && child.localName === localName) {
      result.push(child);
    }
  }
  return result;
}

function wChild(parent: Element, localName: string): Element | null {
  return wChildren(parent, localName)[0] ?? null;
}

function sdtTag(sdtEl: Element): string | null {
  const sdtPr = wChild(sdtEl, "sdtPr");
  if (!sdtPr) return null;
  const tagEl = wChild(sdtPr, "tag");
  if (!tagEl) return null;
  return tagEl.getAttributeNS(W_NS, "val");
}

function sdtContentOf(sdtEl: Element): Element | null {
  return wChild(sdtEl, "sdtContent");
}

function pStyleStartsWithHeading(paragraph: Element): boolean {
  const pPr = wChild(paragraph, "pPr");
  const pStyle = pPr ? wChild(pPr, "pStyle") : null;
  const value = pStyle?.getAttributeNS(W_NS, "val") ?? "";
  return value.startsWith("Heading");
}

function getDocumentElement(ooxml: string): Element {
  const doc = parseXmlDocument(ooxml);
  const root = doc.documentElement;
  if (root.namespaceURI === W_NS && root.localName === "document") {
    return root;
  }
  const parts = root.getElementsByTagNameNS(PKG_NS, "part");
  for (const part of Array.from(parts)) {
    if (part.getAttributeNS(PKG_NS, "name") === "/word/document.xml") {
      const xmlData = part.getElementsByTagNameNS(PKG_NS, "xmlData")[0];
      if (xmlData) {
        for (const child of Array.from(xmlData.childNodes)) {
          if (isElement(child) && child.namespaceURI === W_NS && child.localName === "document") {
            return child;
          }
        }
      }
    }
  }
  throw new Error("no w:document found: neither a bare root nor a pkg:part named '/word/document.xml'");
}

/** Reads the run-level text of `node` (plan WA8 "OOXML rules"). Used both for an unmarked
 * paragraph's text and for an inline marker's displayed text; a nested inline content control is
 * read as literal text, with a warning, since only one level of inline marker is meaningful. */
function readRunText(node: Element, warnings: string[], context: string): string {
  let text = "";
  for (const child of Array.from(node.childNodes)) {
    if (!isElement(child)) continue;
    if (child.namespaceURI !== W_NS) continue;
    const name = child.localName;
    if (name === "t") {
      text += child.textContent ?? "";
    } else if (name === "tab") {
      text += "\t";
    } else if (name === "br" || name === "cr") {
      text += "\n";
    } else if (name === "noBreakHyphen") {
      text += "\u2011";
    } else if (DESCEND_RUN_CHILDREN.has(name)) {
      text += readRunText(child, warnings, context);
    } else if (name === "sdt") {
      warnings.push(`${context}: a nested content control is read as literal text`);
      const content = sdtContentOf(child);
      if (content) text += readRunText(content, warnings, context);
    } else if (SKIPPED_RUN_CHILDREN.has(name)) {
      // skip
    } else {
      text += readRunText(child, warnings, context);
    }
  }
  return text;
}

type Atom =
  | { type: "text"; value: string; isTerm?: boolean }
  | { type: "variable"; text: string; variableKey: string }
  | { type: "reference"; text: string; targetElementId: string };

function walkElementContent(node: Element, atoms: Atom[], warnings: string[], context: string): void {
  for (const child of Array.from(node.childNodes)) {
    if (!isElement(child)) continue;
    if (child.namespaceURI !== W_NS) continue;
    const name = child.localName;
    if (name === "t") {
      atoms.push({ type: "text", value: child.textContent ?? "" });
    } else if (name === "tab") {
      atoms.push({ type: "text", value: "\t" });
    } else if (name === "br" || name === "cr") {
      atoms.push({ type: "text", value: "\n" });
    } else if (name === "noBreakHyphen") {
      atoms.push({ type: "text", value: "\u2011" });
    } else if (DESCEND_RUN_CHILDREN.has(name)) {
      walkElementContent(child, atoms, warnings, context);
    } else if (name === "sdt") {
      const tag = sdtTag(child);
      const decoded = tag ? decode(tag) : null;
      const content = sdtContentOf(child);
      if (decoded?.kind === "variable" && decoded.value) {
        const text = content ? readRunText(content, warnings, context) : "";
        atoms.push({ type: "variable", text, variableKey: decoded.value });
      } else if (decoded?.kind === "reference" && decoded.value) {
        const text = content ? readRunText(content, warnings, context) : "";
        atoms.push({ type: "reference", text, targetElementId: decoded.value });
      } else if (decoded?.kind === "term") {
        const text = content ? readRunText(content, warnings, context) : "";
        atoms.push({ type: "text", value: text, isTerm: true });
      } else if (content) {
        walkElementContent(content, atoms, warnings, context);
      }
    } else if (SKIPPED_RUN_CHILDREN.has(name)) {
      // skip
    } else {
      walkElementContent(child, atoms, warnings, context);
    }
  }
}

function atomsToParts(atoms: Atom[]): { parts: Part[]; definedTerm: string | null } {
  const parts: Part[] = [];
  let definedTerm: string | null = null;
  let buffer = "";
  const flush = () => {
    if (buffer.length > 0) {
      parts.push({ kind: "literal", text: buffer });
    }
    buffer = "";
  };
  for (const atom of atoms) {
    if (atom.type === "text") {
      if (atom.isTerm && definedTerm === null) {
        definedTerm = atom.value;
      }
      buffer += atom.value;
    } else if (atom.type === "variable") {
      flush();
      parts.push({ kind: "variable", variableKey: atom.variableKey, text: atom.text });
    } else {
      flush();
      parts.push({ kind: "reference", targetElementId: atom.targetElementId, text: atom.text });
    }
  }
  flush();
  return { parts, definedTerm };
}

function parseElement(
  sdtEl: Element,
  kind: ElementKind,
  elementId: string,
  warnings: string[],
): DocumentElement | null {
  const content = sdtContentOf(sdtEl);
  const atoms: Atom[] = [];
  let sawFirstParagraph = false;
  if (content) {
    for (const paragraph of wChildren(content, "p")) {
      if (sawFirstParagraph) {
        atoms.push({ type: "text", value: "\n" });
      }
      sawFirstParagraph = true;
      walkElementContent(paragraph, atoms, warnings, `element ${elementId}`);
    }
  }
  const { parts, definedTerm } = atomsToParts(atoms);
  if (parts.length === 0) {
    warnings.push(`element ${elementId} had no parts after parsing and was dropped`);
    return null;
  }
  return { elementId, kind, definedTerm: kind === "definition" ? definedTerm : null, parts };
}

function parseSection(
  sdtEl: Element,
  sectionKey: string,
  warnings: string[],
): { section: Section; unmarked: Unmarked[] } {
  const content = sdtContentOf(sdtEl);
  const elements: DocumentElement[] = [];
  const unmarked: Unmarked[] = [];
  let headingConsumed = false;
  if (content) {
    for (const child of Array.from(content.childNodes)) {
      if (!isElement(child) || child.namespaceURI !== W_NS) continue;
      if (child.localName === "p") {
        if (!headingConsumed && pStyleStartsWithHeading(child)) {
          headingConsumed = true;
          continue;
        }
        const text = readRunText(child, warnings, `section ${sectionKey}`).trim();
        if (text.length > 0) {
          unmarked.push({ sectionKey, text });
        }
        continue;
      }
      if (child.localName === "sdt") {
        const tag = sdtTag(child);
        const decoded = tag ? decode(tag) : null;
        if (decoded && (decoded.kind === "clause" || decoded.kind === "definition") && decoded.value) {
          const element = parseElement(child, decoded.kind, decoded.value, warnings);
          if (element) elements.push(element);
        }
      }
    }
  }
  return { section: { sectionKey, elements }, unmarked };
}

export function parseBody(ooxml: string): ParsedDocument {
  const documentEl = getDocumentElement(ooxml);
  const body = wChild(documentEl, "body");
  if (!body) {
    throw new Error("no w:body found in the document");
  }
  const warnings: string[] = [];
  const sections: Section[] = [];
  const unmarked: Unmarked[] = [];

  for (const child of Array.from(body.childNodes)) {
    if (!isElement(child) || child.namespaceURI !== W_NS) continue;
    if (child.localName === "sdt") {
      const tag = sdtTag(child);
      const decoded = tag ? decode(tag) : null;
      if (decoded?.kind === "section" && decoded.value) {
        const result = parseSection(child, decoded.value, warnings);
        sections.push(result.section);
        unmarked.push(...result.unmarked);
      }
      continue;
    }
    if (child.localName === "p") {
      const text = readRunText(child, warnings, "document").trim();
      if (text.length > 0) {
        unmarked.push({ sectionKey: null, text });
      }
    }
  }

  return { sections, unmarked, warnings };
}

// --- writing ---------------------------------------------------------------------------------

let nextIdCounter = 1000000001;

function nextId(): number {
  return nextIdCounter++;
}

function appearanceValue(kind: TagKind): string {
  return TAG_APPEARANCE[kind] === "BoundingBox" ? "boundingBox" : "tags";
}

function colourValue(kind: TagKind): string {
  return TAG_COLOUR[kind].replace("#", "");
}

function writeBlockSdt(kind: TagKind, value: string, titleText: string, innerXml: string): string {
  const tag = encode(kind, value);
  return (
    `<w:sdt><w:sdtPr>` +
    `<w:alias w:val="${escapeXml(titleText)}"/>` +
    `<w:tag w:val="${escapeXml(tag)}"/>` +
    `<w:id w:val="${nextId()}"/>` +
    `<w15:color w:val="${colourValue(kind)}"/>` +
    `<w15:appearance w:val="${appearanceValue(kind)}"/>` +
    `</w:sdtPr><w:sdtContent>${innerXml}</w:sdtContent></w:sdt>`
  );
}

function writeInlineSdt(kind: TagKind, value: string | undefined, text: string): string {
  const tag = encode(kind, value);
  const titleText = title(kind, text);
  return (
    `<w:sdt><w:sdtPr>` +
    `<w:alias w:val="${escapeXml(titleText)}"/>` +
    `<w:tag w:val="${escapeXml(tag)}"/>` +
    `<w:id w:val="${nextId()}"/>` +
    `<w15:color w:val="${colourValue(kind)}"/>` +
    `<w15:appearance w:val="${appearanceValue(kind)}"/>` +
    `</w:sdtPr><w:sdtContent><w:r><w:t xml:space="preserve">${escapeXml(text)}</w:t></w:r></w:sdtContent></w:sdt>`
  );
}

type WriteToken =
  | { type: "para-break" }
  | { type: "literal"; text: string }
  | { type: "term"; text: string }
  | { type: "variable"; variableKey: string; text: string }
  | { type: "reference"; targetElementId: string; text: string };

function tokensFor(parts: Part[], definedTerm: string | null): WriteToken[] {
  const tokens: WriteToken[] = [];
  let termWritten = false;
  for (const part of parts) {
    if (part.kind === "literal") {
      const segments = part.text.split("\n");
      segments.forEach((segment, index) => {
        if (index > 0) tokens.push({ type: "para-break" });
        if (segment.length === 0) return;
        if (!termWritten && definedTerm && definedTerm.length > 0) {
          const at = segment.indexOf(definedTerm);
          if (at >= 0) {
            if (at > 0) tokens.push({ type: "literal", text: segment.slice(0, at) });
            tokens.push({ type: "term", text: definedTerm });
            termWritten = true;
            const rest = segment.slice(at + definedTerm.length);
            if (rest.length > 0) tokens.push({ type: "literal", text: rest });
            return;
          }
        }
        tokens.push({ type: "literal", text: segment });
      });
    } else if (part.kind === "variable") {
      tokens.push({ type: "variable", variableKey: part.variableKey, text: part.text });
    } else {
      tokens.push({ type: "reference", targetElementId: part.targetElementId, text: part.text });
    }
  }
  return tokens;
}

function splitIntoParagraphs(tokens: WriteToken[]): Exclude<WriteToken, { type: "para-break" }>[][] {
  const paragraphs: Exclude<WriteToken, { type: "para-break" }>[][] = [[]];
  for (const token of tokens) {
    if (token.type === "para-break") {
      paragraphs.push([]);
    } else {
      paragraphs[paragraphs.length - 1].push(token);
    }
  }
  return paragraphs;
}

function writeParagraphXml(tokens: Exclude<WriteToken, { type: "para-break" }>[]): string {
  const runsXml = tokens
    .map((token) => {
      if (token.type === "literal") {
        return `<w:r><w:t xml:space="preserve">${escapeXml(token.text)}</w:t></w:r>`;
      }
      if (token.type === "term") {
        return writeInlineSdt("term", undefined, token.text);
      }
      if (token.type === "variable") {
        return writeInlineSdt("variable", token.variableKey, token.text);
      }
      return writeInlineSdt("reference", token.targetElementId, token.text);
    })
    .join("");
  return `<w:p>${runsXml}</w:p>`;
}

function writeHeadingXml(heading: string): string {
  return (
    `<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr>` +
    `<w:r><w:t xml:space="preserve">${escapeXml(heading)}</w:t></w:r></w:p>`
  );
}

function writeElementXml(element: DocumentElement): string {
  const tokens = tokensFor(element.parts, element.definedTerm);
  const paragraphs = splitIntoParagraphs(tokens);
  const paragraphsXml = paragraphs.map(writeParagraphXml).join("");
  return writeBlockSdt(element.kind, element.elementId, title(element.kind), paragraphsXml || "<w:p/>");
}

function writeSectionXml(section: WritableSection): string {
  const elementsXml = section.elements.map(writeElementXml).join("");
  const unmarkedXml = (section.unmarked ?? [])
    .map((text) => `<w:p><w:r><w:t xml:space="preserve">${escapeXml(text)}</w:t></w:r></w:p>`)
    .join("");
  return writeBlockSdt(
    "section",
    section.sectionKey,
    title("section", section.heading),
    writeHeadingXml(section.heading) + elementsXml + unmarkedXml,
  );
}

/** Writes a list of sections (with their headings and elements) as `w:body` content. */
export function writeSections(sections: WritableSection[]): string {
  nextIdCounter = 1000000001;
  return sections.map(writeSectionXml).join("");
}

function newTemplateElementId(): string {
  return newUuid();
}

interface WritableTemplate {
  sections: { sectionKey: string; heading: string; elementKinds: ElementKind[] }[];
}

/** Writes an empty document from a template: per section, the heading and one placeholder
 * element of the section's first admitted element kind, each with a fresh element id. The
 * element's paragraph carries a single space, not truly empty text: an empty paragraph has zero
 * parts once parsed back, and "empty literals are dropped" (plan WA8 OOXML rules) would silently
 * lose the element the author is meant to fill in; a single space is schema-valid (`LiteralPart`
 * requires at least one character) and survives the round trip as one element with one part. */
export function writeTemplate(template: WritableTemplate): string {
  nextIdCounter = 1000000001;
  return template.sections
    .map((section) => {
      const kind = section.elementKinds[0];
      const elementId = newTemplateElementId();
      const placeholderParagraph = `<w:p><w:r><w:t xml:space="preserve"> </w:t></w:r></w:p>`;
      const elementXml = writeBlockSdt(kind, elementId, title(kind), placeholderParagraph);
      return writeBlockSdt(
        "section",
        section.sectionKey,
        title("section", section.heading),
        writeHeadingXml(section.heading) + elementXml,
      );
    })
    .join("");
}

/** Wraps `bodyXml` (the output of `writeSections`/`writeTemplate`) as a flat-OPC package with the
 * `/_rels/.rels` and `/word/document.xml` parts, ready for `DocumentPort.insertOoxml`. */
export function writePackage(bodyXml: string): string {
  return (
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
    `<pkg:package xmlns:pkg="${PKG_NS}">` +
    `<pkg:part pkg:name="/_rels/.rels" pkg:contentType="application/vnd.openxmlformats-package.relationships+xml">` +
    `<pkg:xmlData>` +
    `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">` +
    `<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>` +
    `</Relationships>` +
    `</pkg:xmlData>` +
    `</pkg:part>` +
    `<pkg:part pkg:name="/word/document.xml" pkg:contentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml">` +
    `<pkg:xmlData>` +
    `<w:document xmlns:w="${W_NS}" xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml">` +
    `<w:body>${bodyXml}<w:sectPr/></w:body>` +
    `</w:document>` +
    `</pkg:xmlData>` +
    `</pkg:part>` +
    `</pkg:package>`
  );
}
