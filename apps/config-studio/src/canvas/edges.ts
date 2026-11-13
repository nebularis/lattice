// SPDX-License-Identifier: MPL-2.0
// The canvas kit's edge geometry and label placement. An edge's path and where its label sits are one function of the node boxes
// and the edges, so the curve and the label come from the same numbers, and every canvas built on the kit gains it. It is pure, with
// no React and no DOM, and deterministic. The same nodes and edges in any order give the same routes, since edges are taken in
// order of id and no randomness and no time is used.

export interface Box {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Point {
  x: number;
  y: number;
}

/** An edge to route, between two nodes of the map given to `routeEdges` by their ids. */
export interface RouteEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
}

export interface RouteOptions {
  /** The direction the layout runs, which decides what a forward and a backward edge is. */
  direction: "LR" | "TB";
  /** The width of one character of the label, in the label's font. */
  labelCharWidth: number;
  /** The height of the label's box, border included. */
  labelHeight: number;
  /** The width the label's box adds on each side of its text, border included. */
  labelPadding: number;
}

/** From the label's CSS in styles.css, 11px type with 1px of border and a padding of 1px and 6px. */
export const DEFAULT_ROUTE_OPTIONS: RouteOptions = { direction: "LR", labelCharWidth: 6.5, labelHeight: 21, labelPadding: 7 };

/** The size of a node on the canvas before it is measured. The width is the one `.canvas-node` has in styles.css. */
export const DEFAULT_NODE_SIZE = { width: 240, height: 51 };

export type Side = "left" | "right" | "top" | "bottom";

/** A cubic Bezier from `p0` to `p3`, with `p1` and `p2` its control points. */
export interface Curve {
  p0: Point;
  p1: Point;
  p2: Point;
  p3: Point;
}

export interface EdgeRoute {
  id: string;
  /** An SVG path, `M` and one `C`, drawn from the source to the target. */
  path: string;
  sourceSide: Side;
  targetSide: Side;
  curve: Curve;
  /** The box the label covers, centred on a point of the curve. Absent where the edge has no label. */
  label?: Box;
}

/** The distance between two attachment points on one side, for edges between one pair of nodes. */
const SPREAD_STEP = 16;
/** The least and the most a control point lies from its attachment point. The most keeps a curve over a long run near its ends, so a label can sit in the gap beside a node the run crosses. */
const CONTROL_FLOOR = 24;
const CONTROL_CEILING = 120;
/** The parameters tried for a label, in order of preference. */
export const LABEL_CANDIDATES: readonly number[] = [0.5, 0.4, 0.6, 0.3, 0.7, 0.2, 0.8];

const compare = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);
const round = (n: number) => Math.round(n * 100) / 100;

const NORMAL: Record<Side, Point> = { left: { x: -1, y: 0 }, right: { x: 1, y: 0 }, top: { x: 0, y: -1 }, bottom: { x: 0, y: 1 } };

/** The point of a side at `offset` along it from its middle. */
function attach(box: Box, side: Side, offset: number): Point {
  const cx = box.x + box.width / 2;
  const cy = box.y + box.height / 2;
  switch (side) {
    case "left": return { x: box.x, y: cy + offset };
    case "right": return { x: box.x + box.width, y: cy + offset };
    case "top": return { x: cx + offset, y: box.y };
    case "bottom": return { x: cx + offset, y: box.y + box.height };
  }
}

/** The length of a side, which is how far attachment points can be spread along it. */
const sideLength = (box: Box, side: Side) => (side === "left" || side === "right" ? box.height : box.width);

/**
 * The sides an edge leaves and enters by, chosen so that its curve never has to wrap around its own node. Ranks run along x in LR
 * and along y in TB.
 * - Two nodes in different ranks, that is whose extents along the direction do not overlap. A forward edge, to the target further
 *   along the direction by centre, leaves the source's far side and enters the target's near side (right then left in LR, bottom
 *   then top in TB). A backward edge leaves the source's near side and enters the target's far side (left then right in LR, top
 *   then bottom in TB), so it runs straight back and never loops behind a node.
 * - Two nodes in one rank, whose extents along the direction overlap. The edge uses the sides that face each other across the rank
 *   (bottom then top where the target lies lower in LR, top then bottom where it lies higher, right then left or left then right in
 *   TB by the same rule).
 */
export function chooseSides(source: Box, target: Box, direction: "LR" | "TB"): [Side, Side] {
  const lr = direction === "LR";
  const [a, la, b, lb] = lr ? (["x", "width", "y", "height"] as const) : (["y", "height", "x", "width"] as const);
  const overlap = source[a] < target[a] + target[la] && target[a] < source[a] + source[la];
  if (!overlap) {
    const forward = target[a] + target[la] / 2 > source[a] + source[la] / 2;
    if (lr) return forward ? ["right", "left"] : ["left", "right"];
    return forward ? ["bottom", "top"] : ["top", "bottom"];
  }
  const after = target[b] + target[lb] / 2 >= source[b] + source[lb] / 2;
  if (lr) return after ? ["bottom", "top"] : ["top", "bottom"];
  return after ? ["right", "left"] : ["left", "right"];
}

/** The point of a curve at t, 0 at its start and 1 at its end. */
export function curvePoint(curve: Curve, t: number): Point {
  const u = 1 - t;
  const w0 = u * u * u;
  const w1 = 3 * u * u * t;
  const w2 = 3 * u * t * t;
  const w3 = t * t * t;
  return {
    x: w0 * curve.p0.x + w1 * curve.p1.x + w2 * curve.p2.x + w3 * curve.p3.x,
    y: w0 * curve.p0.y + w1 * curve.p1.y + w2 * curve.p2.y + w3 * curve.p3.y,
  };
}

