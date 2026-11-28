// SPDX-License-Identifier: MPL-2.0
// The canvas kit's layout. A layout is one function from nodes and edges to a position for each node, so another layout, such as
// elkjs or dagre (BL-23), is one more entry in `layouts` and nothing else in a canvas changes. It is pure, with no React and no
// DOM, and deterministic. The same nodes and edges in any order give the same positions, since it sorts by id before it reads
// anything and uses no randomness and no time.

import { DEFAULT_NODE_SIZE, DEFAULT_ROUTE_OPTIONS, labelWidth, loopRoom } from "./edges";

export interface LayoutNode {
  id: string;
  /** The size on the canvas, when the node's is known. A node with none takes no room beyond the gaps. */
  width?: number;
  height?: number;
  /** Nodes with one group are kept next to each other within a rank, where the ordering allows it. */
  group?: string;
  /** A rank the node must take, kept as given. Ranks count from 0 and may be negative, and the first rank sits at x = 0. */
  rank?: number;
  /** The place within the rank, kept as given. A rank where every node has one uses them as slots, so gaps are kept. */
  order?: number;
}

export interface LayoutEdge {
  source: string;
  target: string;
  /** The text of the edge's label, which a loop's room is sized from. Nothing else reads it. */
  label?: string;
}

export interface LayoutOptions {
  /** Ranks run left to right in LR and top to bottom in TB. */
  direction: "LR" | "TB";
  /** The pitch from one rank to the next, plus the extent of each rank with sizes. It is a column in LR and a row in TB. */
  columnGap: number;
  /** The pitch from one node to the next within a rank, plus the extent of each node with sizes. */
  rowGap: number;
}

export type Layout = (nodes: readonly LayoutNode[], edges: readonly LayoutEdge[], options: LayoutOptions) => Map<string, { x: number; y: number }>;

/** The sweeps of the barycentre heuristic. Each is one pass down the ranks and one up. */
const SWEEPS = 4;

const compare = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);
const given = (n: number | undefined): n is number => n !== undefined && Number.isFinite(n);

/**
 * Our own layered layout. Cycles are broken by a depth first search from the sources, and the edges it finds going back are
 * ignored in ranking. A node takes the longest path from a source as its rank unless it carries one. Within a rank the nodes keep
 * an explicit order, or else are ordered by sweeps of the barycentre heuristic, a group first and ties by id. A node with no
 * edge and no rank of its own is not ranked. It goes in a compact block beside the drawing, on the side that does not extend the
 * layout direction (SVA-O4), in rows that wrap at the drawing's width in LR and in columns that wrap at its height in TB, sorted
 * by id. A graph of only such nodes is a plain grid. An edge to a node that is not given is ignored, and a repeated id throws.
 *
 * An edge from a node to itself, a loop, does not rank or order anything. It leaves room, though. The loops of a node leave it by the side
 * across the flow with fewer edge ends, the top, or the left in TB, on a tie (`loopSide` of edges.ts), and the layout reads the ends from the
 * edges between nodes of one rank, the only ones that end on those sides. A node's loops and their labels reach out from that side by
 * `loopRoom`, and the gap to the node beside it on that side grows to hold them, so the loops and their labels never meet a neighbour
 * whatever the row gap is. A node whose size is not given is taken as `DEFAULT_NODE_SIZE` for that, and nothing changes in a graph with no loop.
 */
