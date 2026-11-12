// SPDX-License-Identifier: MPL-2.0
// The layered layout is a pure function of its nodes and edges. Its timing test prints figures and never fails on time.

import { describe, expect, it } from "vitest";
import { layered, layouts, type LayoutEdge, type LayoutNode, type LayoutOptions } from "./layout";

const LR: LayoutOptions = { direction: "LR", columnGap: 280, rowGap: 64 };
const TB: LayoutOptions = { direction: "TB", columnGap: 100, rowGap: 50 };
const nodes = (...ids: string[]): LayoutNode[] => ids.map((id) => ({ id }));
const edge = (source: string, target: string): LayoutEdge => ({ source, target });
const entries = (m: Map<string, { x: number; y: number }>) => [...m.entries()].sort((a, b) => (a[0] < b[0] ? -1 : 1));

/** A small deterministic generator, so a generated graph is the same on every run and machine. */
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

/** A layered graph of about 1.5 edges a node, each from a layer to a later one, and a few edges back. */
export function generated(size: number, seed = 7): { nodes: LayoutNode[]; edges: LayoutEdge[] } {
  const random = seeded(seed + size);
  const layers = Math.max(3, Math.round(Math.sqrt(size) / 1.5));
  const ns = Array.from({ length: size }, (_, i) => ({ id: `n${String(i).padStart(5, "0")}`, layer: Math.floor((i * layers) / size) }));
  const edges: LayoutEdge[] = [];
  const pick = (from: number, to: number) => from + Math.floor(random() * (to - from));
  for (let i = 0; i < size; i++) {
    if (ns[i].layer === layers - 1) continue;
    const first = ns.findIndex((n) => n.layer === ns[i].layer + 1);
    const end = ns.findIndex((n) => n.layer === ns[i].layer + 2);
    const stop = end === -1 ? size : end;
    for (let k = 0; k < 1 + Math.round(random()); k++) edges.push(edge(ns[i].id, ns[pick(first, stop)].id));
    if (random() < 0.1) edges.push(edge(ns[i].id, ns[pick(first, stop)].id));
  }
  for (let k = 0; k < Math.ceil(size / 50); k++) {
    const to = pick(0, size);
    const from = pick(to, size);
    if (from !== to) edges.push(edge(ns[from].id, ns[to].id));
  }
  return { nodes: ns.map((n) => ({ id: n.id })), edges };
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

describe("the layered layout", () => {
  it("is the one registered layout", () => {
    expect(Object.keys(layouts)).toEqual(["layered"]);
    expect(layouts.layered).toBe(layered);
  });

  it("ranks a chain left to right, one column for each", () => {
    const p = layered(nodes("a", "b", "c"), [edge("a", "b"), edge("b", "c")], LR);
    expect([p.get("a"), p.get("b"), p.get("c")]).toEqual([{ x: 0, y: 0 }, { x: 280, y: 0 }, { x: 560, y: 0 }]);
  });

  it("ranks a diamond by its longest path and puts the two middle nodes in one column", () => {
    const p = layered(nodes("a", "b", "c", "d"), [edge("a", "b"), edge("a", "c"), edge("b", "d"), edge("c", "d")], LR);
    expect(p.get("a")).toEqual({ x: 0, y: 0 });
    expect(p.get("b")).toEqual({ x: 280, y: 0 });
    expect(p.get("c")).toEqual({ x: 280, y: 64 });
    expect(p.get("d")!.x).toBe(560);
  });

  it("ranks a node after its longest path, not its shortest", () => {
    const p = layered(nodes("a", "b", "c"), [edge("a", "b"), edge("b", "c"), edge("a", "c")], LR);
    expect(p.get("c")!.x).toBe(560);
  });

  it("ends on a cycle and ranks the rest by the edges that remain", () => {
    const p = layered(nodes("a", "b", "c", "z"), [edge("a", "b"), edge("b", "c"), edge("c", "a"), edge("c", "z")], LR);
    expect(p.size).toBe(4);
    expect([p.get("a")!.x, p.get("b")!.x, p.get("c")!.x, p.get("z")!.x]).toEqual([0, 280, 560, 840]);
  });

  it("ends on a cycle with no source and on a cycle of two", () => {
    expect(layered(nodes("a", "b"), [edge("a", "b"), edge("b", "a")], LR).size).toBe(2);
    const p = layered(nodes("a", "b", "c"), [edge("a", "b"), edge("b", "c"), edge("c", "a")], LR);
    expect(new Set([...p.values()].map((v) => v.x)).size).toBe(3);
  });

  it("keeps an explicit rank and order, and reproduces the mapping canvas's positions from depth and row", () => {
    // The mapping canvas puts a mapping at depth * COLUMN, row * ROW with COLUMN 280 and ROW 64, and its source concepts one rank before.
    const mappings = [
      { id: "root", depth: 0, row: 0, parent: undefined, source: "s1" },
      { id: "a", depth: 1, row: 1, parent: "root", source: "s1" },
      { id: "a1", depth: 2, row: 2, parent: "a", source: "s2" },
      { id: "b", depth: 1, row: 3, parent: "root", source: undefined },
      { id: "tmpl", depth: 0, row: 4, parent: undefined, source: undefined },
    ];
    const sources = ["s1", "s2"];
    const ns: LayoutNode[] = [
      ...sources.map((id, n) => ({ id, rank: -1, order: n })),
      ...mappings.map((m) => ({ id: m.id, rank: m.depth, order: m.row })),
    ];
    const es = mappings.flatMap((m) => [...(m.parent ? [edge(m.parent, m.id)] : []), ...(m.source ? [edge(m.source, m.id)] : [])]);
    const p = layered(shuffled(ns, 3), shuffled(es, 4), LR);
    for (const m of mappings) expect(p.get(m.id)).toEqual({ x: m.depth * 280, y: m.row * 64 });
    sources.forEach((id, n) => expect(p.get(id)).toEqual({ x: -280, y: n * 64 }));
  });

  it("uses an explicit order as a slot, so a gap is kept, and moves a repeated order to the next slot", () => {
    const p = layered([{ id: "a", rank: 0, order: 0 }, { id: "b", rank: 0, order: 3 }, { id: "c", rank: 0, order: 3 }], [], LR);
    expect([p.get("a")!.y, p.get("b")!.y, p.get("c")!.y]).toEqual([0, 3 * 64, 4 * 64]);
  });

  it("puts nodes with no edge in a rank after the rest, sorted by id", () => {
    const p = layered(nodes("a", "b", "y", "x"), [edge("a", "b")], LR);
    expect(p.get("x")).toEqual({ x: 560, y: 0 });
    expect(p.get("y")).toEqual({ x: 560, y: 64 });
    expect(layered(nodes("q", "p"), [], LR).get("p")).toEqual({ x: 0, y: 0 });
  });

  it("keeps an explicit rank on a node with no edge", () => {
    expect(layered([{ id: "a", rank: 2, order: 5 }, { id: "b" }], [], LR).get("a")).toEqual({ x: 560, y: 320 });
  });

  it("keeps the nodes of a group next to each other within a rank", () => {
    const ns: LayoutNode[] = [
      { id: "r" },
      { id: "c1", group: "g1" }, { id: "c2", group: "g2" }, { id: "c3", group: "g1" }, { id: "c4", group: "g2" },
    ];
    const p = layered(ns, ["c1", "c2", "c3", "c4"].map((c) => edge("r", c)), LR);
    const order = ["c1", "c2", "c3", "c4"].sort((a, b) => p.get(a)!.y - p.get(b)!.y);
    expect(order).toEqual(["c1", "c3", "c2", "c4"]);
  });

  it("orders a rank by the barycentre of its neighbours, so a crossing is removed", () => {
    // Ids sort a1, a2 and b1, b2, but a1 feeds b2 and a2 feeds b1, so b2 belongs above b1.
    const p = layered(nodes("a1", "a2", "b1", "b2"), [edge("a1", "b2"), edge("a2", "b1")], LR);
    expect(p.get("b2")!.y).toBeLessThan(p.get("b1")!.y);
  });

  it("takes node sizes into account in both directions", () => {
    const ns: LayoutNode[] = [{ id: "a", width: 100, height: 30 }, { id: "b", width: 60, height: 40 }, { id: "c", width: 60, height: 40 }];
    const es = [edge("a", "b"), edge("a", "c")];
    const lr = layered(ns, es, { direction: "LR", columnGap: 20, rowGap: 10 });
    expect(lr.get("a")).toEqual({ x: 0, y: 0 });
    expect(lr.get("b")).toEqual({ x: 20 + 100, y: 0 });
    expect(lr.get("c")).toEqual({ x: 120, y: 10 + 40 });
    const tb = layered(ns, es, { direction: "TB", columnGap: 20, rowGap: 10 });
    expect(tb.get("b")).toEqual({ x: 0, y: 20 + 30 });
    expect(tb.get("c")).toEqual({ x: 10 + 60, y: 50 });
  });

  it("runs ranks downwards in TB", () => {
    const p = layered(nodes("a", "b"), [edge("a", "b")], TB);
    expect(p.get("a")).toEqual({ x: 0, y: 0 });
    expect(p.get("b")).toEqual({ x: 0, y: 100 });
  });

  it("gives the same positions for the same graph in any order and on a repeat", () => {
    const { nodes: ns, edges: es } = generated(120);
    const base = entries(layered(ns, es, LR));
    for (const seed of [1, 2, 3, 4]) expect(entries(layered(shuffled(ns, seed), shuffled(es, seed + 10), LR))).toEqual(base);
    expect(entries(layered(ns, es, LR))).toEqual(base);
    const plain = [...ns.map((n) => ({ ...n, group: Number(n.id.slice(1)) % 3 ? "x" : "y" }))];
    expect(entries(layered(shuffled(plain, 9), shuffled(es, 8), LR))).toEqual(entries(layered(plain, es, LR)));
  });

  it("puts no two nodes at one position, and runs every edge of an acyclic graph from a lower x to a higher one", () => {
    const { nodes: ns, edges: es } = generated(300);
    const forward = es.filter((e) => e.source < e.target && Number(e.source.slice(1)) < Number(e.target.slice(1)));
    // The generator's back edges run from a later node to an earlier one, so the rest is acyclic.
    const p = layered(ns, forward, LR);
    expect(new Set([...p.values()].map((v) => `${v.x},${v.y}`)).size).toBe(ns.length);
    for (const e of forward) expect(p.get(e.source)!.x).toBeLessThan(p.get(e.target)!.x);
    const q = layered(ns, es, LR);
    expect(new Set([...q.values()].map((v) => `${v.x},${v.y}`)).size).toBe(ns.length);
  });

  it("ignores an edge to a node that is not given, an edge from a node to itself and a repeated edge", () => {
    const p = layered(nodes("a", "b"), [edge("a", "b"), edge("a", "b"), edge("a", "ghost"), edge("ghost", "b"), edge("b", "b")], LR);
    expect(p.size).toBe(2);
    expect(p.get("b")).toEqual({ x: 280, y: 0 });
  });

  it("throws on a repeated id, and names it", () => {
    expect(() => layered(nodes("a", "b", "a"), [], LR)).toThrow(/"a" is given more than once/);
  });

  it("returns nothing for nothing", () => {
    expect(layered([], [], LR).size).toBe(0);
  });
});

describe("the layered layout's time", () => {
  // A measurement. It prints its figures and asserts only that each size finishes with a position for every node (ADR-A124).
  for (const size of [100, 500, 2000]) {
    it(`lays out ${size} nodes`, () => {
      const { nodes: ns, edges: es } = generated(size);
      const t0 = performance.now();
      const p = layered(ns, es, LR);
      const ms = performance.now() - t0;
      console.log(`layout-time nodes=${size} edges=${es.length} ms=${ms.toFixed(1)}`);
      expect(p.size).toBe(size);
      for (const n of ns) expect(p.has(n.id)).toBe(true);
    });
  }
});
