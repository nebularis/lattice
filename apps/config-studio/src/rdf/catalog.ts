// SPDX-License-Identifier: MPL-2.0
// Reading an OASIS XML catalog, as Protege writes it and as tools/ontology_catalog.py generates it
// (ADR-A88), from the files an author dropped. Nothing here fetches anything. A catalog entry maps
// an ontology or version IRI to a location, and a location that is a path is given relative to the
// dropped root, so the caller can look it up among the dropped files.

const XML_NS = "http://www.w3.org/XML/1998/namespace";

export interface CatalogEntry {
  /** The IRI the entry maps. */
  name: string;
  /** A path relative to the dropped root, or a location with a scheme, left as written. */
  target: string;
}

export interface ParsedCatalog {
  entries: CatalogEntry[];
  /** The `nextCatalog` targets, as paths relative to the dropped root, in document order. */
  nextCatalogs: string[];
  /** Set when the text is not a readable catalog, and then the lists are empty. */
  error?: string;
}

/** True for a location with a scheme, such as https:, which is never a dropped file. */
export function isWebLocation(target: string): boolean {
  return /^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(target);
}

/** Resolves `.` and `..` and drops empty segments. A path that climbs above the root keeps its leading `..`. */
export function normalisePath(path: string): string {
  const parts: string[] = [];
  for (const segment of path.replace(/\\/g, "/").split("/")) {
    if (segment === "" || segment === ".") continue;
    if (segment === "..") {
      if (parts.length > 0 && parts[parts.length - 1] !== "..") parts.pop();
      else parts.push("..");
      continue;
    }
    parts.push(segment);
  }
  return parts.join("/");
}

function safeDecode(path: string): string {
  try {
    return decodeURI(path);
  } catch {
    return path;
  }
}

// A reference resolves against the directory of its base, as in a URI. A base such as "sub/" keeps
// its trailing slash, so it is not normalised here.
function resolveRef(base: string, ref: string): string {
  if (isWebLocation(ref)) return ref;
  if (isWebLocation(base)) {
    try {
      return new URL(ref, base).href;
    } catch {
      return ref;
    }
  }
  if (ref.startsWith("/")) return ref.replace(/^\/+/, "");
  return base.slice(0, base.lastIndexOf("/") + 1) + ref;
}

function finish(resolved: string): string {
  return isWebLocation(resolved) ? resolved : normalisePath(safeDecode(resolved));
}

/**
 * Reads one catalog. `catalogPath` is the catalog file's own path inside the dropped folder, which
 * every relative location, `xml:base` included, is resolved against. Elements other than `uri`,
 * `nextCatalog` and `group` are ignored, and an element is matched by its local name.
 */
export function parseCatalog(text: string, catalogPath: string): ParsedCatalog {
  const empty = (error: string): ParsedCatalog => ({ entries: [], nextCatalogs: [], error });
  let doc: Document;
  try {
    doc = new DOMParser().parseFromString(text, "application/xml");
  } catch (error) {
    return empty(error instanceof Error ? error.message : String(error));
  }
  if (doc.getElementsByTagName("parsererror").length > 0) return empty("the text is not well-formed XML");
  const root = doc.documentElement;
  if (!root || root.localName !== "catalog") return empty("the root element is not a catalog");

  const entries: CatalogEntry[] = [];
  const nextCatalogs: string[] = [];
  const baseOf = (element: Element, parent: string): string => {
    const own = element.getAttributeNS(XML_NS, "base");
    return own ? resolveRef(parent, own) : parent;
  };
  const walk = (element: Element, parentBase: string): void => {
    const base = baseOf(element, parentBase);
    for (const child of Array.from(element.children)) {
      if (child.localName === "group") {
        walk(child, base);
      } else if (child.localName === "uri") {
        const name = child.getAttribute("name");
        const uri = child.getAttribute("uri");
        if (name && uri) entries.push({ name, target: finish(resolveRef(baseOf(child, base), uri)) });
      } else if (child.localName === "nextCatalog") {
        const catalog = child.getAttribute("catalog");
        if (catalog) nextCatalogs.push(finish(resolveRef(baseOf(child, base), catalog)));
      }
    }
  };
  walk(root, catalogPath);
  return { entries, nextCatalogs };
}

export interface CatalogLookup {
  /** One IRI to location map. Where two catalogs name an IRI, the first one read wins, as in OASIS. */
  lookup: Map<string, string>;
  /** The catalogs a chain named that were not among the dropped files, in the order met. */
  missingCatalogs: string[];
  /** The catalogs that were dropped but could not be read. */
  errors: { path: string; message: string }[];
}

/**
 * Merges the catalog at `startPath` with the catalogs its `nextCatalog` elements name, among the
 * dropped files, which map a relative path to its text. A catalog's own entries come before those of
 * the catalogs it chains to. A catalog met twice is read once, so a cycle ends.
 */
export function buildCatalogLookup(files: ReadonlyMap<string, string>, startPath: string): CatalogLookup {
  const dropped = new Map<string, string>();
  for (const [path, text] of files) dropped.set(normalisePath(path), text);
  const lookup = new Map<string, string>();
  const missingCatalogs: string[] = [];
  const errors: { path: string; message: string }[] = [];
  const visited = new Set<string>();

  const visit = (path: string): void => {
    if (visited.has(path)) return;
    visited.add(path);
    const text = dropped.get(path);
    if (text === undefined) {
      missingCatalogs.push(path);
      return;
    }
    const parsed = parseCatalog(text, path);
    if (parsed.error !== undefined) {
      errors.push({ path, message: parsed.error });
      return;
    }
    for (const entry of parsed.entries) if (!lookup.has(entry.name)) lookup.set(entry.name, entry.target);
    for (const next of parsed.nextCatalogs) visit(next);
  };
  visit(normalisePath(startPath));
  return { lookup, missingCatalogs, errors };
}
