// SPDX-License-Identifier: MPL-2.0
// Resolving an ontology's owl:imports closure from what the author dropped, what the workspace
// holds and what the service stages, in that fixed order (ADR-A88, SVA-Q5). An import that none of
// them gives is reported missing and never guessed. Nothing here fetches anything, reads the clock
// or draws a random number, so the same input in any file order gives the same plan.

import { Parser } from "n3";
import { isWebLocation, normalisePath } from "./catalog";

const OWL = "http://www.w3.org/2002/07/owl#";
const RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#";
const XML_NS = "http://www.w3.org/XML/1998/namespace";

export type MediaType = "text/turtle" | "application/rdf+xml";

export interface OntologyHeader {
  ontologyIri?: string;
  versionIri?: string;
  imports: string[];
}

/** Thrown by `ontologyHeader` when the text cannot be parsed. */
export class HeaderError extends Error {}

/** Guesses a media type from a file name. Returns undefined for any other extension. */
export function mediaTypeOf(path: string): MediaType | undefined {
  const lower = path.toLowerCase();
  if (lower.endsWith(".ttl")) return "text/turtle";
  if (lower.endsWith(".owl") || lower.endsWith(".rdf") || lower.endsWith(".xml")) return "application/rdf+xml";
  return undefined;
}

function turtleHeader(text: string): OntologyHeader {
  let quads;
  try {
    quads = new Parser({ format: "text/turtle" }).parse(text);
  } catch (error) {
    throw new HeaderError(error instanceof Error ? error.message : String(error));
  }
  const ontology = quads.find(
    (q) => q.subject.termType === "NamedNode" && q.predicate.value === `${RDF}type` && q.object.value === `${OWL}Ontology`,
  );
  if (!ontology) return { imports: [] };
  const subject = ontology.subject.value;
  const objects = (predicate: string): string[] =>
    quads
      .filter((q) => q.subject.value === subject && q.predicate.value === predicate && q.object.termType === "NamedNode")
      .map((q) => q.object.value);
  const header: OntologyHeader = { ontologyIri: subject, imports: [...new Set(objects(`${OWL}imports`))] };
  const version = objects(`${OWL}versionIRI`)[0];
  if (version !== undefined) header.versionIri = version;
  return header;
}

// An RDF/XML reference, resolved against the nearest xml:base. A relative reference with no
// absolute base cannot be resolved and gives undefined.
function resolveXmlRef(ref: string, base: string): string | undefined {
  if (isWebLocation(ref)) return ref;
  if (!isWebLocation(base)) return undefined;
  try {
    return new URL(ref, base).href;
  } catch {
    return undefined;
  }
}

function xmlBaseOf(element: Element): string {
  const chain: Element[] = [];
  for (let e: Element | null = element; e; e = e.parentElement) chain.unshift(e);
  let base = "";
  for (const e of chain) {
    const own = e.getAttributeNS(XML_NS, "base");
    if (!own) continue;
    base = isWebLocation(own) ? own : (resolveXmlRef(own, base) ?? base);
  }
  return base;
}

function rdfXmlHeader(text: string): OntologyHeader {
  let doc: Document;
  try {
    doc = new DOMParser().parseFromString(text, "application/xml");
  } catch (error) {
    throw new HeaderError(error instanceof Error ? error.message : String(error));
  }
  if (doc.getElementsByTagName("parsererror").length > 0) throw new HeaderError("the text is not well-formed XML");
  const root = doc.documentElement;
  if (!root) throw new HeaderError("the document has no root element");

  const isOntology = (e: Element): boolean => {
    if (e.namespaceURI === OWL && e.localName === "Ontology") return true;
    if (e.namespaceURI !== RDF || e.localName !== "Description") return false;
    return Array.from(e.children).some(
      (c) => c.namespaceURI === RDF && c.localName === "type" && c.getAttributeNS(RDF, "resource") === `${OWL}Ontology`,
    );
  };
  const element = Array.from(root.children).find(isOntology);
  if (!element) return { imports: [] };

  const base = xmlBaseOf(element);
  const header: OntologyHeader = { imports: [] };
  const about = element.getAttributeNS(RDF, "about");
  const ontologyIri = about === null ? undefined : about === "" ? (base || undefined) : resolveXmlRef(about, base);
  if (ontologyIri !== undefined) header.ontologyIri = ontologyIri;
  const resources = (name: string): string[] =>
    Array.from(element.children)
      .filter((c) => c.namespaceURI === OWL && c.localName === name)
      .map((c) => c.getAttributeNS(RDF, "resource"))
      .filter((r): r is string => r !== null && r !== "")
      .map((r) => resolveXmlRef(r, base))
      .filter((r): r is string => r !== undefined);
  const version = resources("versionIRI")[0];
  if (version !== undefined) header.versionIri = version;
  header.imports = [...new Set(resources("imports"))];
  return header;
}

