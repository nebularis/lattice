// SPDX-License-Identifier: MPL-2.0
// The kit's edge routes are a pure function of the node boxes and the edges (SVA-O2a). The sides an edge attaches by, a pair of
// edges kept apart, a label kept off every node and every other label, the fallback when no place is free, the same result for any
// order of the input, and the facility sample drawn as the ontology canvas draws it.

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { Graph, PREFIXES, compact } from "@lattice/authoring-domain";
import { LAYOUTS } from "../ui/OntologyCanvas";
import { importGraph } from "../rdf/importGraph";
import { classGraph, hierarchyGraph } from "../rdf/ontologyGraph";
import { CLEARANCE, DEFAULT_NODE_SIZE, DEFAULT_ROUTE_OPTIONS, LABEL_CANDIDATES, LOOP_REACH, acrossSides, chooseSides, curvePoint, labelWidth, loopRoom, loopSide, loopSpan, routeEdges, type Box, type Curve, type EdgeRoute, type RouteEdge } from "./edges";
import { layered, type LayoutEdge, type LayoutOptions } from "./layout";

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
/** The distance from a point to a box, 0 inside it. */
const distanceTo = (p: { x: number; y: number }, b: Box) => Math.hypot(Math.max(b.x - p.x, 0, p.x - (b.x + b.width)), Math.max(b.y - p.y, 0, p.y - (b.y + b.height)));
/** Points of a path about a pixel apart. */
function along(path: Curve[], each = 1): { x: number; y: number }[] {
  const out = [path[0].p0];
  for (const c of path) {
    const n = Math.ceil((Math.hypot(c.p1.x - c.p0.x, c.p1.y - c.p0.y) + Math.hypot(c.p2.x - c.p1.x, c.p2.y - c.p1.y) + Math.hypot(c.p3.x - c.p2.x, c.p3.y - c.p2.y)) / each);
    for (let k = 1; k <= n; k++) out.push(curvePoint(c, k / n));
  }
  return out;
}
/** The nearest a route comes to a node box that is not one of its two ends, with its id, over points a pixel apart. */
function nearest(r: EdgeRoute, e: RouteEdge, boxes: ReadonlyMap<string, Box>): { id: string; distance: number } {
  const pts = along(r.curve);
  let best = { id: "", distance: Infinity };
  for (const [id, b] of boxes) {
    if (id === e.source || id === e.target) continue;
    const d = Math.min(...pts.map((p) => distanceTo(p, b)));
    if (d < best.distance) best = { id, distance: d };
  }
  return best;
}
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

  it("leaves out an edge whose node is not given", () => {
    expect(routeEdges(ns, [edge("e", "a", "ghost"), edge("f", "a", "b")]).map((r) => r.id)).toEqual(["f"]);
  });
});

