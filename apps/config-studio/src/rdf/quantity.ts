// SPDX-License-Identifier: MPL-2.0
// Reading and writing quantification's ranges. A qnt:Range names a lower and an upper qnt:Bound,
// each with a qnt:Quantity value on the range's value space, a sense and a closure. Writing one by
// hand is seven nodes, so the studio writes them together.

import { Graph, iri, typed, type Term } from "./graph";
import { ELG, QNT, TYPE, XSD } from "./ns";
import { mint } from "./editors";

export interface End {
  value: number;
  closed: boolean;
}

export interface RangeView {
  iri: string;
  space?: string;
  lower?: End;
  upper?: End;
}

function end(world: Graph, bound: Term | undefined): End | undefined {
  if (!bound) return undefined;
  const value = world.object(bound, QNT("boundValue"));
  const number = value ? Number(world.value(value, QNT("numericValue"))) : NaN;
  if (Number.isNaN(number)) return undefined;
  return { value: number, closed: world.value(bound, QNT("boundClosure")) !== QNT("Open") };
}

export function readRange(world: Graph, range: string): RangeView {
  return {
    iri: range,
    space: world.value(range, QNT("onSpace")),
    lower: end(world, world.object(range, QNT("lowerBound"))),
    upper: end(world, world.object(range, QNT("upperBound"))),
  };
}

export function rangesOf(world: Graph, rangeSet: string): RangeView[] {
  return world
    .objects(rangeSet, QNT("hasRange"))
    .map((r) => readRange(world, r.value))
    .sort((a, b) => (a.lower?.value ?? -Infinity) - (b.lower?.value ?? -Infinity));
}

/** Whether a number lies in a range, by its ends' closures. */
export function contains(range: RangeView, x: number): boolean {
  const { lower, upper } = range;
  if (lower && (x < lower.value || (x === lower.value && !lower.closed))) return false;
  if (upper && (x > upper.value || (x === upper.value && !upper.closed))) return false;
  return true;
}

export interface NewRange {
  space: string;
  lower?: End;
  upper?: End;
}

/** Writes a range and its bounds and quantities, and adds it to `rangeSet` when one is given. */
export function addRange(graph: Graph, namespace: string, name: string, spec: NewRange, rangeSet?: string): { graph: Graph; iri: string } {
  const range = mint(graph, namespace, `${name} range`);
  const next = graph.edit((e) => {
    e.add(range, TYPE, iri(QNT("Range")));
    e.add(range, QNT("onSpace"), iri(spec.space));
    for (const [sense, endpoint, property] of [
      ["Lower", spec.lower, QNT("lowerBound")],
      ["Upper", spec.upper, QNT("upperBound")],
    ] as const) {
      if (!endpoint) continue;
      const quantity = `${range}-${sense.toLowerCase()}-value`;
      const bound = `${range}-${sense.toLowerCase()}`;
      e.add(quantity, TYPE, iri(QNT("Quantity")));
      e.add(quantity, QNT("onSpace"), iri(spec.space));
      e.add(quantity, QNT("numericValue"), typed(String(endpoint.value), XSD("decimal")));
      e.add(bound, TYPE, iri(QNT("Bound")));
      e.add(bound, QNT("onSpace"), iri(spec.space));
      e.add(bound, QNT("boundValue"), iri(quantity));
      e.add(bound, QNT("boundSense"), iri(QNT(sense)));
      e.add(bound, QNT("boundClosure"), iri(QNT(endpoint.closed ? "Closed" : "Open")));
      e.add(range, property, iri(bound));
      e.add(range, QNT("hasBound"), iri(bound));
    }
    if (rangeSet) e.add(rangeSet, QNT("hasRange"), iri(range));
  });
  return { graph: next, iri: range };
}

/** Removes a range with the bounds and quantities only it uses. */
export function removeRange(graph: Graph, range: string): Graph {
  return graph.edit((e) => {
    for (const bound of graph.objects(range, QNT("hasBound"))) {
      const value = graph.object(bound, QNT("boundValue"));
      if (value && graph.subjects(QNT("boundValue"), value).length === 1) e.remove(value);
      if (graph.subjects(QNT("hasBound"), bound).length === 1) e.remove(bound);
    }
    e.remove(range);
  });
}

/** The value space of a condition's required ranges, for a candidate written against it. */
export function conditionSpace(world: Graph, condition: string): string | undefined {
  const set = world.value(condition, ELG("requiredRangeSet"));
  return set ? world.value(set, QNT("onSpace")) ?? rangesOf(world, set)[0]?.space : undefined;
}

/** A range set holding one closed point, the shape of a candidate value (elg:candidateRangeSet). */
export function pointRangeSet(graph: Graph, namespace: string, name: string, space: string, value: number): { graph: Graph; iri: string } {
  const set = mint(graph, namespace, `${name} candidate`);
  const withSet = graph.edit((e) => {
    e.add(set, TYPE, iri(QNT("RangeSet")));
    e.add(set, QNT("onSpace"), iri(space));
  });
  const made = addRange(withSet, namespace, `${name} candidate`, { space, lower: { value, closed: true }, upper: { value, closed: true } }, set);
  return { graph: made.graph, iri: set };
}