export const layered: Layout = (nodes, edges, options) => {
  const byId = new Map<string, LayoutNode>();
  for (const n of nodes) {
    if (byId.has(n.id)) throw new Error(`layered: the node id ${JSON.stringify(n.id)} is given more than once`);
    byId.set(n.id, n);
  }
  const ids = [...byId.keys()].sort(compare);
  const count = ids.length;
  const index = new Map(ids.map((id, i) => [id, i]));
  const node = ids.map((id) => byId.get(id)!);

  // The edges as sorted pairs of indices, without repeats, self edges and edges to a node not given.
  const seen = new Set<number>();
  const pairs: [number, number][] = [];
  for (const e of edges) {
    const s = index.get(e.source);
    const t = index.get(e.target);
    if (s === undefined || t === undefined || s === t || seen.has(s * count + t)) continue;
    seen.add(s * count + t);
    pairs.push([s, t]);
  }
  pairs.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  // The loops of each node, and the widest label across the side they leave by.
  const lr = options.direction === "LR";
  const loops = new Array<number>(count).fill(0);
  const loopLabel = new Array<number>(count).fill(0);
  for (const e of edges) {
    const s = index.get(e.source);
    if (s === undefined || e.source !== e.target) continue;
    loops[s]++;
    if (e.label) loopLabel[s] = Math.max(loopLabel[s], lr ? DEFAULT_ROUTE_OPTIONS.labelHeight : labelWidth(e.label));
  }
  const out: number[][] = node.map(() => []);
  const into: number[][] = node.map(() => []);
  for (const [s, t] of pairs) {
    out[s].push(t);
    into[t].push(s);
  }

  // Break cycles. An edge to a node still on the stack goes back and is left out of ranking.
  const back = new Set<number>();
  const colour = new Uint8Array(count);
  const roots = [...ids.keys()].filter((i) => into[i].length === 0).concat([...ids.keys()]);
  for (const root of roots) {
    if (colour[root]) continue;
    const stack: number[] = [root];
    const next: number[] = [0];
    colour[root] = 1;
    while (stack.length) {
      const v = stack[stack.length - 1];
      const k = next[next.length - 1]++;
      if (k >= out[v].length) {
        colour[v] = 2;
        stack.pop();
        next.pop();
        continue;
      }
      const w = out[v][k];
      if (colour[w] === 1) back.add(v * count + w);
      else if (colour[w] === 0) {
        colour[w] = 1;
        stack.push(w);
        next.push(0);
      }
    }
  }
  const down: number[][] = out.map((list, v) => list.filter((w) => !back.has(v * count + w)));
  const up: number[][] = node.map(() => []);
  down.forEach((list, v) => list.forEach((w) => up[w].push(v)));

  // Rank each node by the longest path to it, in an order where every predecessor comes first.
  const rank = new Array<number>(count).fill(0);
  const waiting = up.map((list) => list.length);
  const queue = [...ids.keys()].filter((i) => waiting[i] === 0);
  for (let head = 0; head < queue.length; head++) {
    const v = queue[head];
    const own = node[v].rank;
    rank[v] = given(own) ? own : up[v].length ? Math.max(...up[v].map((p) => rank[p])) + 1 : 0;
    for (const w of down[v]) if (--waiting[w] === 0) queue.push(w);
  }

  // A node with no edge and no rank of its own is left out of the ranks and placed beside the drawing afterwards.
  const isAlone = new Set([...ids.keys()].filter((i) => out[i].length === 0 && into[i].length === 0 && !given(node[i].rank)));
  const alone = [...isAlone];

  const ranks = new Map<number, number[]>();
  for (let i = 0; i < count; i++) if (!isAlone.has(i)) ranks.set(rank[i], [...(ranks.get(rank[i]) ?? []), i]);
  const used = [...ranks.keys()].sort((a, b) => a - b);
  const groupOf = (i: number) => node[i].group ?? "";

  // A rank where any node has an order keeps the explicit orders and is not swept.
  const pinned = new Set<number>();
  const position = new Array<number>(count).fill(0);
  for (const r of used) {
    const list = ranks.get(r)!;
    if (list.some((i) => given(node[i].order))) {
      pinned.add(r);
      list.sort((a, b) => (given(node[a].order) ? node[a].order! : Infinity) - (given(node[b].order) ? node[b].order! : Infinity) || compare(groupOf(a), groupOf(b)) || a - b);
    } else list.sort((a, b) => compare(groupOf(a), groupOf(b)) || a - b);
    list.forEach((i, k) => (position[i] = k));
  }

  const sweep = (r: number, toward: number[][]) => {
    const list = ranks.get(r)!;
    const bary = new Map<number, number>();
    for (const i of list) {
      const near = toward[i];
      bary.set(i, near.length ? near.reduce((sum, p) => sum + position[p], 0) / near.length : position[i]);
    }
    list.sort((a, b) => compare(groupOf(a), groupOf(b)) || bary.get(a)! - bary.get(b)! || a - b);
    list.forEach((i, k) => (position[i] = k));
  };
  for (let s = 0; s < SWEEPS; s++) {
    for (const r of used) if (!pinned.has(r)) sweep(r, up);
    for (const r of [...used].reverse()) if (!pinned.has(r)) sweep(r, down);
  }

  // The room each node's loops need on the side they take. The ends on the two sides across the flow are those of the edges between nodes
  // of one rank, a neighbour before the node, by its place in the rank, ending on its low side and one after it on its high side.
  const low = new Array<number>(count).fill(0);
  const high = new Array<number>(count).fill(0);
  for (const e of edges) {
    // Each edge counts, as the router counts the ends of an edge drawn twice or in each direction.
    const s = index.get(e.source);
    const t = index.get(e.target);
    if (s === undefined || t === undefined || s === t || isAlone.has(s) || isAlone.has(t) || rank[s] !== rank[t]) continue;
    const [first, second] = position[s] < position[t] ? [s, t] : [t, s];
    high[first]++;
    low[second]++;
  }
  const lead = new Array<number>(count).fill(0);
  const trail = new Array<number>(count).fill(0);
  for (let i = 0; i < count; i++) {
    if (!loops[i]) continue;
    const room = loopRoom(loops[i], loopLabel[i]);
    if (high[i] < low[i]) trail[i] = room;
    else lead[i] = room;
  }

  // Coordinates. Along the ranks a rank's pitch is the columnGap, plus the widest node of each rank before it where sizes are
  // given, counted from rank 0. Across a rank a node's is its slot times the rowGap, plus the sizes of the nodes before it.
  const along = (i: number) => (lr ? node[i].width : node[i].height) ?? 0;
  const across = (i: number) => (lr ? node[i].height : node[i].width) ?? 0;
  const start = new Map<number, number>();
  let sum = 0;
  for (const r of used.filter((r) => r >= 0)) {
    start.set(r, r * options.columnGap + sum);
    sum += Math.max(0, ...ranks.get(r)!.map(along));
  }
  sum = 0;
  for (const r of used.filter((r) => r < 0).reverse()) {
    sum += Math.max(0, ...ranks.get(r)!.map(along));
    start.set(r, r * options.columnGap - sum);
  }

  // A node's extent across the rank where the loops are measured, as given and else as expected.
  const reach = (i: number) => across(i) || (lr ? DEFAULT_NODE_SIZE.height : DEFAULT_NODE_SIZE.width);
  const place = new Array<{ x: number; y: number }>(count);
  for (const r of used) {
    const list = ranks.get(r)!;
    const slotted = pinned.has(r) && list.every((i) => given(node[i].order));
    let slot = -Infinity;
    let before = 0;
    // Where loops stand between two nodes, the second is moved on until the room they need is between them, and each node after it with it.
    let shift = 0;
    let last: { at: number; node: number } | undefined;
    list.forEach((i, k) => {
      slot = slotted ? Math.max(node[i].order!, slot + 1) : k;
      const a = start.get(r)!;
      let c = slot * options.rowGap + before + shift;
      if (last && trail[last.node] + lead[i] > 0) {
        const wanted = last.at + reach(last.node) + trail[last.node] + lead[i];
        if (c < wanted) {
          shift += wanted - c;
          c = wanted;
        }
      }
      last = { at: c, node: i };
      before += across(i);
      place[i] = lr ? { x: a, y: c } : { x: c, y: a };
    });
  }

  // The nodes with no link. Their rows run along the ranks and wrap at the drawing's extent along them, and the block starts a gap
  // across from the drawing's far edge, so it extends the drawing on the side the layout does not run. A pitch along the rows is
  // the columnGap plus the widest node, as between ranks, and across them the rowGap plus the tallest. A node of unknown size
  // counts as nothing, as it does among the ranks.
  if (alone.length) {
    const drawn = [...ids.keys()].filter((i) => !isAlone.has(i));
    const aOf = (i: number) => (lr ? place[i].x : place[i].y);
    const bOf = (i: number) => (lr ? place[i].y : place[i].x);
    const wide = Math.max(...alone.map(along));
    const deep = Math.max(...alone.map(across));
    const pitchA = options.columnGap + wide;
    // A node alone with a loop keeps the room the loop needs on its side of the pitch.
    const pitchB = options.rowGap + deep + Math.max(0, ...alone.map((i) => lead[i])) + Math.max(0, ...alone.map((i) => trail[i]));
    const a0 = drawn.length ? Math.min(...drawn.map(aOf)) : 0;
    const extentA = drawn.length ? Math.max(...drawn.map((i) => aOf(i) + along(i))) - a0 : 0;
    const b0 = (drawn.length ? Math.max(...drawn.map((i) => bOf(i) + across(i) + trail[i])) + options.rowGap : 0) + Math.max(0, ...alone.map((i) => lead[i]));
    const perRow = drawn.length ? Math.max(1, Math.floor((extentA - wide) / pitchA) + 1) : Math.ceil(Math.sqrt(alone.length));
    alone.forEach((i, k) => {
      const a = a0 + (k % perRow) * pitchA;
      const b = b0 + Math.floor(k / perRow) * pitchB;
      place[i] = lr ? { x: a, y: b } : { x: b, y: a };
    });
  }
  return new Map(ids.map((id, i) => [id, place[i]]));
};

/** The layouts a canvas can be given by name. A later slice registers another here. */
export const layouts: Record<string, Layout> = { layered };
