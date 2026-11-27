// SPDX-License-Identifier: MPL-2.0
// The canvas kit's edge geometry and label placement. An edge's path and where its label sits are one function of the node boxes
// and the edges, so the curve and the label come from the same numbers, and every canvas built on the kit gains it. It is pure, with
// no React and no DOM, and deterministic. The same nodes and edges in any order give the same routes, since nodes and edges are
// taken in order of id and no randomness and no time is used. An edge is routed in three steps. The sides are chosen from the boxes,
// then an edge that would cross a node it does not join is given waypoints in the free channels of the ranks it crosses (SVA-O4),
// then the edges that share a side of a node are spread along it, in the order of where they go.

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
  /** An SVG path, `M` and one `C` for each segment, drawn from the source to the target. */
  path: string;
  sourceSide: Side;
  targetSide: Side;
  /** The segments of the path, one where the edge needs no waypoint and one more for each waypoint. Each starts where the one before ends. */
  curve: Curve[];
  /** The box the label covers, centred on a point of the path. Absent where the edge has no label. */
  label?: Box;
}

/** How near a route may come to a node it does not join. A route is checked at points a few pixels apart, so a drawing is held to a little less. */
export const CLEARANCE = 8;
/** The margin kept from a node where a channel between nodes is found, a pixel more than the clearance. */
const CHANNEL_MARGIN = CLEARANCE + 1;
/** How far before and after a rank's nodes a route takes its flat run, so it is level before it is beside a node. */
const RANK_PAD = 14;
/** The distance between two routes that cross one rank by one channel, and how far a detour round a rank lies from it. */
const LANE_STEP = 6;
const DETOUR = 30;
/** The margin kept from the corners of a side, where edges are spread along it. */
const SIDE_MARGIN = 8;
/** The spacing of the points a route is checked at, and the divisions of a segment for arc length. */
const SAMPLE_STEP = 4;
const ARC_STEPS = 32;
/** The least and the most a control point lies from its attachment point. The most keeps a curve over a long run near its ends, so a label can sit in the gap beside a node the run crosses. */
const CONTROL_FLOOR = 24;
const CONTROL_CEILING = 120;
/** The parameters tried for a label, in order of preference. */
export const LABEL_CANDIDATES: readonly number[] = [0.5, 0.4, 0.6, 0.3, 0.7, 0.2, 0.8];
/** The finer parameters tried, nearest the middle first, when none of those covers nothing. Where one of them covers nothing the label takes it. */
const FINE_CANDIDATES: readonly number[] = Array.from({ length: 73 }, (_, i) => 0.05 + i * 0.0125).sort((a, b) => Math.abs(a - 0.5) - Math.abs(b - 0.5) || a - b);

/** How much longer than its label an edge must be for the label to sit on it, and how far from the edge a label placed beside it is kept. */
const SHORT_MARGIN = 4;
const BESIDE_GAP = 4;
/** How far a label beside an edge is moved out at each try, and the room kept between it and a node. */
const BESIDE_STEP = 6;
const BESIDE_CLEARANCE = 2;

const compare = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);
const round = (n: number) => Math.round(n * 100) / 100;
const clamp = (n: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, n));

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

