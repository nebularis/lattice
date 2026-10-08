/**
 * Small shared DOM-parsing helpers used by both `ooxml.ts` and `metadata.ts`, so the two modules
 * do not each re-implement namespace-qualified child lookup and XML escaping.
 */

export function escapeXml(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

export function parseXmlDocument(xml: string): Document {
  const parser = new DOMParser();
  const doc = parser.parseFromString(xml, "application/xml");
  const parserError = doc.getElementsByTagName("parsererror")[0];
  if (parserError) {
    throw new Error(`invalid XML: ${parserError.textContent ?? "unknown parse error"}`);
  }
  return doc;
}

export function firstChildByNameNs(parent: Element, ns: string, localName: string): Element | null {
  for (const child of Array.from(parent.childNodes)) {
    if (child.nodeType === 1 && (child as Element).namespaceURI === ns && (child as Element).localName === localName) {
      return child as Element;
    }
  }
  return null;
}

export function childrenByNameNs(parent: Element, ns: string, localName: string): Element[] {
  const result: Element[] = [];
  for (const child of Array.from(parent.childNodes)) {
    if (child.nodeType === 1 && (child as Element).namespaceURI === ns && (child as Element).localName === localName) {
      result.push(child as Element);
    }
  }
  return result;
}
