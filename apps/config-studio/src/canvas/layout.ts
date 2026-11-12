// SPDX-License-Identifier: MPL-2.0
// The canvas kit's layout. A layout is one function from nodes and edges to a position for each node, so another layout, such as
// elkjs or dagre (BL-23), is one more entry in `layouts` and nothing else in a canvas changes. It is pure, with no React and no
// DOM, and deterministic. The same nodes and edges in any order give the same positions, since it sorts by id before it reads
// anything and uses no randomness and no time.

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
 * edge and no rank of its own goes in a final rank, sorted by id. An edge to a node that is not given and an edge from a node to
 * itself are ignored, and a repeated id throws.
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

  // A node with no edge and no rank of its own goes in a rank after the rest.
  const alone = [...ids.keys()].filter((i) => out[i].length === 0 && into[i].length === 0 && !given(node[i].rank));
  const isAlone = new Set(alone);
  let last = -Infinity;
  for (let i = 0; i < count; i++) if (!isAlone.has(i)) last = Math.max(last, rank[i]);
  const aloneRank = last === -Infinity ? 0 : last + 1;
  for (const i of alone) rank[i] = aloneRank;

  const ranks = new Map<number, number[]>();
  for (let i = 0; i < count; i++) ranks.set(rank[i], [...(ranks.get(rank[i]) ?? []), i]);
  const used = [...ranks.keys()].sort((a, b) => a - b);
  const groupOf = (i: number) => node[i].group ?? "";

  // A rank where any node has an order keeps the explicit orders and is not swept. The nodes alone are ordered by id.
  const pinned = new Set<number>();
  const position = new Array<number>(count).fill(0);
  for (const r of used) {
    const list = ranks.get(r)!;
    if (r === aloneRank && alone.length && list.every((i) => isAlone.has(i))) {
      pinned.add(r);
      list.sort((a, b) => a - b);
    } else if (list.some((i) => given(node[i].order))) {
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

  // Coordinates. Along the ranks a rank's pitch is the columnGap, plus the widest node of each rank before it where sizes are
  // given, counted from rank 0. Across a rank a node's is its slot times the rowGap, plus the sizes of the nodes before it.
  const lr = options.direction === "LR";
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

  const place = new Array<{ x: number; y: number }>(count);
  for (const r of used) {
    const list = ranks.get(r)!;
    const slotted = pinned.has(r) && list.every((i) => given(node[i].order));
    let slot = -Infinity;
    let before = 0;
    list.forEach((i, k) => {
      slot = slotted ? Math.max(node[i].order!, slot + 1) : k;
      const a = start.get(r)!;
      const c = slot * options.rowGap + before;
      before += across(i);
      place[i] = lr ? { x: a, y: c } : { x: c, y: a };
    });
  }
  return new Map(ids.map((id, i) => [id, place[i]]));
};

/** The layouts a canvas can be given by name. A later slice registers another here. */
export const layouts: Record<string, Layout> = { layered };