describe("a loop, an edge from a node to itself", () => {
  const label = "ex:refinancesInChain";
  const one = (direction: "LR" | "TB", extra: Record<string, Box> = {}, edges: RouteEdge[] = [edge("e", "a", "a", label)]) => routeEdges(nodesOf({ a: box(0, 0), ...extra }), edges, { direction });
  /** The nearest the curve of a loop comes to a node, over points a pixel apart. */
  const near = (r: EdgeRoute, b: Box) => Math.min(...along(r.curve).map((p) => distanceTo(p, b)));

  it("leaves and enters by one side across the layout's flow, the top in LR and the left in TB on a tie", () => {
    const [lr] = one("LR");
    expect([lr.sourceSide, lr.targetSide]).toEqual(["top", "top"]);
    expect(start(lr.path)[1]).toBe(0);
    expect(end(lr.path)[1]).toBe(0);
    expect(start(lr.path)).not.toEqual(end(lr.path));
    expect(curvePoint(lr.curve, 0.5).y).toBeLessThan(0);
    const [tb] = one("TB");
    expect([tb.sourceSide, tb.targetSide]).toEqual(["left", "left"]);
    expect(start(tb.path)[0]).toBe(0);
    expect(end(tb.path)[0]).toBe(0);
    expect(curvePoint(tb.curve, 0.5).x).toBeLessThan(0);
    expect(acrossSides("LR")).toEqual(["top", "bottom"]);
    expect(acrossSides("TB")).toEqual(["left", "right"]);
  });

  it("takes the side with fewer edge ends on the node, and the first on a tie, by a rule that reads the ends only", () => {
    expect(loopSide("LR", 0, 0)).toBe("top");
    expect(loopSide("LR", 1, 1)).toBe("top");
    expect(loopSide("LR", 1, 2)).toBe("top");
    expect(loopSide("LR", 2, 1)).toBe("bottom");
    expect(loopSide("TB", 0, 0)).toBe("left");
    expect(loopSide("TB", 3, 1)).toBe("right");
  });

  it("takes the bottom in LR where more edges end on the top of the node, as when other nodes of its rank lie above it", () => {
    // Two nodes of a rank lie above the node, so two edges end on its top, and its loop takes the bottom.
    const ns = nodesOf({ a: box(0, 200), b: box(0, 0), c: box(0, 100) });
    const loops = routeEdges(ns, [edge("l", "a", "a", label), edge("ab", "a", "b"), edge("ac", "a", "c")], { direction: "LR" });
    expect(route(loops, "ab").sourceSide).toBe("top");
    expect(route(loops, "ac").sourceSide).toBe("top");
    expect([route(loops, "l").sourceSide, route(loops, "l").targetSide]).toEqual(["bottom", "bottom"]);
    expect(start(route(loops, "l").path)[1]).toBe(240);
    // With one end on each side the loop is on the top, and with fewer on the top than the bottom it is on the top.
    const tie = routeEdges(nodesOf({ a: box(0, 100), b: box(0, 0), c: box(0, 200) }), [edge("l", "a", "a", label), edge("ab", "a", "b"), edge("ac", "a", "c")], { direction: "LR" });
    expect(route(tie, "l").sourceSide).toBe("top");
    // An edge that ends on the node by the other end counts as an end there as well.
    const into = routeEdges(ns, [edge("l", "a", "a", label), edge("ba", "b", "a"), edge("ca", "c", "a")], { direction: "LR" });
    expect(route(into, "ba").targetSide).toBe("top");
    expect(route(into, "l").sourceSide).toBe("bottom");
  });

  it("takes the right in TB where more edges end on the left of the node", () => {
    const ns = nodesOf({ a: box(400, 0), b: box(0, 0), c: box(200, 0) });
    const r = routeEdges(ns, [edge("l", "a", "a", label), edge("ab", "a", "b"), edge("ac", "a", "c")], { direction: "TB" });
    expect(route(r, "ab").sourceSide).toBe("left");
    expect([route(r, "l").sourceSide, route(r, "l").targetSide]).toEqual(["right", "right"]);
    expect(curvePoint(route(r, "l").curve, 0.5).x).toBeGreaterThan(400 + 100);
  });

  it("is not moved by the edges that end on the sides along the flow, which are the sides edges between ranks use", () => {
    const lr = routeEdges(nodesOf({ a: box(200, 0), b: box(0, 0), c: box(500, 0) }), [edge("l", "a", "a", label), edge("ab", "b", "a"), edge("ac", "a", "c")], { direction: "LR" });
    expect([route(lr, "ab").targetSide, route(lr, "ac").sourceSide]).toEqual(["left", "right"]);
    expect(route(lr, "l").sourceSide).toBe("top");
  });

  it("lays the loops of one node side by side on that side, each with its own label, and no loop over another's label", () => {
    for (const direction of ["LR", "TB"] as const) {
      // Labels as wide as the facility class graph's, which an outer loop of a nested stack would cross.
      const rs = one(direction, {}, [edge("e", "a", "a", "ex:refinances"), edge("f", "a", "a", "ex:refinancesInChain"), edge("g", "a", "a", "ex:third")]);
      expect(new Set(rs.map((r) => r.sourceSide)).size).toBe(1);
      const lr = direction === "LR";
      const along = (p: { x: number; y: number }) => (lr ? p.x : p.y);
      // Each loop has its own part of the side, in order of id, and reaches as far out as the others.
      const spans = rs.map((r) => [along(r.curve[0].p0), along(r.curve[0].p3)].sort((x, y) => x - y));
      for (let i = 1; i < spans.length; i++) expect(spans[i][0]).toBeGreaterThan(spans[i - 1][1]);
      const far = rs.map((r) => (lr ? -curvePoint(r.curve, 0.5).y : -curvePoint(r.curve, 0.5).x));
      for (const f of far) expect(f).toBeCloseTo(far[0], 5);
      for (const r of rs) expect(overlap(r.label!, box(0, 0))).toBe(0);
      for (let i = 0; i < rs.length; i++) for (let j = i + 1; j < rs.length; j++) expect(overlap(rs[i].label!, rs[j].label!)).toBe(0);
      expect(rs.every((r) => near(r, box(0, 0)) === 0)).toBe(true);
      // No loop passes through the label of another.
      for (const r of rs) {
        for (const other of rs) {
          if (other === r) continue;
          for (let t = 0; t <= 1; t += 0.01) {
            const p = curvePoint(r.curve, t);
            const inside = p.x > other.label!.x && p.x < other.label!.x + other.label!.width && p.y > other.label!.y && p.y < other.label!.y + other.label!.height;
            expect(inside, `${r.id} through the label of ${other.id} in ${direction}`).toBe(false);
          }
        }
      }
    }
  });

  it("divides the side among its loops, one loop taking the middle half", () => {
    expect(loopSpan(200, 1, 0)).toEqual([-50, 50]);
    const two = [loopSpan(200, 2, 0), loopSpan(200, 2, 1)];
    expect(two[0][0]).toBeCloseTo(-75 + 7.5, 5);
    expect(two[0][1]).toBeLessThan(two[1][0]);
    expect(two[1][1]).toBeCloseTo(75 - 7.5, 5);
  });

  it("puts the label of a loop just beyond the loop's far point, on the side it leaves by, and clear of the node", () => {
    const [lr] = one("LR");
    const farLR = curvePoint(lr.curve, 0.5);
    // The loop leaves the top, so the label lies above its far point and covers nothing of the node.
    expect(lr.label!.y + lr.label!.height).toBeLessThan(farLR.y);
    expect(lr.label!.x + lr.label!.width / 2).toBeCloseTo(farLR.x, 5);
    expect(overlap(lr.label!, box(0, 0))).toBe(0);
    const [tb] = one("TB");
    const farTB = curvePoint(tb.curve, 0.5);
    expect(tb.label!.x + tb.label!.width).toBeLessThan(farTB.x);
    expect(tb.label!.y + tb.label!.height / 2).toBeCloseTo(farTB.y, 5);
    expect(overlap(tb.label!, box(0, 0))).toBe(0);
  });

  it("puts a label over no node of the drawing, moving it along the side where a node is there", () => {
    // A node above the loop's node, a little to its right, in the way of the label's first place.
    const blocker = box(40, -150, 100, 60);
    const [r] = routeEdges(nodesOf({ a: box(0, 0), z: blocker }), [edge("e", "a", "a", label)], { direction: "LR" });
    expect(overlap(r.label!, blocker)).toBe(0);
    expect(overlap(r.label!, box(0, 0))).toBe(0);
    expect(r.label!.y + r.label!.height).toBeLessThan(0);
  });

  it("gives the same routes for any order of the nodes and the edges", () => {
    const ns = nodesOf({ a: box(0, 200), b: box(0, 0), c: box(0, 100) });
    const es = [edge("l", "a", "a", label), edge("m", "a", "a", "ex:two"), edge("ab", "a", "b"), edge("c", "c", "c", "ex:own")];
    const first = routeEdges(ns, es, { direction: "LR" });
    for (const seed of [1, 2, 3]) expect(routeEdges(new Map(shuffled([...ns.entries()], seed)), shuffled(es, seed + 9), { direction: "LR" })).toEqual(first);
  });

  it("is given room by the layout, which reads the same numbers", () => {
    expect(loopRoom(0, 21)).toBe(0);
    expect(loopRoom(1, 21)).toBeCloseTo(0.75 * LOOP_REACH + 6 + 21 + CLEARANCE, 5);
    // Each further loop beside it may put its label one label further out.
    expect(loopRoom(2, 21) - loopRoom(1, 21)).toBeCloseTo(21 + 6, 5);
    expect(labelWidth("ex:a", DEFAULT_ROUTE_OPTIONS)).toBe(4 * DEFAULT_ROUTE_OPTIONS.labelCharWidth + 2 * DEFAULT_ROUTE_OPTIONS.labelPadding);
  });
});

