// SPDX-License-Identifier: MPL-2.0
// The kit's edge routes are a pure function of the node boxes and the edges (SVA-O2a). The sides an edge attaches by, a pair of
// edges kept apart, a label kept off every node and every other label, the fallback when no place is free, the same result for any
// order of the input, and the facility sample drawn as the ontology canvas draws it.

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { Graph, PREFIXES, compact } from "@lattice/authoring-domain";
import { classGraph } from "../rdf/ontologyGraph";
import { LAYOUTS } from "../ui/OntologyCanvas";
import { DEFAULT_NODE_SIZE, LABEL_CANDIDATES, chooseSides, curvePoint, routeEdges, type Box, type EdgeRoute, type RouteEdge } from "./edges";
import { layered } from "./layout";

const box = (x: number, y: number, width = 100, height = 40): Box => ({ x, y, width, height });
const nodesOf = (entries: Record<string, Box>) => new Map(Object.entries(entries));
const edge = (id: string, source: string, target: string, label?: string): RouteEdge => ({ id, source, target, label });
const route = (r: EdgeRoute[], id: string) => r.find((x) => x.id === id)!;

/** The numbers of a path `M x y C x y, x y, x y`. */
const numbers = (path: string) => (path.match(/-?\d+(\.\d+)?/g) ?? []).map(Number);
const start = (path: string) => numbers(path).slice(0, 2);
const end = (path: string) => numbers(path).slice(-2);

const overlap = (a: Box, b: Box) => {
  const w = Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x);
  const h = Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y);
  return w > 0 && h > 0 ? w * h : 0;
};
const centre = (b: Box) => ({ x: b.x + b.width / 2, y: b.y + b.height / 2 });

