// SPDX-License-Identifier: MPL-2.0
// The document model as LATTICE's document markup (ADR-A137, contracts/document/document.rnc),
// written and read without a DOM, so it runs in a browser, in Node and in a test alike.
//
// A clause or definition is mixed content and is read exactly, so the writer puts no whitespace
// inside one, and the reader keeps every character of it. Each run of text between marks is one
// literal part.
//
// ponytail: the model keeps unmarked text apart from the elements, so the writer puts a section's
// unmarked text after its elements and the document's unmarked text after its sections, and the
// order of unmarked text among elements is not kept. Add a position to Unmarked if that matters.

import type { DocumentElement, DocumentSnapshot, Part, Section, Unmarked, ValueType, VariableDeclaration } from "./types";

export const MARKUP_NAMESPACE = "https://www.nebularis.org/neuro-semantic/lattice/document/1";

// --- writing -----------------------------------------------------------------------------------

function escapeText(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\r/g, "&#13;");
}

function escapeAttribute(text: string): string {
  return escapeText(text).replace(/"/g, "&quot;").replace(/\n/g, "&#10;").replace(/\t/g, "&#9;");
}

function mergeLiterals(parts: Part[]): Part[] {
  const merged: Part[] = [];
  for (const part of parts) {
    const last = merged[merged.length - 1];
    if (part.kind === "literal") {
      if (part.text === "") continue;
      if (last?.kind === "literal") {
        merged[merged.length - 1] = { kind: "literal", text: last.text + part.text };
        continue;
      }
    }
    merged.push(part);
  }
  return merged;
}

function writePart(part: Part): string {
  switch (part.kind) {
    case "literal":
      return escapeText(part.text);
    case "variable":
      return `<var key="${escapeAttribute(part.variableKey)}">${escapeText(part.text)}</var>`;
    case "reference":
      return `<ref target="${escapeAttribute(part.targetElementId)}">${escapeText(part.text)}</ref>`;
  }
}

function writeElement(element: DocumentElement, indent: string): string {
  const content = mergeLiterals(element.parts).map(writePart).join("");
  const id = `id="${escapeAttribute(element.elementId)}"`;
  const open =
    element.kind === "definition" ? `<definition ${id} term="${escapeAttribute(element.definedTerm ?? "")}">` : `<clause ${id}>`;
  return `${indent}${open}${content}</${element.kind}>`;
}

function writeUnmarked(entry: Unmarked, indent: string): string {
  return `${indent}<unmarked>${escapeText(entry.text)}</unmarked>`;
}

function writeSection(section: Section, unmarked: Unmarked[]): string {
  const children = [
    ...section.elements.map((element) => writeElement(element, "      ")),
    ...unmarked.map((entry) => writeUnmarked(entry, "      ")),
  ];
  const open = `<section key="${escapeAttribute(section.sectionKey)}">`;
  return children.length === 0 ? `    ${open}</section>` : `    ${open}\n${children.join("\n")}\n    </section>`;
}

function writeVariable(variable: VariableDeclaration): string {
  return `    <variable key="${escapeAttribute(variable.variableKey)}" type="${escapeAttribute(variable.valueType)}">${escapeText(variable.label)}</variable>`;
}

/** The document as markup, valid against `contracts/document/document.rnc` where the model is. */
export function writeMarkup(document: DocumentSnapshot): string {
  const bodyChildren = [
    ...document.sections.map((section) =>
      writeSection(
        section,
        document.unmarked.filter((entry) => entry.sectionKey === section.sectionKey),
      ),
    ),
    ...document.unmarked.filter((entry) => entry.sectionKey === null).map((entry) => writeUnmarked(entry, "    ")),
  ];
  const meta = [
    `    <title>${escapeText(document.title)}</title>`,
    `    <template>${escapeText(document.templateId)}</template>`,
    ...document.variables.map(writeVariable),
  ];
  return (
    `<?xml version="1.0" encoding="UTF-8"?>\n` +
    `<document xmlns="${MARKUP_NAMESPACE}" id="${escapeAttribute(document.documentId)}">\n` +
    `  <meta>\n${meta.join("\n")}\n  </meta>\n` +
    (bodyChildren.length === 0 ? `  <body></body>\n` : `  <body>\n${bodyChildren.join("\n")}\n  </body>\n`) +
    `</document>\n`
  );
}

// --- reading -----------------------------------------------------------------------------------

interface XmlElement {
  name: string;
  attributes: Record<string, string>;
  children: (XmlElement | string)[];
}

const ENTITIES: Record<string, string> = { lt: "<", gt: ">", amp: "&", quot: '"', apos: "'" };

function decodeEntities(text: string): string {
  return text.replace(/&(#x[0-9a-fA-F]+|#[0-9]+|[a-z]+);/g, (whole, name: string) => {
    if (name[0] === "#") {
      const code = name[1] === "x" ? parseInt(name.slice(2), 16) : parseInt(name.slice(1), 10);
      if (!Number.isInteger(code) || code > 0x10ffff) throw new Error(`invalid markup: bad character reference ${whole}`);
      return String.fromCodePoint(code);
    }
    const value = ENTITIES[name];
    if (value === undefined) throw new Error(`invalid markup: unknown entity ${whole}`);
    return value;
  });
}

/** A parser for the markup's subset of XML. A DOCTYPE is refused, as the service refuses a DTD. */
function parseXml(source: string): XmlElement {
  let pos = 0;
  const fail = (message: string): never => {
    throw new Error(`invalid markup: ${message} at offset ${pos}`);
  };
  const skipPast = (end: string): void => {
    const at = source.indexOf(end, pos);
    if (at < 0) fail(`missing ${end}`);
    pos = at + end.length;
  };
  const skipSpace = (): void => {
    while (pos < source.length && /\s/.test(source[pos])) pos++;
  };

  function parseElement(): XmlElement {
    pos++; // <
    const name = /^[^\s/>]+/.exec(source.slice(pos))?.[0] ?? fail("missing element name");
    pos += name.length;
    const attributes: Record<string, string> = {};
    for (;;) {
      skipSpace();
      if (source.startsWith("/>", pos)) {
        pos += 2;
        return { name, attributes, children: [] };
      }
      if (source[pos] === ">") {
        pos++;
        break;
      }
      const match = /^([^\s=/>]+)\s*=\s*(?:"([^"]*)"|'([^']*)')/.exec(source.slice(pos)) ?? fail("bad attribute");
      attributes[match[1]] = decodeEntities(match[2] ?? match[3]);
      pos += match[0].length;
    }
    const children: (XmlElement | string)[] = [];
    let text = "";
    const flush = (): void => {
      if (text !== "") children.push(text);
      text = "";
    };
    for (;;) {
      if (pos >= source.length) fail(`unclosed <${name}>`);
      if (source.startsWith("</", pos)) {
        flush();
        const end = source.indexOf(">", pos);
        if (source.slice(pos + 2, end).trim() !== name) fail(`mismatched </${source.slice(pos + 2, end)}>`);
        pos = end + 1;
        return { name, attributes, children };
      }
      if (source.startsWith("<!--", pos)) skipPast("-->");
      else if (source.startsWith("<![CDATA[", pos)) {
        const end = source.indexOf("]]>", pos);
        if (end < 0) fail("unclosed CDATA");
        text += source.slice(pos + 9, end);
        pos = end + 3;
      } else if (source.startsWith("<?", pos)) skipPast("?>");
      else if (source[pos] === "<") {
        flush();
        children.push(parseElement());
      } else {
        const next = source.indexOf("<", pos);
        const end = next < 0 ? source.length : next;
        text += decodeEntities(source.slice(pos, end));
        pos = end;
      }
    }
  }

  skipSpace();
  for (;;) {
    if (source.startsWith("<?", pos)) skipPast("?>");
    else if (source.startsWith("<!--", pos)) skipPast("-->");
    else if (source.startsWith("<!DOCTYPE", pos)) fail("a DOCTYPE is not allowed");
    else break;
    skipSpace();
  }
  if (source[pos] !== "<") fail("no root element");
  const root = parseElement();
  skipSpace();
  if (pos < source.length) fail("content after the root element");
  return root;
}

