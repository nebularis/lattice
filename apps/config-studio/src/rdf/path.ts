// SPDX-License-Identifier: MPL-2.0
// A surface contract's read path. One forward hop is written as srf:readProperty, anything else
// as srf:hasPathStep nodes, and never both (srf:S1).

import { Graph, SH, SRF, TYPE, XSD, blankNode, iri, typed, type GraphEditor, type Term } from "@lattice/authoring-domain";

export interface Step {
  property: string;
  inverse: boolean;
}

export function readPath(graph: Graph, contract: string): Step[] {
  const single = graph.value(contract, SRF("readProperty"));
  if (single) return [{ property: single, inverse: false }];
  return graph
    .objects(contract, SRF("hasPathStep"))
    .map((s) => ({
      index: Number(graph.value(s, SRF("stepIndex")) ?? 0),
      property: graph.value(s, SRF("stepProperty")) ?? "",
      inverse: graph.value(s, SRF("stepDirection")) === SRF("Inverse"),
    }))
    .sort((a, b) => a.index - b.index)
    .map(({ property, inverse }) => ({ property, inverse }));
}

export function writePath(graph: Graph, contract: string, steps: Step[]): Graph {
  return graph.edit((e) => {
    for (const s of graph.objects(contract, SRF("hasPathStep"))) e.remove(s);
    e.setAll(contract, SRF("readProperty"), []);
    if (steps.length === 1 && !steps[0].inverse) {
      e.add(contract, SRF("readProperty"), iri(steps[0].property));
      return;
    }
    steps.forEach((step, i) => {
      let node = `${contract}-step-${i}`;
      for (let n = 2; graph.has(node) && !graph.objects(contract, SRF("hasPathStep")).some((s) => s.value === node); n++) node = `${contract}-step-${i}-${n}`;
      e.add(node, TYPE, iri(SRF("PathStep")));
      e.add(node, SRF("stepIndex"), typed(String(i), XSD("nonNegativeInteger")));
      e.add(node, SRF("stepProperty"), iri(step.property));
      e.add(node, SRF("stepDirection"), iri(SRF(step.inverse ? "Inverse" : "Forward")));
      e.add(contract, SRF("hasPathStep"), iri(node));
    });
  });
}

/** One hop of an expansion's members path, a property taken forward or inversely with a closure where the path repeats it. */
export interface MemberHop {
  property: string;
  inverse: boolean;
  /** One or more, zero or more, or zero or one. */
  closure?: "+" | "*" | "?";
  /** Further properties the hop may take instead, as an alternative path states. */
  alternatives?: string[];
}

const CLOSURES = { "+": "oneOrMorePath", "*": "zeroOrMorePath", "?": "zeroOrOnePath" } as const;

/** A hop as the SHACL path that states it: a property, `sh:inversePath` for an inverse hop, `sh:alternativePath` for alternatives, and a closure around the hop. */
function hopPath(e: GraphEditor, hop: MemberHop): Term {
  let path: Term = iri(hop.property);
  if (hop.alternatives?.length) {
    const alternative = blankNode();
    e.setList(alternative, SH("alternativePath"), [path, ...hop.alternatives.map((p) => iri(p))]);
    path = alternative;
  }
  if (hop.inverse) {
    const inverse = blankNode();
    e.add(inverse, SH("inversePath"), path);
    path = inverse;
  }
  if (hop.closure) {
    const closure = blankNode();
    e.add(closure, SH(CLOSURES[hop.closure]), path);
    path = closure;
  }
  return path;
}

/**
 * An expansion's members path, written as the Surface README gives it (srf:P20): one hop as the property or its path, a sequence of hops as a list,
 * and no named source beside it, since a statement states a source or a path and never both. No hops removes the path. The read path form of a
 * contract is `writePath`, and the property a binding binds is `writeBindingProperty`.
 */
export function writeMembersPath(graph: Graph, statement: string, hops: MemberHop[]): Graph {
  return graph.edit((e) => {
    e.setAll(statement, SRF("expansionSource"), []);
    e.setAll(statement, SRF("membersPath"), []);
    const paths = hops.map((h) => hopPath(e, h));
    if (paths.length === 1) e.add(statement, SRF("membersPath"), paths[0]);
    else if (paths.length > 1) e.setList(statement, SRF("membersPath"), paths);
  });
}

/** The one property a role binding binds, or none. */
export function writeBindingProperty(graph: Graph, binding: string, property: string | undefined): Graph {
  return graph.edit((e) => e.setAll(binding, SRF("bindsProperty"), property ? [iri(property)] : []));
}