/** The curve between two attachment points. A control point lies out from its point along its side's normal, by half the gap, within the floor and the ceiling. */
function curveBetween(p0: Point, side0: Side, p3: Point, side3: Side): Curve {
  const n0 = NORMAL[side0];
  const n3 = NORMAL[side3];
  const gap = Math.abs((p3.x - p0.x) * n0.x + (p3.y - p0.y) * n0.y);
  const reach = Math.min(CONTROL_CEILING, Math.max(CONTROL_FLOOR, gap / 2));
  return {
    p0,
    p1: { x: p0.x + n0.x * reach, y: p0.y + n0.y * reach },
    p2: { x: p3.x + n3.x * reach, y: p3.y + n3.y * reach },
    p3,
  };
}

const pathOf = (c: Curve) => `M ${round(c.p0.x)} ${round(c.p0.y)} C ${round(c.p1.x)} ${round(c.p1.y)}, ${round(c.p2.x)} ${round(c.p2.y)}, ${round(c.p3.x)} ${round(c.p3.y)}`;

const overlapArea = (a: Box, b: Box) => {
  const w = Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x);
  const h = Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y);
  return w > 0 && h > 0 ? w * h : 0;
};

/**
 * The route of every edge whose two nodes are in `nodes`, in order of id. Edges between one pair of nodes, in either direction,
 * attach at points spread along the side by a fixed step around its middle in order of id, so their curves do not coincide. An edge
 * from a node to itself leaves and enters by the same side as a loop, the right in LR and the bottom in TB. Labels are then placed
 * greedily in order of id. A label takes the first of `LABEL_CANDIDATES` along its curve whose box covers no node and no label placed
 * before. Where every candidate covers something it takes the one covering the least area, ties by the order of preference, so a
 * label is always placed.
 */
export function routeEdges(nodes: ReadonlyMap<string, Box>, edges: readonly RouteEdge[], options: Partial<RouteOptions> = {}): EdgeRoute[] {
  // An option given as undefined is the default, so a caller can pass what it was given without checking each.
  const o = { ...DEFAULT_ROUTE_OPTIONS, ...Object.fromEntries(Object.entries(options).filter(([, v]) => v !== undefined)) };
  const sorted = edges.filter((e) => nodes.has(e.source) && nodes.has(e.target)).sort((a, b) => compare(a.id, b.id));

  // The edges between each pair of nodes, and the loops on each node, in order of id.
  const together = new Map<string, string[]>();
  for (const e of sorted) {
    const key = e.source === e.target ? e.source : [e.source, e.target].sort(compare).join("\u0000");
    together.set(key, [...(together.get(key) ?? []), e.id]);
  }

  const routes = sorted.map((e): EdgeRoute => {
    const s = nodes.get(e.source)!;
    const t = nodes.get(e.target)!;
    const key = e.source === e.target ? e.source : [e.source, e.target].sort(compare).join("\u0000");
    const group = together.get(key)!;
    const k = group.length;
    const index = group.indexOf(e.id);
    let curve: Curve;
    let sourceSide: Side;
    let targetSide: Side;
    if (e.source === e.target) {
      sourceSide = targetSide = o.direction === "LR" ? "right" : "bottom";
      const quarter = sideLength(s, sourceSide) / 4;
      const a = attach(s, sourceSide, -quarter);
      const b = attach(s, sourceSide, quarter);
      const reach = 44 + 26 * index;
      const n = NORMAL[sourceSide];
      curve = { p0: a, p1: { x: a.x + n.x * reach, y: a.y + n.y * reach }, p2: { x: b.x + n.x * reach, y: b.y + n.y * reach }, p3: b };
    } else {
      [sourceSide, targetSide] = chooseSides(s, t, o.direction);
      const room = Math.min(sideLength(s, sourceSide), sideLength(t, targetSide)) - SPREAD_STEP;
      const step = k > 1 ? Math.min(SPREAD_STEP, Math.max(0, room) / (k - 1)) : 0;
      const offset = (index - (k - 1) / 2) * step;
      curve = curveBetween(attach(s, sourceSide, offset), sourceSide, attach(t, targetSide, offset), targetSide);
    }
    return { id: e.id, path: pathOf(curve), sourceSide, targetSide, curve };
  });

  const obstacles = [...nodes.values()];
  const placed: Box[] = [];
  const byId = new Map(sorted.map((e) => [e.id, e]));
  return routes.map((r) => {
    const text = byId.get(r.id)!.label;
    if (!text) return r;
    const width = text.length * o.labelCharWidth + 2 * o.labelPadding;
    let best: Box | undefined;
    let least = Infinity;
    for (const t of LABEL_CANDIDATES) {
      const p = curvePoint(r.curve, t);
      const box = { x: p.x - width / 2, y: p.y - o.labelHeight / 2, width, height: o.labelHeight };
      const area = obstacles.reduce((sum, n) => sum + overlapArea(box, n), 0) + placed.reduce((sum, n) => sum + overlapArea(box, n), 0);
      if (area < least) {
        least = area;
        best = box;
      }
      if (area === 0) break;
    }
    placed.push(best!);
    return { ...r, label: best };
  });
}