/**
 * Reads an ontology's header: its IRI, its version IRI and the IRIs it imports. A Turtle document is
 * parsed whole. An RDF/XML document is read for its header alone, since the service converts the
 * body when it fences the document. A document with no owl:Ontology gives no IRI and no imports.
 * Throws HeaderError when the text does not parse.
 */
export function ontologyHeader(text: string, mediaType: MediaType): OntologyHeader {
  return mediaType === "text/turtle" ? turtleHeader(text) : rdfXmlHeader(text);
}

export interface DroppedFile {
  /** The path relative to the dropped root. */
  path: string;
  text: string;
  /** Guessed from the extension when left out. */
  mediaType?: MediaType;
}

export interface ResolveInput {
  /** The paths of the documents the author chose as roots. */
  roots: readonly string[];
  files: readonly DroppedFile[];
  /** The merged catalog, from IRI to a path relative to the dropped root. May be empty. */
  catalog: ReadonlyMap<string, string>;
  /** The imports the workspace already holds, from IRI to digest. */
  held: ReadonlyMap<string, string>;
  /** The IRIs of the documents the service stages. */
  staged: ReadonlySet<string> | readonly string[];
}

export type ImportStatus = "catalog" | "file" | "held" | "staged" | "missing";

export interface PlanNode {
  iri: string;
  status: ImportStatus;
  path?: string;
  digest?: string;
  ontologyIri?: string;
  versionIri?: string;
  importedBy: string[];
}

export interface PlanEdge {
  from: string;
  to: string;
}

export type ProblemKind =
  | "root-not-dropped"
  | "root-without-ontology"
  | "unsupported-type"
  | "unparseable"
  | "catalog-web-location"
  | "catalog-file-not-dropped"
  | "catalog-iri-mismatch"
  | "ambiguous-declaration";

export interface PlanProblem {
  kind: ProblemKind;
  message: string;
  iri?: string;
  path?: string;
}

export interface ImportPlan {
  /** The ontology IRIs of the roots, sorted. */
  roots: string[];
  /** Every IRI reached, sorted by IRI. */
  nodes: PlanNode[];
  /** Each owl:imports statement met, sorted. */
  edges: PlanEdge[];
  problems: PlanProblem[];
}

const compare = (a: string, b: string): number => (a < b ? -1 : a > b ? 1 : 0);

type Parsed = { header: OntologyHeader } | { error: string };

/**
 * Walks the closure of the roots' imports breadth first, with a visited set, so a cycle ends. Each
 * import IRI resolves in this order, and the first hit wins: the catalog, a dropped file that
 * declares the IRI as its ontology IRI or version IRI, a held import, a staged document, else missing.
 * A catalog entry whose location was not dropped is a problem, and the walk then goes on to the later
 * steps, which can still resolve the IRI.
 */
