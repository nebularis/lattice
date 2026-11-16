// SPDX-License-Identifier: MPL-2.0
// The page's columns, against a fake store, since the unit suite runs where there is no browser.

import { describe, expect, it } from "vitest";
import type { PositionStore } from "../canvas/positions";
import { DOCK, LIST, MIDDLE_MIN, NAV_WIDTH, RAIL, STEP, clampWidth, columnKey, dockDefaultCollapsed, dockDefaultWidth, keyedWidth, maxWidth, readColumn, resolveWidth, writeColumn } from "./columns";

function fake(initial: Record<string, string> = {}): PositionStore & { data: Record<string, string> } {
  const data = { ...initial };
  return { data, getItem: (k) => data[k] ?? null, setItem: (k, v) => void (data[k] = v), removeItem: (k) => void delete data[k] };
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

describe("the key of a column", () => {
  it("is one for the navigation and one for the dock, and one per view for the list", () => {
    expect(columnKey("nav")).not.toBe(columnKey("dock"));
    expect(columnKey("list", "baseline")).not.toBe(columnKey("list", "mapping"));
    expect(columnKey("list", "baseline")).toBe(columnKey("list", "baseline"));
    expect(columnKey("list", "baseline")).not.toBe(columnKey("nav"));
  });
});

describe("a stored column", () => {
  it("is read back as it was written", () => {
    const store = fake();
    writeColumn(columnKey("dock"), { collapsed: true, width: 410 }, store);
    expect(readColumn(columnKey("dock"), store)).toEqual({ collapsed: true, width: 410 });
  });

  it("is the defaults where nothing was kept", () => {
    expect(readColumn(columnKey("nav"), fake())).toEqual({});
  });

  it("ignores a value that is not valid, part by part", () => {
    const key = columnKey("list", "baseline");
    expect(readColumn(key, fake({ [key]: "not json" }))).toEqual({});
    expect(readColumn(key, fake({ [key]: "[1,2]" }))).toEqual({});
    expect(readColumn(key, fake({ [key]: '{"collapsed":"yes","width":"wide"}' }))).toEqual({});
    expect(readColumn(key, fake({ [key]: '{"collapsed":true,"width":-5}' }))).toEqual({ collapsed: true });
    expect(readColumn(key, fake({ [key]: '{"collapsed":1,"width":300}' }))).toEqual({ width: 300 });
  });

  it("is the defaults, and a write is harmless, where the browser keeps nothing", () => {
    expect(readColumn("k", refusing)).toEqual({});
    expect(() => writeColumn("k", { width: 300 }, refusing)).not.toThrow();
    expect(readColumn("k", undefined)).toEqual({});
  });

  it("is kept per view for the list", () => {
    const store = fake();
    writeColumn(columnKey("list", "baseline"), { width: 300 }, store);
    writeColumn(columnKey("list", "mapping"), { collapsed: true }, store);
    expect(readColumn(columnKey("list", "baseline"), store)).toEqual({ width: 300 });
    expect(readColumn(columnKey("list", "mapping"), store)).toEqual({ collapsed: true });
    expect(readColumn(columnKey("list", "library"), store)).toEqual({});
  });
});

describe("the width of a column", () => {
  it("is the default where none is stored", () => {
    expect(resolveWidth(undefined, LIST, 1600, NAV_WIDTH + DOCK.default)).toBe(LIST.default);
  });

  it("is raised to its minimum", () => {
    expect(resolveWidth(40, LIST, 1600, 600)).toBe(LIST.min);
  });

  it("is lowered to what the window allows, keeping the middle its minimum", () => {
    const others = NAV_WIDTH + DOCK.default;
    expect(resolveWidth(5000, LIST, 1600, others)).toBe(1600 - others - MIDDLE_MIN);
  });

  it("is the minimum where the window allows less, and the middle yields", () => {
    expect(resolveWidth(500, DOCK, 900, NAV_WIDTH + LIST.default)).toBe(DOCK.min);
    expect(clampWidth(100, 220, 50)).toBe(220);
  });

  it("is a whole number of pixels", () => {
    expect(clampWidth(300.6, 220, 800)).toBe(301);
  });

  it("allows the window less the other columns and the middle's minimum", () => {
    expect(maxWidth(1440, 500)).toBe(1440 - 500 - MIDDLE_MIN);
  });
});

describe("the dock's default", () => {
  it("is wide for the run pane's columns only where the middle keeps room to spare beside it", () => {
    expect(dockDefaultWidth(1920, NAV_WIDTH + 340, true)).toBe(DOCK.wide);
    expect(dockDefaultWidth(1600, NAV_WIDTH + 340, true)).toBe(DOCK.default);
    expect(dockDefaultWidth(1200, NAV_WIDTH + 340, true)).toBe(DOCK.default);
    expect(dockDefaultWidth(1920, NAV_WIDTH + 340, false)).toBe(DOCK.default);
  });

  it("is collapsed only where an open dock would leave the middle less than its minimum", () => {
    const needed = NAV_WIDTH + LIST.default + DOCK.min + MIDDLE_MIN;
    expect(dockDefaultCollapsed(needed)).toBe(false);
    expect(dockDefaultCollapsed(needed - 1)).toBe(true);
    expect(dockDefaultCollapsed(1600)).toBe(false);
    expect(dockDefaultCollapsed(1100)).toBe(true);
  });

  it("has a rail narrower than any column's minimum", () => {
    expect(RAIL).toBeLessThan(LIST.min);
    expect(RAIL).toBeLessThan(DOCK.min);
  });
});

describe("the keys of a handle", () => {
  it("widen with the arrow that grows the column and narrow with the other, by a step", () => {
    expect(keyedWidth("ArrowRight", 300, 220, 700, "ArrowRight")).toBe(300 + STEP);
    expect(keyedWidth("ArrowLeft", 300, 220, 700, "ArrowRight")).toBe(300 - STEP);
    expect(keyedWidth("ArrowLeft", 300, 300, 700, "ArrowLeft")).toBe(300 + STEP);
    expect(keyedWidth("ArrowRight", 400, 300, 700, "ArrowLeft")).toBe(400 - STEP);
  });

  it("stop at the limits", () => {
    expect(keyedWidth("ArrowLeft", 225, 220, 700, "ArrowRight")).toBe(220);
    expect(keyedWidth("ArrowRight", 695, 220, 700, "ArrowRight")).toBe(700);
  });

  it("go to the minimum on Home and the maximum on End, and ignore any other key", () => {
    expect(keyedWidth("Home", 400, 220, 700, "ArrowRight")).toBe(220);
    expect(keyedWidth("End", 400, 220, 700, "ArrowRight")).toBe(700);
    expect(keyedWidth("a", 400, 220, 700, "ArrowRight")).toBeUndefined();
  });
});
