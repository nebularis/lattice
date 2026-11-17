// SPDX-License-Identifier: MPL-2.0
// JSON and XML output for the explorer (SVA-M4), turned into nodes of a collapsible tree. A text that does not parse is an error value
// with the parser's message, so the explorer can say so and show the text, and nothing here throws.

export type TreeKind = "object" | "array" | "string" | "number" | "boolean" | "null" | "element" | "attribute" | "text";

export interface TreeNode {
  /** The path from the root, so it is unique among the nodes of one tree. */
  id: string;
  /** A JSON key or index, an XML element's or attribute's qualified name, or nothing for XML text. */
  label?: string;
  kind: TreeKind;
  /** A scalar's text, an attribute's value or an XML text's content. */
  value?: string;
  /** What a container holds, such as "3 keys" or "2 items". */
  summary?: string;
  children: TreeNode[];
}

export type ParsedTree = { ok: true; root: TreeNode } | { ok: false; message: string };

const MAX_DEPTH = 200;

function jsonNode(value: unknown, id: string, label: string | undefined, depth: number): TreeNode {
  if (value === null) return { id, label, kind: "null", value: "null", children: [] };
  if (typeof value === "string") return { id, label, kind: "string", value: JSON.stringify(value), children: [] };
  if (typeof value === "number") return { id, label, kind: "number", value: String(value), children: [] };
  if (typeof value === "boolean") return { id, label, kind: "boolean", value: String(value), children: [] };
  if (depth >= MAX_DEPTH) return { id, label, kind: "string", value: "(nested too deeply to show)", children: [] };
  if (Array.isArray(value)) {
    return { id, label, kind: "array", summary: `${value.length} ${value.length === 1 ? "item" : "items"}`, children: value.map((v, i) => jsonNode(v, `${id}/${i}`, String(i), depth + 1)) };
  }
  const entries = Object.entries(value as Record<string, unknown>);
  return { id, label, kind: "object", summary: `${entries.length} ${entries.length === 1 ? "key" : "keys"}`, children: entries.map(([k, v]) => jsonNode(v, `${id}/${k}`, k, depth + 1)) };
}

export function parseJsonTree(text: string): ParsedTree {
  try {
    return { ok: true, root: jsonNode(JSON.parse(text), "", undefined, 0) };
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : String(error) };
  }
}

function xmlNode(element: Element, id: string, depth: number): TreeNode {
  const children: TreeNode[] = [];
  for (const attribute of Array.from(element.attributes)) children.push({ id: `${id}/@${attribute.name}`, label: attribute.name, kind: "attribute", value: attribute.value, children: [] });
  if (depth >= MAX_DEPTH) {
    children.push({ id: `${id}/…`, kind: "text", value: "(nested too deeply to show)", children: [] });
  } else {
    let n = 0;
    for (const child of Array.from(element.childNodes)) {
      if (child.nodeType === 1) children.push(xmlNode(child as Element, `${id}/${n++}`, depth + 1));
      else if (child.nodeType === 3 || child.nodeType === 4) {
        const content = (child.nodeValue ?? "").trim();
        if (content) children.push({ id: `${id}/${n++}`, kind: "text", value: content, children: [] });
      }
    }
  }
  return { id, label: element.tagName, kind: "element", children };
}

/** XML read with the browser's own parser. Element names are as written, so a namespace shows as its prefix, and the declarations are attributes. */
export function parseXmlTree(text: string): ParsedTree {
  if (typeof DOMParser === "undefined") return { ok: false, message: "This environment has no XML parser." };
  try {
    const doc = new DOMParser().parseFromString(text, "application/xml");
    const error = doc.getElementsByTagName("parsererror")[0];
    if (error) return { ok: false, message: (error.textContent ?? "The XML is not well formed.").replace(/\s+/g, " ").trim() };
    return { ok: true, root: xmlNode(doc.documentElement, "", 0) };
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : String(error) };
  }
}

/** The text pretty-printed, or the reason it is not JSON. */
export function prettyJson(text: string): { ok: true; text: string } | { ok: false; message: string } {
  try {
    return { ok: true, text: JSON.stringify(JSON.parse(text), null, 2) };
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : String(error) };
  }
}