/** The point of one Bezier segment at t, 0 at its start and 1 at its end. */
function bezier(curve: Curve, t: number): Point {
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

/**
 * The point of a path at t, 0 at its start and 1 at its end. A single segment is read at its Bezier parameter, which for a curve
 * symmetric about its middle is its middle at 0.5. A path of several segments is read by arc length, so t is that fraction of its
 * length. The length is approximated by 32 chords for each segment, and the point is then found on the curve at the parameter the
 * chord's fraction gives, so it lies on the path and only its distance along it is approximate.
 */
export function curvePoint(path: Curve | readonly Curve[], t: number): Point {
  const segments: readonly Curve[] = "p0" in path ? [path] : path;
  if (segments.length === 1) return bezier(segments[0], t);
  const lengths: number[] = [];
  let total = 0;
  for (const s of segments) {
    let prev = s.p0;
    for (let k = 1; k <= ARC_STEPS; k++) {
      const p = bezier(s, k / ARC_STEPS);
      const d = Math.hypot(p.x - prev.x, p.y - prev.y);
      lengths.push(d);
      total += d;
      prev = p;
    }
  }
  let want = clamp(t, 0, 1) * total;
  for (let i = 0; i < lengths.length; i++) {
    if (want <= lengths[i] || i === lengths.length - 1) {
      const frac = lengths[i] > 0 ? Math.min(1, want / lengths[i]) : 0;
      const seg = Math.floor(i / ARC_STEPS);
      return bezier(segments[seg], ((i % ARC_STEPS) + frac) / ARC_STEPS);
    }
    want -= lengths[i];
  }
  return segments[0].p0;
}

/** A point of a route and the unit direction the route runs in there. */
interface Anchor {
  p: Point;
  d: Point;
}

/** The smooth path through anchors. A control point lies out from its anchor along the anchor's direction, by half the gap, within the floor and the ceiling, so two segments meeting at an anchor have collinear control points there. */
function through(anchors: readonly Anchor[]): Curve[] {
  const out: Curve[] = [];
  for (let i = 0; i + 1 < anchors.length; i++) {
    const a = anchors[i];
    const b = anchors[i + 1];
    const dx = b.p.x - a.p.x;
    const dy = b.p.y - a.p.y;
    const gap = Math.max(Math.abs(dx * a.d.x + dy * a.d.y), Math.abs(dx * b.d.x + dy * b.d.y));
    const reach = Math.min(CONTROL_CEILING, Math.max(CONTROL_FLOOR, gap / 2));
    out.push({ p0: a.p, p1: { x: a.p.x + a.d.x * reach, y: a.p.y + a.d.y * reach }, p2: { x: b.p.x - b.d.x * reach, y: b.p.y - b.d.y * reach }, p3: b.p });
  }
  return out;
}

const pathOf = (curves: readonly Curve[]) =>
  `M ${round(curves[0].p0.x)} ${round(curves[0].p0.y)}` + curves.map((c) => ` C ${round(c.p1.x)} ${round(c.p1.y)}, ${round(c.p2.x)} ${round(c.p2.y)}, ${round(c.p3.x)} ${round(c.p3.y)}`).join("");

const overlapArea = (a: Box, b: Box) => {
  const w = Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x);
  const h = Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y);
  return w > 0 && h > 0 ? w * h : 0;
};

/** The length of a path, approximated by 32 chords for each segment. */
function arcLength(path: readonly Curve[]): number {
  let total = 0;
  for (const s of path) {
    let prev = s.p0;
    for (let k = 1; k <= ARC_STEPS; k++) {
      const p = bezier(s, k / ARC_STEPS);
      total += Math.hypot(p.x - prev.x, p.y - prev.y);
      prev = p;
    }
  }
  return total;
}

/**
 * The box of a label of the given size beside its edge, for an edge shorter than the label along the edge's own direction, which a
 * label on it would hide. The direction is the one from the path's start to its end. The label is centred on the path's middle and
 * moved out across the path, to the right of it (below it where the path runs across) and then to the left, by half its own extent
 * across the path and a gap, and then further in steps, to the first place that covers no node and no label placed before it. It is
 * moved out no further than clears the two nodes of the edge together. Nothing is returned, and the label is placed on the path as for
 * any edge, where the edge is as long as its label, where the label is longer than the two nodes together along the path, which no
 * place beside the edge would suit, and where no place is free.
 */