/** A small deterministic generator, so a shuffle is the same on every run and machine. */
function seeded(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function shuffled<T>(list: T[], seed: number): T[] {
  const random = seeded(seed);
  const out = [...list];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

describe("the sides an edge attaches by", () => {
  const ns = nodesOf({ a: box(0, 0), b: box(300, 0), c: box(0, 100) });

  it("leaves a forward edge by the source's far side and enters by the target's near side, and its path starts and ends there", () => {
    const [r] = routeEdges(ns, [edge("e", "a", "b")], { direction: "LR" });
    expect([r.sourceSide, r.targetSide]).toEqual(["right", "left"]);
    expect(start(r.path)).toEqual([100, 20]);
    expect(end(r.path)).toEqual([300, 20]);
  });

  it("leaves a backward edge by the source's near side and enters by the target's far side, so it never wraps around its node", () => {
    const [r] = routeEdges(ns, [edge("e", "b", "a")], { direction: "LR" });
    expect([r.sourceSide, r.targetSide]).toEqual(["left", "right"]);
    expect(start(r.path)).toEqual([300, 20]);
    expect(end(r.path)).toEqual([100, 20]);
    // The curve runs from the source to the target within the gap between them, never beyond either node.
    for (let t = 0; t <= 1; t += 0.05) {
      const p = curvePoint(r.curve, t);
      expect(p.x).toBeGreaterThanOrEqual(100);
      expect(p.x).toBeLessThanOrEqual(300);
    }
  });

  it("uses the top and bottom sides, whichever faces the other node, for two nodes in one rank", () => {
    const [down] = routeEdges(ns, [edge("e", "a", "c")], { direction: "LR" });
    expect([down.sourceSide, down.targetSide]).toEqual(["bottom", "top"]);
    expect(start(down.path)).toEqual([50, 40]);
    expect(end(down.path)).toEqual([50, 100]);
    const [up] = routeEdges(ns, [edge("e", "c", "a")], { direction: "LR" });
    expect([up.sourceSide, up.targetSide]).toEqual(["top", "bottom"]);
    expect(start(up.path)).toEqual([50, 100]);
    expect(end(up.path)).toEqual([50, 40]);
  });

  it("takes a node whose extent along the direction overlaps the source's as in its rank, though it was dragged a little", () => {
    expect(chooseSides(box(0, 0), box(60, 100), "LR")).toEqual(["bottom", "top"]);
    expect(chooseSides(box(0, 0), box(100, 100), "LR")).toEqual(["right", "left"]);
  });

  it("turns the rule through a quarter for TB", () => {
    const tb = nodesOf({ a: box(0, 0), b: box(0, 200), c: box(200, 0) });
    expect(chooseSides(tb.get("a")!, tb.get("b")!, "TB")).toEqual(["bottom", "top"]);
    expect(chooseSides(tb.get("b")!, tb.get("a")!, "TB")).toEqual(["top", "bottom"]);
    expect(chooseSides(tb.get("a")!, tb.get("c")!, "TB")).toEqual(["right", "left"]);
    expect(chooseSides(tb.get("c")!, tb.get("a")!, "TB")).toEqual(["left", "right"]);
    const [r] = routeEdges(tb, [edge("e", "a", "b")], { direction: "TB" });
    expect(start(r.path)).toEqual([50, 40]);
    expect(end(r.path)).toEqual([50, 200]);
  });

  it("draws an edge from a node to itself as a loop on one side", () => {
    const [r] = routeEdges(nodesOf({ a: box(0, 0) }), [edge("e", "a", "a", "ex:self")], { direction: "LR" });
    expect([r.sourceSide, r.targetSide]).toEqual(["right", "right"]);
    expect(start(r.path)[0]).toBe(100);
    expect(end(r.path)[0]).toBe(100);
    expect(start(r.path)).not.toEqual(end(r.path));
    expect(curvePoint(r.curve, 0.5).x).toBeGreaterThan(100);
  });

  it("leaves out an edge whose node is not given", () => {
    expect(routeEdges(ns, [edge("e", "a", "ghost"), edge("f", "a", "b")]).map((r) => r.id)).toEqual(["f"]);
  });
});

describe("the point on a path", () => {
  it("is the start at 0 and the end at 1, and the middle of a straight run at 0.5", () => {
    const [r] = routeEdges(nodesOf({ a: box(0, 0), b: box(300, 0) }), [edge("e", "a", "b")]);
    expect(curvePoint(r.curve, 0)).toEqual({ x: 100, y: 20 });
    expect(curvePoint(r.curve, 1)).toEqual({ x: 300, y: 20 });
    expect(curvePoint(r.curve, 0.5)).toEqual({ x: 200, y: 20 });
  });
});

describe("edges between one pair of nodes", () => {
  const ns = nodesOf({ a: box(0, 0), b: box(300, 100) });
  const gap = (x: EdgeRoute, y: EdgeRoute) => {
    const d = [0.1, 0.3, 0.5, 0.7, 0.9].map((t) => {
      const p = curvePoint(x.curve, t);
      const q = curvePoint(y.curve, t);
      return Math.hypot(p.x - q.x, p.y - q.y);
    });
    return Math.min(...d);
  };

  it("attach at different points of the side, in the same direction", () => {
    const r = routeEdges(ns, [edge("e2", "a", "b"), edge("e1", "a", "b")]);
    expect(start(route(r, "e1").path)).not.toEqual(start(route(r, "e2").path));
    expect(end(route(r, "e1").path)).not.toEqual(end(route(r, "e2").path));
    expect(gap(route(r, "e1"), route(r, "e2"))).toBeGreaterThan(8);
  });

  it("attach at different points of the side, in opposite directions", () => {
    const r = routeEdges(ns, [edge("f", "a", "b"), edge("g", "b", "a")]);
    const [f, g] = [route(r, "f"), route(r, "g")];
    expect([f.sourceSide, f.targetSide]).toEqual(["right", "left"]);
    expect([g.sourceSide, g.targetSide]).toEqual(["left", "right"]);
    expect(start(f.path)).not.toEqual(end(g.path));
    expect(end(f.path)).not.toEqual(start(g.path));
    expect(gap(f, g)).toBeGreaterThan(8);
  });

  it("stay centred on the side's middle and are kept in order of id, whichever order they are given in", () => {
    const r = routeEdges(ns, [edge("e3", "a", "b"), edge("e1", "a", "b"), edge("e2", "a", "b")]);
    const ys = ["e1", "e2", "e3"].map((id) => start(route(r, id).path)[1]);
    expect(ys[1]).toBe(20);
    expect(ys[0]).toBeLessThan(ys[1]);
    expect(ys[2]).toBeGreaterThan(ys[1]);
    expect(ys.every((y) => y >= 0 && y <= 40)).toBe(true);
  });

  it("do not move an edge that has no other between its pair", () => {
    const r = routeEdges(nodesOf({ a: box(0, 0), b: box(300, 0), c: box(300, 100) }), [edge("e1", "a", "b"), edge("e2", "a", "c")]);
    expect(start(route(r, "e1").path)).toEqual([100, 20]);
    expect(start(route(r, "e2").path)).toEqual([100, 20]);
  });
});

describe("a label", () => {
  const width = (text: string, o = { labelCharWidth: 6.5, labelPadding: 7 }) => text.length * o.labelCharWidth + 2 * o.labelPadding;

  it("sits at t = 0.5 when nothing is in the way, and is as wide as its text and padding", () => {
    const [r] = routeEdges(nodesOf({ a: box(0, 0), b: box(400, 0) }), [edge("e", "a", "b", "ex:p")]);
    const c = centre(r.label!);
    const p = curvePoint(r.curve, 0.5);
    expect(c.x).toBeCloseTo(p.x, 9);
    expect(c.y).toBeCloseTo(p.y, 9);
    expect(r.label!.width).toBeCloseTo(width("ex:p"), 9);
    expect(r.label!.height).toBe(21);
  });

  it("uses the width and height it is given", () => {
    const [r] = routeEdges(nodesOf({ a: box(0, 0), b: box(400, 0) }), [edge("e", "a", "b", "abcd")], { labelCharWidth: 10, labelPadding: 3, labelHeight: 30 });
    expect([r.label!.width, r.label!.height]).toEqual([46, 30]);
  });

  it("takes the default for an option given as undefined", () => {
    const ns = nodesOf({ a: box(0, 0), b: box(400, 0) });
    expect(routeEdges(ns, [edge("e", "a", "b", "ex:p")], { direction: undefined, labelCharWidth: undefined, labelHeight: undefined, labelPadding: undefined })).toEqual(routeEdges(ns, [edge("e", "a", "b", "ex:p")]));
  });

  it("has none for an edge with no label", () => {
    expect(routeEdges(nodesOf({ a: box(0, 0), b: box(400, 0) }), [edge("e", "a", "b")])[0].label).toBeUndefined();
  });

  it("moves off a node box that covers t = 0.5, to another point of its edge", () => {
    const ns = nodesOf({ a: box(0, 0), b: box(400, 0), block: box(210, -30, 80, 100) });
    const [r] = routeEdges(ns, [edge("e", "a", "b", "ex:p")]);
    expect(overlap(r.label!, ns.get("block")!)).toBe(0);
    const c = centre(r.label!);
    const at = LABEL_CANDIDATES.filter((t) => Math.abs(curvePoint(r.curve, t).x - c.x) < 1e-9 && Math.abs(curvePoint(r.curve, t).y - c.y) < 1e-9);
    expect(at).toHaveLength(1);
    expect(at[0]).not.toBe(0.5);
  });

  it("keeps the labels of two crossing edges apart, where both would sit on the crossing", () => {
    const ns = nodesOf({ a: box(0, 0), b: box(0, 100), c: box(400, 0), d: box(400, 100) });
    const r = routeEdges(ns, [edge("e1", "a", "d", "ex:first"), edge("e2", "b", "c", "ex:second")]);
    const [one, two] = [route(r, "e1").label!, route(r, "e2").label!];
    // The curves cross at their middles, so the first takes t = 0.5 and the second must move.
    expect(centre(one)).toEqual(curvePoint(route(r, "e1").curve, 0.5));
    expect(overlap(one, two)).toBe(0);
    expect(centre(two)).not.toEqual(curvePoint(route(r, "e2").curve, 0.5));
  });

  it("takes the place with the least overlap when no place is free, ties by the order of preference", () => {
    // A label wider than the gap covers both nodes wherever it sits, so the candidates differ only in how much it covers.
    const ns = nodesOf({ a: box(0, 0), b: box(200, 0), c: box(100, 60, 60, 60) });
    const text = "x".repeat(60);
    const [r] = routeEdges(ns, [edge("e", "a", "b", text)]);
    const w = width(text);
    const cost = (t: number) => {
      const p = curvePoint(r.curve, t);
      const b = { x: p.x - w / 2, y: p.y - 10.5, width: w, height: 21 };
      return [...ns.values()].reduce((sum, n) => sum + overlap(b, n), 0);
    };
    expect(LABEL_CANDIDATES.every((t) => cost(t) > 0)).toBe(true);
    const least = Math.min(...LABEL_CANDIDATES.map(cost));
    const expected = LABEL_CANDIDATES.find((t) => cost(t) === least)!;
    const p = curvePoint(r.curve, expected);
    expect(r.label).toEqual({ x: p.x - w / 2, y: p.y - 10.5, width: w, height: 21 });
  });

  it("counts the labels already placed in the fallback", () => {
    // Two edges with one wide label each, on one pair, in a space no label fits. A result is returned for both.
    const ns = nodesOf({ a: box(0, 0), b: box(200, 0) });
    const text = "y".repeat(50);
    const r = routeEdges(ns, [edge("e1", "a", "b", text), edge("e2", "a", "b", text)]);
    expect(r.every((x) => x.label !== undefined)).toBe(true);
    expect(r[0].label).not.toEqual(r[1].label);
  });
});

describe("determinism", () => {
  const ns = nodesOf({ a: box(0, 0), b: box(300, 0), c: box(300, 100), d: box(600, 50), e: box(0, 100) });
  const es = [
    edge("e01", "a", "b", "ex:one"), edge("e02", "b", "a", "ex:two"), edge("e03", "a", "c", "ex:three"), edge("e04", "c", "d", "ex:four"),
    edge("e05", "d", "a", "ex:five"), edge("e06", "e", "d", "ex:six"), edge("e07", "e", "e", "ex:seven"), edge("e08", "b", "c"),
  ];

  it("gives the same paths and labels for any order of the nodes and edges, and on a repeat", () => {
    const base = routeEdges(ns, es);
    for (const seed of [1, 2, 3, 4, 5]) {
      const reordered = new Map(shuffled([...ns.entries()], seed));
      expect(routeEdges(reordered, shuffled(es, seed + 10))).toEqual(base);
    }
    expect(routeEdges(ns, es)).toEqual(base);
    expect(base.map((r) => r.id)).toEqual(es.map((x) => x.id).sort());
  });
});

describe("the facility sample on the ontology canvas", () => {
  const samples = join(__dirname, "../../../../contracts/config-studio/samples");
  const read = (name: string) => Graph.parse(readFileSync(join(samples, name), "utf-8"));

  for (const shapes of [false, true]) {
    it(`covers no node and no other label with any label, with shapes ${shapes ? "on" : "off"}`, () => {
      // As OntologyCanvas draws it, the lending baseline with the facility baseline over it, laid out by the kit with the canvas's
      // options and drawn at the default node size.
      const g = read("lending-baseline.ttl").merge(read("facility-baseline.ttl"));
      const drawn = classGraph(g, { shapes });
      const prefixes = { ...PREFIXES, ...g.prefixes };
      const layout = LAYOUTS.classes;
      const at = layered(drawn.nodes.map((n) => ({ id: n.iri })), drawn.edges.map((e) => ({ source: e.source, target: e.target })), layout);
      const boxes = new Map(drawn.nodes.map((n) => [n.iri, { ...at.get(n.iri)!, ...DEFAULT_NODE_SIZE }]));
      const routes = routeEdges(boxes, drawn.edges.map((e) => edge(e.id, e.source, e.target, compact(e.property, prefixes))), { direction: layout.direction });
      expect(routes).toHaveLength(drawn.edges.length);
      expect(routes.length).toBeGreaterThan(0);
      const labels = routes.map((r) => ({ id: r.id, box: r.label! }));
      for (const l of labels) {
        expect(l.box, l.id).toBeDefined();
        for (const [iri, n] of boxes) expect(overlap(l.box, n), `${l.id} on ${iri}`).toBe(0);
      }
      for (let i = 0; i < labels.length; i++) {
        for (let j = i + 1; j < labels.length; j++) expect(overlap(labels[i].box, labels[j].box), `${labels[i].id} on ${labels[j].id}`).toBe(0);
      }
    });
  }
});