describe("the layout leaves room for the loops", () => {
  const label = "ex:refinancesInChain";
  const SIZE = { width: 240, height: 51 };
  /** A hub with a rank of `n` nodes after it, a column in LR and a row in TB, and the loops on some of them. */
  function column(n: number, loops: Record<number, number>, options: LayoutOptions) {
    const ids = Array.from({ length: n }, (_, i) => `n${i}`);
    const nodes = [{ id: "hub", ...SIZE }, ...ids.map((id) => ({ id, ...SIZE }))];
    const edges: (LayoutEdge & { id: string })[] = ids.map((id) => ({ id: `h-${id}`, source: "hub", target: id }));
    ids.forEach((id, i) => {
      for (let k = 0; k < (loops[i] ?? 0); k++) edges.push({ id: `l-${id}-${k}`, source: id, target: id, label: k === 0 ? label : `ex:loop${k}` });
    });
    const at = layered(nodes, edges, options);
    const boxes = new Map(nodes.map((nd) => [nd.id, { ...at.get(nd.id)!, ...SIZE }]));
    const routes = routeEdges(boxes, edges.map((e) => edge(e.id, e.source, e.target, e.label)), { direction: options.direction });
    return { boxes, routes, edges, ids };
  }
  const gaps = [0, 14, 30, 84, 280];
  const reaches = (r: EdgeRoute, b: Box) => Math.min(...along(r.curve).map((p) => distanceTo(p, b)));

  for (const direction of ["LR", "TB"] as const) {
    for (const rowGap of gaps) {
      for (const columnGap of [14, 160]) {
        it(`keeps every loop and its label clear of the other nodes, in ${direction} with a row gap of ${rowGap} and a column gap of ${columnGap}`, () => {
          const { boxes, routes, ids } = column(6, { 1: 2, 3: 1, 4: 3 }, { direction, columnGap, rowGap });
          const loops = routes.filter((r) => r.sourceSide === r.targetSide && r.id.startsWith("l-"));
          expect(loops).toHaveLength(6);
          for (const r of loops) {
            const own = r.id.split("-")[1];
            for (const [id, b] of boxes) {
              if (id === own) continue;
              expect(reaches(r, b), `the loop ${r.id} by ${id}`).toBeGreaterThanOrEqual(CLEARANCE - 1);
              expect(overlap(r.label!, b), `the label of ${r.id} on ${id}`).toBe(0);
            }
          }
          // And over no other label of the drawing.
          const labels = routes.filter((r) => r.label).map((r) => r.label!);
          for (let i = 0; i < labels.length; i++) for (let j = i + 1; j < labels.length; j++) expect(overlap(labels[i], labels[j])).toBe(0);
          expect(ids).toHaveLength(6);
        });
      }
    }
  }

  it("grows the gap on the loop's side by the loops' reach, and only there", () => {
    const options: LayoutOptions = { direction: "LR", columnGap: 160, rowGap: 14 };
    const plain = column(4, {}, options);
    const looped = column(4, { 1: 2 }, options);
    const top = (c: ReturnType<typeof column>, id: string) => c.boxes.get(id)!.y;
    // n0 does not move, the gap above n1 holds its two loops and their labels, and the nodes after n1 move on with it.
    expect(top(looped, "n0")).toBe(top(plain, "n0"));
    const gap = top(looped, "n1") - (top(looped, "n0") + SIZE.height);
    expect(gap).toBeGreaterThanOrEqual(loopRoom(2, DEFAULT_ROUTE_OPTIONS.labelHeight));
    expect(top(looped, "n2") - top(looped, "n1")).toBe(top(plain, "n2") - top(plain, "n1"));
    expect(top(looped, "n2") - top(plain, "n2")).toBe(top(looped, "n1") - top(plain, "n1"));
    // A node with no loop leaves the gaps of a layout without loops as they were.
    expect(top(plain, "n1") - (top(plain, "n0") + SIZE.height)).toBe(14);
  });

  it("is the layout it was where no node has a loop", () => {
    const nodes = ["a", "b", "c", "d"].map((id) => ({ id, ...SIZE }));
    const edges = [edge("1", "a", "b"), edge("2", "a", "c"), edge("3", "b", "d")].map(({ source, target }) => ({ source, target }));
    const options: LayoutOptions = { direction: "LR", columnGap: 160, rowGap: 14 };
    const before = layered(nodes, edges, options);
    expect([...before.entries()]).toEqual([...layered(nodes, [...edges, { source: "z", target: "z" }], options).entries()]);
  });

  it("gives a node alone with a loop room for it among the nodes alone", () => {
    const options: LayoutOptions = { direction: "LR", columnGap: 160, rowGap: 14 };
    const nodes = ["a", "b", "c", "d"].map((id) => ({ id, ...SIZE }));
    const edges: LayoutEdge[] = [{ source: "b", target: "b", label }, { source: "c", target: "c", label }];
    const at = layered(nodes, edges, options);
    const boxes = new Map(nodes.map((n) => [n.id, { ...at.get(n.id)!, ...SIZE }]));
    const routes = routeEdges(boxes, edges.map((e, i) => edge(`l${i}`, e.source, e.target, e.label)), { direction: "LR" });
    for (const r of routes) {
      for (const [id, b] of boxes) {
        if (id !== (r.id === "l0" ? "b" : "c")) expect(overlap(r.label!, b), `${r.id} on ${id}`).toBe(0);
      }
    }
  });

  it("holds at the persistence canvas's smallest row gap with the widest labels of the facility", () => {
    const options: LayoutOptions = { direction: "LR", columnGap: 160, rowGap: 14 };
    const { boxes, routes } = column(5, { 0: 1, 1: 1, 2: 1, 3: 1, 4: 1 }, options);
    for (const r of routes.filter((x) => x.id.startsWith("l-"))) {
      const own = r.id.split("-")[1];
      for (const [id, b] of boxes) {
        if (id === own) continue;
        expect(overlap(r.label!, b)).toBe(0);
        expect(reaches(r, b)).toBeGreaterThanOrEqual(CLEARANCE - 1);
      }
    }
    // A column of nodes five deep, each with a loop, takes the room of five loops and no more than each needs.
    const top = [...boxes.values()].filter((b) => b.x > 0).map((b) => b.y).sort((a, b) => a - b);
    for (let i = 1; i < top.length; i++) expect(top[i] - top[i - 1]).toBeLessThanOrEqual(SIZE.height + loopRoom(1, DEFAULT_ROUTE_OPTIONS.labelHeight) + 1);
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

  it("spread the edges that share a side of a node, whatever their other ends are, not at its middle", () => {
    const r = routeEdges(nodesOf({ a: box(0, 0), b: box(300, 0), c: box(300, 100) }), [edge("e1", "a", "b"), edge("e2", "a", "c")]);
    const [one, two] = [start(route(r, "e1").path)[1], start(route(r, "e2").path)[1]];
    expect(one).not.toBe(two);
    expect(one).toBeGreaterThan(0);
    expect(two).toBeLessThan(40);
  });
});

describe("the attachment points on one side", () => {
  it("are distinct, inside the margins, and ordered by the position of the other end along the side", () => {
    const ns = nodesOf({ a: box(0, 150, 100, 60), t1: box(400, 0), t2: box(400, 100), t3: box(400, 200), t4: box(400, 300) });
    // Given in an order that is neither the ids' nor the targets'.
    const r = routeEdges(ns, [edge("e1", "a", "t4"), edge("e2", "a", "t1"), edge("e3", "a", "t3"), edge("e4", "a", "t2")]);
    const ys = ["e2", "e4", "e3", "e1"].map((id) => start(route(r, id).path)[1]);
    expect(new Set(ys).size).toBe(4);
    expect([...ys].sort((p, q) => p - q)).toEqual(ys);
    expect(ys.every((y) => y >= 150 + 8 && y <= 210 - 8)).toBe(true);
  });

  it("take both ends of edges that enter and leave by one side, in one order", () => {
    const ns = nodesOf({ a: box(0, 0), b: box(400, 0), c: box(0, 100) });
    const r = routeEdges(ns, [edge("e1", "a", "b"), edge("e2", "b", "a"), edge("e3", "c", "b")]);
    const ends = [start(route(r, "e1").path), end(route(r, "e2").path)];
    expect(ends[0]).not.toEqual(ends[1]);
  });
});

describe("routing around nodes", () => {
  // Three ranks along x. The middle one holds m1 and m2, with a gap between them, and the straight line from a to z runs through m1.
  const ns = nodesOf({ a: box(0, 60), z: box(600, 60), m1: box(300, 0, 100, 90), m2: box(300, 140, 100, 50) });
  const around = (rs: EdgeRoute[], e: RouteEdge) => nearest(route(rs, e.id), e, ns);

  it("takes an edge that would run through a node between its ends clear of it, by the free channel nearest the straight line", () => {
    const e = edge("e", "a", "z");
    const rs = routeEdges(ns, [e]);
    expect(around(rs, e).distance).toBeGreaterThanOrEqual(CLEARANCE - 1);
    // The straight line from the middle of a to the middle of z is y = 80, in m1, and the nearest free channel is the gap below it.
    const through = along(route(rs, "e").curve).filter((p) => p.x > 300 && p.x < 400);
    expect(through.length).toBeGreaterThan(0);
    expect(through.every((p) => p.y > 90 + CLEARANCE && p.y < 140 - CLEARANCE)).toBe(true);
  });

  it("goes round the rank, on the lower side at a tie, where no channel holds the line", () => {
    const wall = nodesOf({ a: box(0, 60), z: box(600, 60), m: box(300, 0, 100, 160) });
    const e = edge("e", "a", "z");
    const [r] = routeEdges(wall, [e]);
    expect(nearest(r, e, wall).distance).toBeGreaterThanOrEqual(CLEARANCE - 1);
    // The line is y = 80, 80 from each side of the wall, so the tie goes to the lower coordinate, above it.
    expect(along(r.curve).filter((p) => p.x > 300 && p.x < 400).every((p) => p.y < 0)).toBe(true);
  });

  it("gives two edges through one channel a lane each, a few pixels apart, in order of id", () => {
    const es = [edge("e2", "a", "z"), edge("e1", "a", "z")];
    const rs = routeEdges(ns, es);
    const lane = (id: string) => {
      const mid = along(route(rs, id).curve).filter((p) => Math.abs(p.x - 350) < 1);
      return mid[0].y;
    };
    expect(lane("e1")).toBeLessThan(lane("e2"));
    expect(lane("e2") - lane("e1")).toBeGreaterThanOrEqual(5);
    for (const e of es) expect(around(rs, e).distance).toBeGreaterThanOrEqual(CLEARANCE - 1);
  });

  it("returns a route where no channel clears every node, the one that comes least near", () => {
    // A wall that stands against a's side and reaches far up and down. Any route leaves a through the wall's clearance.
    const tight = nodesOf({ a: box(0, 0, 100, 40), z: box(600, 0, 100, 40), wall: box(104, -2000, 20, 4000) });
    const e = edge("e", "a", "z");
    const [r] = routeEdges(tight, [e, edge("x", "a", "z")]);
    expect(r.curve.length).toBeGreaterThan(0);
    expect(start(r.path)[0]).toBe(100);
    expect(end(r.path)[0]).toBe(600);
    expect(numbers(r.path).every(Number.isFinite)).toBe(true);
  });

  it("leaves no kink at a waypoint, the control points either side of it in line with it", () => {
    const [r] = routeEdges(ns, [edge("e", "a", "z")]);
    expect(r.curve.length).toBeGreaterThan(1);
    for (let i = 0; i + 1 < r.curve.length; i++) {
      const [before, after] = [r.curve[i], r.curve[i + 1]];
      expect(after.p0).toEqual(before.p3);
      const cross = (before.p3.x - before.p2.x) * (after.p1.y - before.p3.y) - (before.p3.y - before.p2.y) * (after.p1.x - before.p3.x);
      expect(Math.abs(cross)).toBeLessThan(1e-6);
      // And they lie on either side of it, so the path runs on through it.
      expect((before.p3.x - before.p2.x) * (after.p1.x - before.p3.x) + (before.p3.y - before.p2.y) * (after.p1.y - before.p3.y)).toBeGreaterThan(0);
    }
  });

  it("goes round a node between two nodes of one rank, on the side with less intrusion", () => {
    const column = nodesOf({ a: box(0, 0), m: box(0, 100), c: box(0, 200) });
    const e = edge("e", "a", "c");
    const [r] = routeEdges(column, [e]);
    expect(nearest(r, e, column).distance).toBeGreaterThanOrEqual(CLEARANCE - 1);
  });

  it("turns the same rule through a quarter for TB", () => {
    const tb = nodesOf({ a: box(60, 0), z: box(60, 600), m1: box(0, 300, 120, 100), m2: box(150, 300, 50, 100) });
    const e = edge("e", "a", "z");
    const [r] = routeEdges(tb, [e], { direction: "TB" });
    expect(nearest(r, e, tb).distance).toBeGreaterThanOrEqual(CLEARANCE - 1);
    expect(r.curve.length).toBeGreaterThan(1);
  });
});

describe("a label on a path of several segments", () => {
  it("sits at one of the candidate fractions along the whole path, on the path, and off every node", () => {
    const ns = nodesOf({ a: box(0, 60), z: box(600, 60), m1: box(300, 0, 100, 90), m2: box(300, 140, 100, 50) });
    const [r] = routeEdges(ns, [edge("e", "a", "z", "ex:p")]);
    expect(r.curve.length).toBeGreaterThan(1);
    const c = centre(r.label!);
    const pts = along(r.curve, 0.5);
    expect(Math.min(...pts.map((p) => Math.hypot(p.x - c.x, p.y - c.y)))).toBeLessThan(0.5);
    for (const [, b] of ns) expect(overlap(r.label!, b)).toBe(0);
    // The ends are the path's ends, and the middle is as far along as the start is from the end by arc length.
    expect(curvePoint(r.curve, 0)).toEqual(r.curve[0].p0);
    expect(curvePoint(r.curve, 1)).toEqual(r.curve[r.curve.length - 1].p3);
    const half = curvePoint(r.curve, 0.5);
    const arc = (to: { x: number; y: number }) => {
      let sum = 0;
      for (let i = 1; i < pts.length; i++) {
        sum += Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y);
        if (Math.hypot(pts[i].x - to.x, pts[i].y - to.y) < 0.6) return sum;
      }
      return NaN;
    };
    const total = pts.reduce((sum, p, i) => (i ? sum + Math.hypot(p.x - pts[i - 1].x, p.y - pts[i - 1].y) : 0), 0);
    expect(arc(half) / total).toBeGreaterThan(0.48);
    expect(arc(half) / total).toBeLessThan(0.52);
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

describe("determinism of routed edges", () => {
  const ns = nodesOf({ a: box(0, 60), z: box(600, 60), y: box(600, 200), m1: box(300, 0, 100, 90), m2: box(300, 140, 100, 50), m3: box(300, 230, 100, 50) });
  const es = [edge("e1", "a", "z", "ex:one"), edge("e2", "a", "y", "ex:two"), edge("e3", "a", "z", "ex:three"), edge("e4", "y", "a", "ex:four"), edge("e5", "z", "a")];

  it("gives the same routes for any order of the nodes and the edges, and on a repeat", () => {
    const base = routeEdges(ns, es);
    expect(base.some((r) => r.curve.length > 1)).toBe(true);
    for (const seed of [1, 2, 3, 4, 5, 6]) expect(routeEdges(new Map(shuffled([...ns.entries()], seed)), shuffled(es, seed + 20))).toEqual(base);
    expect(routeEdges(ns, es)).toEqual(base);
  });
});

describe("the facility sample on the ontology canvas", () => {
  const samples = join(__dirname, "../../../../contracts/config-studio/samples");
  const read = (name: string) => Graph.parse(readFileSync(join(samples, name), "utf-8"));
  // As OntologyCanvas draws it, the lending baseline with the facility baseline over it, laid out by the kit with the canvas's
  // options, and drawn at the default node size, or at the size the import graph's nodes are given to the layout.
  const g = read("lending-baseline.ttl").merge(read("facility-baseline.ttl"));
  const prefixes = { ...PREFIXES, ...g.prefixes };

  type Drawing = { name: string; nodes: string[]; edges: RouteEdge[]; view: keyof typeof LAYOUTS; size: { width: number; height: number } };
  const drawings: Drawing[] = [];
  for (const shapes of [false, true]) {
    const drawn = classGraph(g, { shapes });
    drawings.push({ name: `the classes with shapes ${shapes ? "on" : "off"}`, view: "classes", size: DEFAULT_NODE_SIZE, nodes: drawn.nodes.map((n) => n.iri), edges: drawn.edges.map((e) => edge(e.id, e.source, e.target, compact(e.property, prefixes))) });
  }
  const tree = hierarchyGraph(g, {});
  // The hierarchy runs a superclass above its subclasses, so its edges are drawn from the target to the source.
  drawings.push({ name: "the class hierarchy", view: "hierarchy", size: DEFAULT_NODE_SIZE, nodes: tree.nodes.map((n) => n.iri), edges: tree.edges.map((e) => edge(e.id, e.target, e.source)) });
  const imports = importGraph({ baseline: g, held: [], vocabulary: read("facility-vocabulary.ttl") });
  drawings.push({ name: "the import graph", view: "imports", size: { width: 240, height: 76 }, nodes: imports.nodes.map((n) => n.id), edges: imports.edges.map((e) => edge(e.id, e.source, e.target, e.label)) });

  for (const d of drawings) {
    describe(d.name, () => {
      const layout = LAYOUTS[d.view];
      const at = layered(d.nodes.map((id) => ({ id, ...d.size })), d.edges.map((e) => ({ source: e.source, target: e.target, label: e.label })), layout);
      const boxes = new Map(d.nodes.map((id) => [id, { ...at.get(id)!, ...d.size }]));
      const routes = routeEdges(boxes, d.edges, { direction: layout.direction });

      it("has a route for every edge", () => {
        expect(routes).toHaveLength(d.edges.length);
        expect(routes.length).toBeGreaterThan(0);
      });

      it("draws the facility's two loops across the flow, clear of every other node", () => {
        const loops = d.edges.filter((e) => e.source === e.target);
        expect(loops).toHaveLength(d.view === "classes" ? 2 : 0);
        for (const e of loops) {
          const r = route(routes, e.id);
          expect([r.sourceSide, r.targetSide]).toEqual([r.sourceSide, r.sourceSide]);
          expect(["top", "bottom"]).toContain(r.sourceSide);
          for (const [id, b] of boxes) {
            if (id === e.source) continue;
            expect(overlap(r.label!, b), `${e.id} label on ${id}`).toBe(0);
            expect(distanceTo(curvePoint(r.curve, 0.5), b), `${e.id} by ${id}`).toBeGreaterThan(0);
          }
        }
      });

      it("passes within the clearance of no node but the two it joins", () => {
        for (const r of routes) {
          const near = nearest(r, d.edges.find((e) => e.id === r.id)!, boxes);
          expect(near.distance, `${r.id} by ${near.id}`).toBeGreaterThanOrEqual(CLEARANCE - 1);
        }
      });

      it("covers no node and no other label with any label", () => {
        const labels = routes.filter((r) => r.label).map((r) => ({ id: r.id, box: r.label! }));
        for (const l of labels) {
          for (const [iri, n] of boxes) expect(overlap(l.box, n), `${l.id} on ${iri}`).toBe(0);
        }
        for (let i = 0; i < labels.length; i++) {
          for (let j = i + 1; j < labels.length; j++) expect(overlap(labels[i].box, labels[j].box), `${labels[i].id} on ${labels[j].id}`).toBe(0);
        }
      });
    });
  }
});

describe("the label of an edge shorter than itself", () => {
  // Two nodes one above the other with a gap of 13, as the mapping canvas draws a mapping and its template.
  const wide = (x: number, y: number) => box(x, y, 240, 51);
  const stacked = () => nodesOf({ a: wide(0, 0), b: wide(0, 64) });
  const pathBox = (r: EdgeRoute): Box => {
    const pts = along(r.curve, 1);
    const xs = pts.map((p) => p.x);
    const ys = pts.map((p) => p.y);
    return { x: Math.min(...xs), y: Math.min(...ys), width: Math.max(...xs) - Math.min(...xs), height: Math.max(...ys) - Math.min(...ys) };
  };
  const length = (r: EdgeRoute) => Math.hypot(end(r.path)[0] - start(r.path)[0], end(r.path)[1] - start(r.path)[1]);

  it("is beside the edge and not on it, so the line stays visible", () => {
    const [r] = routeEdges(stacked(), [edge("e", "a", "b", "template")]);
    expect(length(r)).toBeLessThan(21);
    expect(overlap(r.label!, pathBox(r))).toBe(0);
    for (const p of along(r.curve, 1)) expect(p.x < r.label!.x || p.x > r.label!.x + r.label!.width || p.y < r.label!.y || p.y > r.label!.y + r.label!.height).toBe(true);
  });

  it("covers no node and no other label, the place beside it being free of both", () => {
    const ns = stacked();
    const r = routeEdges(ns, [edge("e", "a", "b", "template"), edge("f", "a", "b", "template")]);
    for (const x of r) for (const [, b] of ns) expect(overlap(x.label!, b)).toBe(0);
    expect(overlap(r[0].label!, r[1].label!)).toBe(0);
    for (const x of r) expect(overlap(x.label!, pathBox(x))).toBe(0);
  });

  it("takes the right side of a path that runs down, and the left where the right is taken by a node", () => {
    const [free] = routeEdges(stacked(), [edge("e", "a", "b", "template")]);
    expect(centre(free.label!).x).toBeGreaterThan(centre(wide(0, 0)).x);
    const blocked = nodesOf({ a: wide(0, 0), b: wide(0, 64), c: box(250, 0, 300, 115) });
    const [r] = routeEdges(blocked, [edge("e", "a", "b", "template")]);
    expect(centre(r.label!).x).toBeLessThan(0);
    for (const [, b] of blocked) expect(overlap(r.label!, b)).toBe(0);
    expect(overlap(r.label!, pathBox(r))).toBe(0);
  });

  it("is on the path of an edge as long as its label, as before", () => {
    const [r] = routeEdges(nodesOf({ a: wide(0, 0), b: wide(0, 300) }), [edge("e", "a", "b", "template")]);
    const c = centre(r.label!);
    const p = curvePoint(r.curve, 0.5);
    expect([c.x, c.y]).toEqual([p.x, p.y]);
  });

  it("is on the path of an edge between two ranks that is longer than its label", () => {
    const [r] = routeEdges(nodesOf({ a: box(0, 0), b: box(200, 0) }), [edge("e", "a", "b", "template")]);
    const c = centre(r.label!);
    const p = curvePoint(r.curve, 0.5);
    expect([c.x, c.y]).toEqual([p.x, p.y]);
  });

  it("gives the same labels for any order of the nodes and the edges, and on a repeat", () => {
    const ns = stacked();
    const es = [edge("e", "a", "b", "template"), edge("f", "a", "b", "source")];
    const first = routeEdges(ns, es);
    expect(routeEdges(new Map([...ns].reverse()), [...es].reverse())).toEqual(first);
    expect(routeEdges(ns, es)).toEqual(first);
  });
});
