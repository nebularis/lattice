// SPDX-License-Identifier: MPL-2.0
// A node an edit adds is drawn clear of the nodes that kept their places, the nodes that kept them never move, and the search is
// deterministic and bounded.

import { describe, expect, it } from "vitest";
import { placeClear, type PlaceBox, type Spacing } from "./place";
import { resolvePositions, type Point } from "./positions";

const size = { width: 240, height: 51 };
const spacing: Spacing = { direction: "LR", columnGap: 280, rowGap: 64 };
const sizeOf = () => size;
const box = (x: number, y: number): PlaceBox => ({ x, y, ...size });
const wantedAt = (entries: Record<string, Point>) => new Map(Object.entries(entries));
const covers = (a: PlaceBox, b: PlaceBox) => a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height;
const boxOf = (p: Point): PlaceBox => ({ ...p, ...size });

describe("the place of a new node", () => {
  it("is the layout's where nothing covers it", () => {
    const out = placeClear(wantedAt({ n: { x: 520, y: 0 } }), sizeOf, [box(0, 0)], spacing);
    expect(out.get("n")).toEqual({ x: 520, y: 0 });
  });

  it("is the nearest free place where the layout's is taken, and no node that kept its place is moved", () => {
    const kept = [box(0, 0)];
    const out = placeClear(wantedAt({ n: { x: 0, y: 0 } }), sizeOf, kept, spacing);
    // One row gap below is the nearest, since a row's step is shorter than a column's.
    expect(out.get("n")).toEqual({ x: 0, y: size.height + spacing.rowGap });
    expect(kept).toEqual([box(0, 0)]);
  });

  it("goes further down where the nearest places are taken too, and then to the other side", () => {
    const step = size.height + spacing.rowGap;
    const kept = [box(0, 0), box(0, step), box(0, 2 * step)];
    const out = placeClear(wantedAt({ n: { x: 0, y: 0 } }), sizeOf, kept, spacing);
    expect(out.get("n")).toEqual({ x: 0, y: -step });
  });

  it("is not within the margin of a node, where a node is only just clear of the layout's place", () => {
    const out = placeClear(wantedAt({ n: { x: 0, y: 0 } }), sizeOf, [box(0, size.height + 2)], spacing);
    expect(out.get("n")!.y).not.toBe(0);
    expect(covers(boxOf(out.get("n")!), box(0, size.height + 2))).toBe(false);
  });

  it("gives two new nodes that want one place different places, in order of id", () => {
    const out = placeClear(wantedAt({ b: { x: 0, y: 0 }, a: { x: 0, y: 0 } }), sizeOf, [], spacing);
    expect(out.get("a")).toEqual({ x: 0, y: 0 });
    expect(out.get("b")).not.toEqual({ x: 0, y: 0 });
    expect(covers(boxOf(out.get("a")!), boxOf(out.get("b")!))).toBe(false);
  });

  it("gives the same places for any order of the input, and on a repeat", () => {
    const kept = [box(0, 0), box(0, 115), box(520, 0)];
    const entries: [string, Point][] = [["c", { x: 0, y: 0 }], ["a", { x: 0, y: 0 }], ["b", { x: 520, y: 0 }], ["d", { x: 0, y: 115 }]];
    const first = placeClear(new Map(entries), sizeOf, kept, spacing);
    const reversed = placeClear(new Map([...entries].reverse()), sizeOf, [...kept].reverse(), spacing);
    expect([...reversed].sort()).toEqual([...first].sort());
    expect([...placeClear(new Map(entries), sizeOf, kept, spacing)]).toEqual([...first]);
    const placed = [...first.values()].map(boxOf);
    for (let i = 0; i < placed.length; i++) {
      for (const k of kept) expect(covers(placed[i], k)).toBe(false);
      for (let j = i + 1; j < placed.length; j++) expect(covers(placed[i], placed[j])).toBe(false);
    }
  });

  it("runs along the layout's direction in TB, where a step along it is down", () => {
    const tb: Spacing = { direction: "TB", columnGap: 110, rowGap: 280 };
    const out = placeClear(wantedAt({ n: { x: 0, y: 0 } }), sizeOf, [box(0, 0)], tb);
    // A step across a rank is the node's width and the row gap, a step along it its height and the column gap, which is the nearer.
    expect(out.get("n")).toEqual({ x: 0, y: size.height + tb.columnGap });
  });

  it("ends where the canvas is crowded, and keeps the layout's place", () => {
    const crowd: PlaceBox[] = [];
    for (let x = -4000; x <= 4000; x += 120) for (let y = -4000; y <= 4000; y += 40) crowd.push({ x, y, ...size });
    const out = placeClear(wantedAt({ n: { x: 10, y: 20 } }), sizeOf, crowd, spacing);
    expect(out.get("n")).toEqual({ x: 10, y: 20 });
  });
});

describe("resolvePositions with a clearance", () => {
  const laid = new Map<string, Point>([["a", { x: 0, y: 0 }], ["b", { x: 0, y: 115 }], ["n", { x: 0, y: 0 }]]);
  const clearance = { ...spacing, sizeOf };

  it("moves a new node off the node that kept the layout's place, and leaves that one where it is", () => {
    const at = resolvePositions(["a", "b", "n"], laid, {}, new Map([["a", { x: 0, y: 0 }], ["b", { x: 300, y: 300 }]]), clearance);
    expect(at.get("a")).toEqual({ x: 0, y: 0 });
    expect(at.get("b")).toEqual({ x: 300, y: 300 });
    expect(covers(boxOf(at.get("n")!), box(0, 0))).toBe(false);
  });

  it("takes a node's saved place as a kept one", () => {
    const at = resolvePositions(["a", "n"], laid, { a: { x: 0, y: 0 } }, undefined, clearance);
    expect(at.get("a")).toEqual({ x: 0, y: 0 });
    expect(covers(boxOf(at.get("n")!), box(0, 0))).toBe(false);
  });

  it("gives every node the layout's own place where none kept one, as in laying out again", () => {
    const at = resolvePositions(["a", "b", "n"], laid, {}, undefined, clearance);
    expect(at).toEqual(laid);
  });

  it("is as it was where no clearance is given", () => {
    const at = resolvePositions(["a", "n"], laid, {}, new Map([["a", { x: 0, y: 0 }]]));
    expect(at.get("n")).toEqual({ x: 0, y: 0 });
  });
});