export function resolveImports(input: ResolveInput): ImportPlan {
  const files = new Map<string, DroppedFile>();
  for (const file of input.files) files.set(normalisePath(file.path), { ...file, path: normalisePath(file.path) });
  const paths = [...files.keys()].sort(compare);

  const parsed = new Map<string, Parsed>();
  const declared = new Map<string, string[]>();
  for (const path of paths) {
    const file = files.get(path)!;
    const mediaType = file.mediaType ?? mediaTypeOf(path);
    if (mediaType === undefined) {
      parsed.set(path, { error: "the file type is not Turtle or RDF/XML" });
      continue;
    }
    try {
      const header = ontologyHeader(file.text, mediaType);
      parsed.set(path, { header });
      for (const iri of new Set([header.ontologyIri, header.versionIri])) {
        if (iri === undefined) continue;
        declared.set(iri, [...(declared.get(iri) ?? []), path]);
      }
    } catch (error) {
      parsed.set(path, { error: error instanceof Error ? error.message : String(error) });
    }
  }

  const stagedSet = new Set(input.staged);
  const problems = new Map<string, PlanProblem>();
  const report = (problem: PlanProblem): void => {
    problems.set(JSON.stringify([problem.kind, problem.iri ?? "", problem.path ?? "", problem.message]), problem);
  };
  const nodes = new Map<string, PlanNode>();
  const documents = new Map<string, string>();
  const edges = new Map<string, PlanEdge>();
  const queue: string[] = [];
  const rootIris = new Set<string>();

  const describe = (node: PlanNode, path: string): void => {
    node.path = path;
    documents.set(node.iri, path);
    const entry = parsed.get(path);
    if (entry && "header" in entry) {
      if (entry.header.ontologyIri !== undefined) node.ontologyIri = entry.header.ontologyIri;
      if (entry.header.versionIri !== undefined) node.versionIri = entry.header.versionIri;
    }
  };

  const reportParseFailure = (iri: string | undefined, path: string): boolean => {
    const entry = parsed.get(path);
    if (entry === undefined || "header" in entry) return false;
    const unsupported = entry.error === "the file type is not Turtle or RDF/XML";
    report({
      kind: unsupported ? "unsupported-type" : "unparseable",
      message: `${path}: ${entry.error}`,
      path,
      ...(iri === undefined ? {} : { iri }),
    });
    return true;
  };

  for (const root of [...input.roots].map(normalisePath).sort(compare)) {
    if (!files.has(root)) {
      report({ kind: "root-not-dropped", message: `The root ${root} is not among the dropped files.`, path: root });
      continue;
    }
    if (reportParseFailure(undefined, root)) continue;
    const entry = parsed.get(root) as { header: OntologyHeader };
    const iri = entry.header.ontologyIri;
    if (iri === undefined) {
      report({ kind: "root-without-ontology", message: `The root ${root} declares no owl:Ontology.`, path: root });
      continue;
    }
    if (nodes.has(iri)) continue;
    const node: PlanNode = { iri, status: "file", importedBy: [] };
    describe(node, root);
    nodes.set(iri, node);
    rootIris.add(iri);
    queue.push(iri);
  }

  const resolveOne = (iri: string): PlanNode => {
    const node: PlanNode = { iri, status: "missing", importedBy: [] };
    const target = input.catalog.get(iri);
    if (target !== undefined) {
      if (isWebLocation(target)) {
        report({
          kind: "catalog-web-location",
          message: `The catalog maps ${iri} to ${target}, a web location that is not fetched.`,
          iri,
          path: target,
        });
      } else {
        const path = normalisePath(target);
        if (!files.has(path)) {
          report({
            kind: "catalog-file-not-dropped",
            message: `The catalog maps ${iri} to ${path}, which was not dropped.`,
            iri,
            path,
          });
        } else {
          node.status = "catalog";
          describe(node, path);
          if (!reportParseFailure(iri, path) && node.ontologyIri !== iri && node.versionIri !== iri) {
            report({
              kind: "catalog-iri-mismatch",
              message: `The catalog maps ${iri} to ${path}, which declares ${node.ontologyIri ?? "no ontology IRI"}.`,
              iri,
              path,
            });
          }
          return node;
        }
      }
    }
    const matches = declared.get(iri);
    if (matches !== undefined && matches.length > 0) {
      if (matches.length > 1) {
        report({
          kind: "ambiguous-declaration",
          message: `${iri} is declared by ${matches.join(", ")}. The first path is used.`,
          iri,
          path: matches[0],
        });
      }
      node.status = "file";
      describe(node, matches[0]);
      return node;
    }
    const digest = input.held.get(iri);
    if (digest !== undefined) {
      node.status = "held";
      node.digest = digest;
    } else if (stagedSet.has(iri)) {
      node.status = "staged";
    }
    return node;
  };

  for (let i = 0; i < queue.length; i++) {
    const from = queue[i];
    const entry = parsed.get(documents.get(from) ?? "");
    if (!entry || !("header" in entry)) continue;
    for (const to of entry.header.imports) {
      edges.set(JSON.stringify([from, to]), { from, to });
      let node = nodes.get(to);
      if (node === undefined) {
        node = resolveOne(to);
        nodes.set(to, node);
        if (documents.has(to)) queue.push(to);
      }
      if (!node.importedBy.includes(from)) node.importedBy.push(from);
    }
  }

  return finalise(nodes, edges, problems, rootIris);
}

function finalise(
  nodes: Map<string, PlanNode>,
  edges: Map<string, PlanEdge>,
  problems: Map<string, PlanProblem>,
  roots: Set<string>,
): ImportPlan {
  return {
    roots: [...roots].sort(compare),
    nodes: [...nodes.values()]
      .map((n) => ({ ...n, importedBy: [...n.importedBy].sort(compare) }))
      .sort((a, b) => compare(a.iri, b.iri)),
    edges: [...edges.values()].sort((a, b) => compare(a.from, b.from) || compare(a.to, b.to)),
    problems: [...problems.values()].sort(
      (a, b) =>
        compare(a.kind, b.kind) || compare(a.iri ?? "", b.iri ?? "") || compare(a.path ?? "", b.path ?? "") || compare(a.message, b.message),
    ),
  };
}
