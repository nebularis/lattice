// SPDX-License-Identifier: MPL-2.0
// A surface contract's read path. One forward hop is written as srf:readProperty, anything else
// as srf:hasPathStep nodes, and never both (srf:S1).

import { Graph, iri, typed } from "./graph";
import { SRF, TYPE, XSD } from "./ns";

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