function besideEdge(path: readonly Curve[], from: Box, to: Box, width: number, height: number, obstacles: readonly Box[], placed: readonly Box[]): Box | undefined {
  const a = path[0].p0;
  const b = path[path.length - 1].p3;
  const length = Math.hypot(b.x - a.x, b.y - a.y);
  if (length < 1e-6) return undefined;
  const [ux, uy] = [(b.x - a.x) / length, (b.y - a.y) / length];
  const extentOf = (w: number, h: number, nx: number, ny: number) => w * Math.abs(nx) + h * Math.abs(ny);
  if (arcLength(path) >= extentOf(width, height, ux, uy) + SHORT_MARGIN) return undefined;
  const x0 = Math.min(from.x, to.x);
  const y0 = Math.min(from.y, to.y);
  const pair = { x: x0, y: y0, width: Math.max(from.x + from.width, to.x + to.width) - x0, height: Math.max(from.y + from.height, to.y + to.height) - y0 };
  if (extentOf(width, height, ux, uy) > extentOf(pair.width, pair.height, ux, uy)) return undefined;
  let [nx, ny] = [-uy, ux];
  if (nx < -1e-9 || (Math.abs(nx) <= 1e-9 && ny < 0)) [nx, ny] = [-nx, -ny];
  const near = extentOf(width, height, nx, ny) / 2 + BESIDE_GAP;
  const far = extentOf(pair.width, pair.height, nx, ny) / 2 + near;
  const m = curvePoint(path, 0.5);
  for (let d = near; d <= far + BESIDE_STEP; d += BESIDE_STEP) {
    for (const side of [1, -1]) {
      const box = { x: m.x + side * nx * d - width / 2, y: m.y + side * ny * d - height / 2, width, height };
      const roomy = { x: box.x - BESIDE_CLEARANCE, y: box.y - BESIDE_CLEARANCE, width: width + 2 * BESIDE_CLEARANCE, height: height + 2 * BESIDE_CLEARANCE };
      if (obstacles.every((n) => overlapArea(roomy, n) === 0) && placed.every((n) => overlapArea(box, n) === 0)) return box;
    }
  }
  return undefined;
}

/** The points of a path about `SAMPLE_STEP` apart, the ends included. */
function sampled(path: readonly Curve[]): Point[] {
  const out: Point[] = [path[0].p0];
  for (const c of path) {
    const hull = Math.hypot(c.p1.x - c.p0.x, c.p1.y - c.p0.y) + Math.hypot(c.p2.x - c.p1.x, c.p2.y - c.p1.y) + Math.hypot(c.p3.x - c.p2.x, c.p3.y - c.p2.y);
    const n = clamp(Math.ceil(hull / SAMPLE_STEP), 8, 400);
    for (let k = 1; k <= n; k++) out.push(bezier(c, k / n));
  }
  return out;
}

/** How many of a path's sample points lie within the clearance of a box, summed over the boxes. Zero means the path is clear of them. */
function intrusion(path: readonly Curve[], boxes: readonly Box[]): number {
  const pts = sampled(path);
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const p of pts) {
    x0 = Math.min(x0, p.x); x1 = Math.max(x1, p.x); y0 = Math.min(y0, p.y); y1 = Math.max(y1, p.y);
  }
  let count = 0;
  for (const b of boxes) {
    const l = b.x - CLEARANCE, r = b.x + b.width + CLEARANCE, t = b.y - CLEARANCE, d = b.y + b.height + CLEARANCE;
    if (r <= x0 || l >= x1 || d <= y0 || t >= y1) continue;
    for (const p of pts) if (p.x > l && p.x < r && p.y > t && p.y < d) count++;
  }
  return count;
}

// The layout's two axes. `a` runs along the ranks (x in LR) and `b` across them.
interface Extent { a0: number; a1: number; b0: number; b1: number }
const extent = (b: Box, lr: boolean): Extent => (lr ? { a0: b.x, a1: b.x + b.width, b0: b.y, b1: b.y + b.height } : { a0: b.y, a1: b.y + b.height, b0: b.x, b1: b.x + b.width });
const pointAt = (lr: boolean, a: number, b: number): Point => (lr ? { x: a, y: b } : { x: b, y: a });
const coordA = (lr: boolean, p: Point) => (lr ? p.x : p.y);
const coordB = (lr: boolean, p: Point) => (lr ? p.y : p.x);

/** A rank as the boxes show it, the nodes whose extents along the direction overlap one another, chained. */
interface Rank { a0: number; a1: number; members: Extent[] }

