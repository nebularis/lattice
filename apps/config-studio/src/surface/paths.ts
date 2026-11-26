// SPDX-License-Identifier: MPL-2.0
// The members path of an expansion, a SHACL property path (SVA-Q59), read as the hops it is made of. A hop is a property, taken forward or
// inversely, with a closure where the path repeats it. A path in a form this does not read is not guessed at. It gives no hops, and the
// drawing says so with a placeholder.

import { Graph, RDF, SH, SRF, type Term } from "@lattice/authoring-domain";

export type Closure = "+" | "*" | "?";

export interface Hop {
  property: string;
  inverse: boolean;
  /** One or more, zero or more, or zero or one. */
  closure?: Closure;
  /** Further properties the hop may take instead, as an alternative path states. */
  alternatives?: string[];
}

const NIL = RDF("nil");

/** The hops of the path at `node`, or undefined where the path is in a form this does not read. */
export function readHops(g: Graph, node: Term): Hop[] | undefined {
  if (node.termType === "NamedNode") return node.value === NIL ? [] : [{ property: node.value, inverse: false }];
  if (node.termType !== "BlankNode") return undefined;
  const items = g.list(node);
  if (items) {
    const hops: Hop[] = [];
    for (const item of items) {
      const inner = readHops(g, item);
      if (!inner) return undefined;
      hops.push(...inner);
    }
    return hops;
  }
  const inverse = g.object(node, SH("inversePath"));
  if (inverse) {
    const inner = readHops(g, inverse);
    // An inverse of a sequence reads the sequence backwards.
    return inner && inner.map((h) => ({ ...h, inverse: !h.inverse })).reverse();
  }
  for (const [predicate, closure] of [["oneOrMorePath", "+"], ["zeroOrMorePath", "*"], ["zeroOrOnePath", "?"]] as const) {
    const inner = g.object(node, SH(predicate));
    if (inner) {
      const hops = readHops(g, inner);
      return hops && hops.length === 1 ? [{ ...hops[0], closure }] : undefined;
    }
  }
  const alternative = g.object(node, SH("alternativePath"));
  if (alternative) {
    const parts = g.list(alternative)?.map((p) => (p.termType === "NamedNode" ? p.value : undefined));
    if (!parts?.length || parts.some((p) => p === undefined)) return undefined;
    return [{ property: parts[0]!, inverse: false, alternatives: parts.slice(1) as string[] }];
  }
  return undefined;
}

/** The members path an expansion statement states for itself, if it does. */
export function membersPath(g: Graph, statement: string): Hop[] | undefined {
  const path = g.object(statement, SRF("membersPath"));
  return path ? readHops(g, path) : undefined;
}

/**
 * The hops each named source stands for, as the vocabulary defines them. srf:ListMembers is the property, then rdf:rest zero or more
 * times, then rdf:first, and srf:TransitiveClosure is the property one or more times. This restates the definition and lowers nothing.
 */
export function sourceHops(source: string | undefined, property: string): Hop[] | undefined {
  if (source === SRF("ListMembers")) {
    return [{ property, inverse: false }, { property: RDF("rest"), inverse: false, closure: "*" }, { property: RDF("first"), inverse: false }];
  }
  if (source === SRF("TransitiveClosure")) return [{ property, inverse: false, closure: "+" }];
  return undefined;
}
