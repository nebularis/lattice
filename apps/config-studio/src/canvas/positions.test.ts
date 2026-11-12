// SPDX-License-Identifier: MPL-2.0
// The author's stored positions, against a fake store, since the unit suite runs where there is no browser.

import { describe, expect, it } from "vitest";
import { clearPositions, readPositions, resolvePositions, writePositions, type PositionStore } from "./positions";

function fake(initial: Record<string, string> = {}): PositionStore & { data: Record<string, string> } {
  const data = { ...initial };
  return {
    data,
    getItem: (k) => data[k] ?? null,
    setItem: (k, v) => void (data[k] = v),
    removeItem: (k) => void delete data[k],
  };
}
const refusing: PositionStore = {
  getItem: () => {
    throw new Error("blocked");
  },
  setItem: () => {
    throw new Error("blocked");
  },
  removeItem: () => {
    throw new Error("blocked");
  },
};

describe("stored positions", () => {
  it("are written and read back under their key", () => {
    const store = fake();
    writePositions("k", { a: { x: 1, y: 2 } }, store);
    expect(readPositions("k", store)).toEqual({ a: { x: 1, y: 2 } });
    expect(readPositions("other", store)).toEqual({});
  });

  it("are empty where the browser keeps nothing, and a read or write never throws", () => {
    expect(readPositions("k", undefined)).toEqual({});
    expect(() => writePositions("k", { a: { x: 1, y: 2 } }, undefined)).not.toThrow();
    expect(readPositions("k", refusing)).toEqual({});
    expect(() => writePositions("k", {}, refusing)).not.toThrow();
    expect(() => clearPositions("k", refusing)).not.toThrow();
  });

  it("ignore what is not a position", () => {
    expect(readPositions("k", fake({ k: "not json" }))).toEqual({});
    expect(readPositions("k", fake({ k: "[1,2]" }))).toEqual({});
    expect(readPositions("k", fake({ k: JSON.stringify({ a: { x: 1, y: 2 }, b: { x: "1", y: 2 }, c: null, d: 5 }) }))).toEqual({ a: { x: 1, y: 2 } });
  });

  it("are forgotten by laying out again", () => {
    const store = fake();
    writePositions("k", { a: { x: 1, y: 2 } }, store);
    clearPositions("k", store);
    expect(readPositions("k", store)).toEqual({});
  });
});

describe("where a node sits", () => {
  const laid = new Map([["a", { x: 0, y: 0 }], ["b", { x: 280, y: 0 }], ["c", { x: 280, y: 64 }]]);
  const saved = { b: { x: 5, y: 6 } };

  it("is the layout's for a node nobody placed, and the saved position for one the author placed", () => {
    expect(resolvePositions(["a", "b", "c"], laid, saved)).toEqual(new Map([["a", { x: 0, y: 0 }], ["b", { x: 5, y: 6 }], ["c", { x: 280, y: 64 }]]));
  });

  it("keeps every node where it is now after an edit, and lays out only a new node", () => {
    const current = new Map([["a", { x: 9, y: 9 }], ["b", { x: 7, y: 7 }]]);
    expect(resolvePositions(["a", "b", "c"], laid, saved, current)).toEqual(new Map([["a", { x: 9, y: 9 }], ["b", { x: 7, y: 7 }], ["c", { x: 280, y: 64 }]]));
  });

  it("is the layout's for every node when laid out again, with nothing saved and nothing current", () => {
    expect([...resolvePositions(["a", "b", "c"], laid, {}).values()]).toEqual([...laid.values()]);
  });
});