function ranksOf(list: readonly { id: string; box: Box }[], lr: boolean): { ranks: Rank[]; index: Map<string, number> } {
  const items = list.map((n) => ({ id: n.id, e: extent(n.box, lr) })).sort((p, q) => p.e.a0 - q.e.a0 || compare(p.id, q.id));
  const ranks: Rank[] = [];
  const index = new Map<string, number>();
  for (const n of items) {
    const last = ranks[ranks.length - 1];
    if (last && n.e.a0 < last.a1) {
      last.a1 = Math.max(last.a1, n.e.a1);
      last.members.push(n.e);
    } else ranks.push({ a0: n.e.a0, a1: n.e.a1, members: [n.e] });
    index.set(n.id, ranks.length - 1);
  }
  return { ranks, index };
}

/** The stretches across a rank where a route can run clear of every node of it, from the first node's far side to the last, a stretch beyond each end being unbounded. */
function channelsOf(rank: Rank): [number, number][] {
  const merged: [number, number][] = [];
  for (const [lo, hi] of rank.members.map((m): [number, number] => [m.b0 - CHANNEL_MARGIN, m.b1 + CHANNEL_MARGIN]).sort((p, q) => p[0] - q[0] || p[1] - q[1])) {
    const last = merged[merged.length - 1];
    if (last && lo <= last[1]) last[1] = Math.max(last[1], hi);
    else merged.push([lo, hi]);
  }
  const out: [number, number][] = [[-Infinity, merged[0][0]]];
  for (let i = 0; i + 1 < merged.length; i++) out.push([merged[i][1], merged[i + 1][0]]);
  out.push([merged[merged.length - 1][1], Infinity]);
  return out;
}

/** Where an edge crosses one rank, in the channel [lo, hi] at `base`, and later `lane`, the coordinate across the rank it takes with the other edges of the channel. */
interface Crossing { rank: number; lo: number; hi: number; base: number; lane: number; forward: boolean }

/** The crossing of every rank strictly between two ranks, in the order the edge travels. A rank is crossed in the channel nearest to the straight line between the points, ties by the lower coordinate. */
function crossings(ranks: readonly Rank[], from: number, to: number, p0: Point, p3: Point, lr: boolean): Crossing[] {
  const step = to > from ? 1 : -1;
  const out: Crossing[] = [];
  const [a0, b0, a3, b3] = [coordA(lr, p0), coordB(lr, p0), coordA(lr, p3), coordB(lr, p3)];
  for (let r = from + step; r !== to; r += step) {
    const mid = (ranks[r].a0 + ranks[r].a1) / 2;
    const line = a3 === a0 ? b0 : b0 + ((b3 - b0) * (mid - a0)) / (a3 - a0);
    let best: Crossing | undefined;
    let least = Infinity;
    for (const [lo, hi] of channelsOf(ranks[r])) {
      const base = clamp(line, lo, hi);
      const d = Math.abs(base - line);
      if (d < least - 1e-9) {
        least = d;
        best = { rank: r, lo, hi, base, lane: base, forward: step > 0 };
      }
    }
    out.push(best!);
  }
  return out;
}

/** Gives each crossing of one channel its own lane, in order of edge id, a few pixels apart and centred on where the edges would cross, kept inside the channel. */
function assignLanes(byEdge: ReadonlyMap<string, Crossing[]>): void {
  const groups = new Map<string, Crossing[]>();
  for (const id of [...byEdge.keys()].sort(compare)) {
    for (const c of byEdge.get(id)!) {
      const key = `${c.rank}|${c.lo}|${c.hi}`;
      groups.set(key, [...(groups.get(key) ?? []), c]);
    }
  }
  for (const list of groups.values()) {
    const n = list.length;
    const { lo, hi } = list[0];
    const step = n > 1 ? Math.min(LANE_STEP, (hi - lo) / (n - 1)) : 0;
    const span = (n - 1) * step;
    const mean = list.reduce((sum, c) => sum + c.base, 0) / n;
    const centre = clamp(mean, lo + span / 2, hi - span / 2);
    list.forEach((c, i) => (c.lane = centre + (i - (n - 1) / 2) * step));
  }
}

