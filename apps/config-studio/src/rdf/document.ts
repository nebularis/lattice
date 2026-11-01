// SPDX-License-Identifier: MPL-2.0
// Reads an assembled document, in the markup of contracts/document, into what the studio shows: a title,
// and per section the numbered clauses, whose text runs mark a variable's shown value. The assembler
// writes a clause's number as the first word of its text.

export interface Run {
  kind: "text" | "var" | "ref";
  text: string;
  /** The variable's key, for a var. */
  key?: string;
}

export interface DocClause {
  number?: string;
  runs: Run[];
}

export interface DocSection {
  /** The section's number, from its key. */
  number: string;
  clauses: DocClause[];
}

export interface AssembledDocument {
  title: string;
  /** Sections, and text outside any section as a section with no number. */
  sections: DocSection[];
}

const NUMBER = /^(\d+(?:\.\d+)*)\s+/;

function runsOf(element: Element): Run[] {
  const out: Run[] = [];
  for (const node of Array.from(element.childNodes)) {
    if (node.nodeType === 3) out.push({ kind: "text", text: node.textContent ?? "" });
    else if (node.nodeType === 1) {
      const e = node as Element;
      if (e.localName === "var") out.push({ kind: "var", text: e.textContent ?? "", key: e.getAttribute("key") ?? undefined });
      else if (e.localName === "ref") out.push({ kind: "ref", text: e.textContent ?? "" });
    }
  }
  return out;
}

function clauseOf(element: Element): DocClause {
  const runs = runsOf(element);
  const first = runs[0];
  const match = first?.kind === "text" ? NUMBER.exec(first.text) : null;
  if (match && first) runs[0] = { ...first, text: first.text.slice(match[0].length) };
  return { number: match?.[1], runs };
}

/** Undefined when the text is not well-formed XML. */
export function readDocument(xml: string): AssembledDocument | undefined {
  const doc = new DOMParser().parseFromString(xml, "application/xml");
  if (doc.getElementsByTagName("parsererror").length) return undefined;
  const title = doc.getElementsByTagName("title")[0]?.textContent ?? "Assembled wording";
  const body = doc.getElementsByTagName("body")[0];
  const sections: DocSection[] = [];
  for (const child of Array.from(body?.children ?? [])) {
    if (child.localName === "section") {
      sections.push({
        number: (child.getAttribute("key") ?? "").replace(/^section-/, ""),
        clauses: Array.from(child.children)
          .filter((c) => c.localName === "clause" || c.localName === "definition" || c.localName === "unmarked")
          .map(clauseOf),
      });
    } else if (child.localName === "unmarked") {
      sections.push({ number: "", clauses: [clauseOf(child)] });
    }
  }
  return { title, sections };
}