function elementsOf(parent: XmlElement): XmlElement[] {
  return parent.children.filter((child): child is XmlElement => typeof child !== "string");
}

function textOf(element: XmlElement): string {
  return element.children.map((child) => (typeof child === "string" ? child : textOf(child))).join("");
}

function attribute(element: XmlElement, name: string): string {
  const value = element.attributes[name];
  if (value === undefined) throw new Error(`invalid markup: <${element.name}> has no ${name}`);
  return value;
}

function readParts(element: XmlElement): Part[] {
  const parts: Part[] = [];
  for (const child of element.children) {
    if (typeof child === "string") parts.push({ kind: "literal", text: child });
    else if (child.name === "var") parts.push({ kind: "variable", variableKey: attribute(child, "key"), text: textOf(child) });
    else if (child.name === "ref") parts.push({ kind: "reference", targetElementId: attribute(child, "target"), text: textOf(child) });
    else throw new Error(`invalid markup: <${child.name}> inside <${element.name}>`);
  }
  return mergeLiterals(parts);
}

function readElement(element: XmlElement): DocumentElement {
  const kind = element.name as "clause" | "definition";
  return {
    elementId: attribute(element, "id"),
    kind,
    definedTerm: kind === "definition" ? attribute(element, "term") : null,
    parts: readParts(element),
  };
}