/** The anchors a crossing adds, a level run along the rank at its lane, entered just before the rank's nodes and left just after. */
function waypoints(c: Crossing, rank: Rank, lr: boolean): Anchor[] {
  const d = pointAt(lr, c.forward ? 1 : -1, 0);
  const before = c.forward ? rank.a0 - RANK_PAD : rank.a1 + RANK_PAD;
  const after = c.forward ? rank.a1 + RANK_PAD : rank.a0 - RANK_PAD;
  return [{ p: pointAt(lr, before, c.lane), d }, { p: pointAt(lr, after, c.lane), d }];
}

/** The space between the far point of a loop and its label. */
const LOOP_LABEL_GAP = 6;
/** How many places a loop's label is tried along its side, on each side of the first. */
const LOOP_LABEL_STEPS = 6;

interface End { id: string; end: "s" | "t"; key: number }

/**
 * The route of every edge whose two nodes are in `nodes`, in order of id.
 * - Sides are chosen by `chooseSides`.
 * - An edge whose curve between the middles of its sides would come within `CLEARANCE` of a node other than its ends is given
 *   waypoints. The ranks are read from the boxes, as the nodes whose extents along the direction overlap. The edge crosses each rank
 *   between its ends in the free channel nearest to the straight line between them, ties by the lower coordinate, along a level
 *   run, and edges that use one channel take lanes of their own, a few pixels apart in order of id. The path passes through the
 *   waypoints with the same tangent either side, so it has no kink. An edge between two nodes of one rank that would cross a node
 *   of it goes round the rank on the side with the less intrusion instead. Where no route clears every node, the route with the
 *   least intrusion is kept, so a route is always returned.
 * - Edges that leave or enter one side of a node share it, spread evenly between margins from its corners, in order of the position
 *   of their other end along the side's axis (the first waypoint where there is one, else the other node's centre), ties by id.
 * - An edge from a node to itself leaves and enters by the same side as a loop, the right in LR and the bottom in TB.
 * Labels are then placed greedily in order of id. The label of a loop goes just beyond the loop's far point where that place is free. Otherwise a label takes the first of `LABEL_CANDIDATES` along its path whose box covers no
 * node and no label placed before. Where every candidate covers something it looks for a free place among finer fractions, nearest
 * the middle first, and where there is none it takes the candidate covering the least area, ties by the order of preference, so a
 * label is always placed. An edge shorter than its label along its own direction would be hidden by a label on it, so its label is put
 * beside it instead, where a place beside it is free (`besideEdge`).
 */