/** Reads markup into the document model. It checks the structure it reads, and leaves the rest to the schema. */
export function readMarkup(markup: string): DocumentSnapshot {
  const root = parseXml(markup);
  if (root.name !== "document" || root.attributes.xmlns !== MARKUP_NAMESPACE) {
    throw new Error(`invalid markup: the root is not a <document> in ${MARKUP_NAMESPACE}`);
  }
  const children = elementsOf(root);
  const meta = children.find((child) => child.name === "meta");
  const body = children.find((child) => child.name === "body");
  if (!meta || !body) throw new Error("invalid markup: a document needs a <meta> and a <body>");
  const metaChildren = elementsOf(meta);
  const field = (name: string): string => {
    const found = metaChildren.find((child) => child.name === name);
    if (!found) throw new Error(`invalid markup: <meta> has no <${name}>`);
    return textOf(found);
  };

  const sections: Section[] = [];
  const unmarked: Unmarked[] = [];
  for (const child of elementsOf(body)) {
    if (child.name === "unmarked") unmarked.push({ sectionKey: null, text: textOf(child) });
    else if (child.name === "section") {
      const sectionKey = attribute(child, "key");
      const elements: DocumentElement[] = [];
      for (const inner of elementsOf(child)) {
        if (inner.name === "unmarked") unmarked.push({ sectionKey, text: textOf(inner) });
        else if (inner.name === "clause" || inner.name === "definition") elements.push(readElement(inner));
        else throw new Error(`invalid markup: <${inner.name}> inside <section>`);
      }
      sections.push({ sectionKey, elements });
    } else throw new Error(`invalid markup: <${child.name}> inside <body>`);
  }

  return {
    schemaVersion: "0.1.0",
    documentId: attribute(root, "id"),
    templateId: field("template"),
    title: field("title"),
    sections,
    variables: metaChildren
      .filter((child) => child.name === "variable")
      .map((child) => ({ variableKey: attribute(child, "key"), label: textOf(child), valueType: attribute(child, "type") as ValueType })),
    unmarked,
  };
}