export function routeEdges(nodes: ReadonlyMap<string, Box>, edges: readonly RouteEdge[], options: Partial<RouteOptions> = {}): EdgeRoute[] {
  // An option given as undefined is the default, so a caller can pass what it was given without checking each.
  const o = { ...DEFAULT_ROUTE_OPTIONS, ...Object.fromEntries(Object.entries(options).filter(([, v]) => v !== undefined)) };
  const lr = o.direction === "LR";
  const sorted = edges.filter((e) => nodes.has(e.source) && nodes.has(e.target)).sort((a, b) => compare(a.id, b.id));
  const list = [...nodes].map(([id, box]) => ({ id, box })).sort((a, b) => compare(a.id, b.id));
  const { ranks, index } = ranksOf(list, lr);
  const blockers = (a: string, b: string) => list.filter((n) => n.id !== a && n.id !== b).map((n) => n.box);

  // The loops on each node, in order of id.
  const loops = new Map<string, string[]>();
  for (const e of sorted) if (e.source === e.target) loops.set(e.source, [...(loops.get(e.source) ?? []), e.id]);

  // Step one. The sides, the curve between the middles of the sides, and the crossings of an edge that curve would run through nodes with.
  interface Plan { e: RouteEdge; s: Box; t: Box; sides: [Side, Side]; cross?: Crossing[] }
  const plans = new Map<string, Plan>();
  const crossed = new Map<string, Crossing[]>();
  for (const e of sorted) {
    if (e.source === e.target) continue;
    const s = nodes.get(e.source)!;
    const t = nodes.get(e.target)!;
    const sides = chooseSides(s, t, o.direction);
    const plan: Plan = { e, s, t, sides };
    plans.set(e.id, plan);
    const p0 = attach(s, sides[0], 0);
    const p3 = attach(t, sides[1], 0);
    const from = index.get(e.source)!;
    const to = index.get(e.target)!;
    const direct = through([{ p: p0, d: NORMAL[sides[0]] }, { p: p3, d: { x: -NORMAL[sides[1]].x, y: -NORMAL[sides[1]].y } }]);
    if (from !== to && intrusion(direct, blockers(e.source, e.target)) > 0) {
      plan.cross = crossings(ranks, from, to, p0, p3, lr);
      crossed.set(e.id, plan.cross);
    }
  }
  assignLanes(crossed);

  // Step two. The attachment points, spread along each side that more than one edge uses.
  const sharing = new Map<string, End[]>();
  const sideOf = new Map<string, Side>();
  for (const plan of plans.values()) {
    const { e, s, t, sides, cross } = plan;
    const axisX = (side: Side) => side === "top" || side === "bottom";
    const first = cross?.length ? waypoints(cross[0], ranks[cross[0].rank], lr)[0].p : undefined;
    const last = cross?.length ? waypoints(cross[cross.length - 1], ranks[cross[cross.length - 1].rank], lr)[1].p : undefined;
    const centre = (b: Box, side: Side) => (axisX(side) ? b.x + b.width / 2 : b.y + b.height / 2);
    const entries: [string, Side, End][] = [
      [e.source, sides[0], { id: e.id, end: "s", key: first ? (axisX(sides[0]) ? first.x : first.y) : centre(t, sides[0]) }],
      [e.target, sides[1], { id: e.id, end: "t", key: last ? (axisX(sides[1]) ? last.x : last.y) : centre(s, sides[1]) }],
    ];
    for (const [node, side, end] of entries) {
      const key = `${node}\u0000${side}`;
      sharing.set(key, [...(sharing.get(key) ?? []), end]);
      sideOf.set(key, side);
    }
  }
  const offsets = new Map<string, number>();
  for (const [key, ends] of sharing) {
    const node = nodes.get(key.split("\u0000")[0])!;
    const side = sideOf.get(key)!;
    ends.sort((a, b) => a.key - b.key || compare(a.id, b.id) || compare(a.end, b.end));
    const k = ends.length;
    const step = Math.max(0, sideLength(node, side) - 2 * SIDE_MARGIN) / k;
    ends.forEach((end, i) => offsets.set(`${end.id}|${end.end}`, (i - (k - 1) / 2) * step));
  }

  // Step three. The path of each edge, through its waypoints if it has any, checked against the nodes once more.
  const routes = sorted.map((e): EdgeRoute => {
    const s = nodes.get(e.source)!;
    const t = nodes.get(e.target)!;
    if (e.source === e.target) {
      const sourceSide: Side = o.direction === "LR" ? "right" : "bottom";
      const quarter = sideLength(s, sourceSide) / 4;
      const a = attach(s, sourceSide, -quarter);
      const b = attach(s, sourceSide, quarter);
      const reach = 44 + 26 * loops.get(e.source)!.indexOf(e.id);
      const n = NORMAL[sourceSide];
      const curve: Curve[] = [{ p0: a, p1: { x: a.x + n.x * reach, y: a.y + n.y * reach }, p2: { x: b.x + n.x * reach, y: b.y + n.y * reach }, p3: b }];
      return { id: e.id, path: pathOf(curve), sourceSide, targetSide: sourceSide, curve };
    }
    const plan = plans.get(e.id)!;
    const [sourceSide, targetSide] = plan.sides;
    const p0 = attach(s, sourceSide, offsets.get(`${e.id}|s`) ?? 0);
    const p3 = attach(t, targetSide, offsets.get(`${e.id}|t`) ?? 0);
    const start: Anchor = { p: p0, d: NORMAL[sourceSide] };
    const stop: Anchor = { p: p3, d: { x: -NORMAL[targetSide].x, y: -NORMAL[targetSide].y } };
    const others = blockers(e.source, e.target);
    const from = index.get(e.source)!;
    const to = index.get(e.target)!;
    let curve = through([start, stop]);
    let hit = intrusion(curve, others);
    if (hit > 0 && from !== to) {
      const cross = plan.cross ?? crossings(ranks, from, to, p0, p3, lr);
      const routed = through([start, ...cross.flatMap((c) => waypoints(c, ranks[c.rank], lr)), stop]);
      const routedHit = cross.length ? intrusion(routed, others) : Infinity;
      if (routedHit <= hit) [curve, hit] = [routed, routedHit];
    } else if (hit > 0) {
      // Two nodes of one rank with a node between them across it. The edge goes round the rank on either side.
      const rank = ranks[from];
      const along = coordB(lr, p3) >= coordB(lr, p0) ? 1 : -1;
      const d = pointAt(lr, 0, along);
      const mid = (coordB(lr, p0) + coordB(lr, p3)) / 2;
      for (const a of [rank.a0 - DETOUR, rank.a1 + DETOUR]) {
        const around = through([start, { p: pointAt(lr, a, mid), d }, stop]);
        const aroundHit = intrusion(around, others);
        if (aroundHit < hit) [curve, hit] = [around, aroundHit];
      }
    }
    return { id: e.id, path: pathOf(curve), sourceSide, targetSide, curve };
  });

  const obstacles = list.map((n) => n.box);
  const placed: Box[] = [];
  const byId = new Map(sorted.map((e) => [e.id, e]));
  return routes.map((r) => {
    const text = byId.get(r.id)!.label;
    if (!text) return r;
    const width = text.length * o.labelCharWidth + 2 * o.labelPadding;
    const edge = byId.get(r.id)!;
    // A loop's label is just beyond its far point on the side the loop leaves by, since a label on the loop itself would cover the node the loop leaves.
    // Where another label is there already it is moved along that side, to either side of the first place in turn, until it is clear.
    if (edge.source === edge.target) {
      const farPoint = curvePoint(r.curve, 0.5);
      const n = NORMAL[r.sourceSide];
      const across = n.x !== 0 ? o.labelHeight : width;
      for (let step = 0; step <= LOOP_LABEL_STEPS * 2; step++) {
        const shift = (step % 2 === 0 ? 1 : -1) * Math.ceil(step / 2) * (across + LOOP_LABEL_GAP);
        const box: Box = n.x !== 0
          ? { x: n.x > 0 ? farPoint.x + LOOP_LABEL_GAP : farPoint.x - LOOP_LABEL_GAP - width, y: farPoint.y - o.labelHeight / 2 + shift, width, height: o.labelHeight }
          : { x: farPoint.x - width / 2 + shift, y: n.y > 0 ? farPoint.y + LOOP_LABEL_GAP : farPoint.y - LOOP_LABEL_GAP - o.labelHeight, width, height: o.labelHeight };
        if (obstacles.every((node) => overlapArea(box, node) === 0) && placed.every((other) => overlapArea(box, other) === 0)) {
          placed.push(box);
          return { ...r, label: box };
        }
      }
    }
    const beside = edge.source === edge.target ? undefined : besideEdge(r.curve, nodes.get(edge.source)!, nodes.get(edge.target)!, width, o.labelHeight, obstacles, placed);
    if (beside) {
      placed.push(beside);
      return { ...r, label: beside };
    }
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
    if (least > 0) {
      for (const t of FINE_CANDIDATES) {
        const p = curvePoint(r.curve, t);
        const box = { x: p.x - width / 2, y: p.y - o.labelHeight / 2, width, height: o.labelHeight };
        if (obstacles.every((n) => overlapArea(box, n) === 0) && placed.every((n) => overlapArea(box, n) === 0)) {
          best = box;
          break;
        }
      }
    }
    placed.push(best!);
    return { ...r, label: best };
  });
}
