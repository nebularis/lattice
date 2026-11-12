// SPDX-License-Identifier: MPL-2.0
// Where the author left each node of a canvas. Positions are kept in this browser under a key for the canvas and never enter a
// graph, since where a node sits says nothing about what it means. A browser that keeps nothing lays the canvas out afresh on
// the next visit, and a canvas still draws.

export interface Point {
  x: number;
  y: number;
}

export type Positions = Record<string, Point>;

/** The part of `Storage` that is used, so a test can give it a fake. */
export type PositionStore = Pick<Storage, "getItem" | "setItem" | "removeItem">;

/** The browser's local storage, or nothing where it is blocked or absent. */
export function browserStore(): PositionStore | undefined {
  try {
    return typeof localStorage === "undefined" ? undefined : localStorage;
  } catch {
    return undefined;
  }
}

const isPoint = (p: unknown): p is Point => typeof p === "object" && p !== null && Number.isFinite((p as Point).x) && Number.isFinite((p as Point).y);

export function readPositions(key: string, store: PositionStore | undefined = browserStore()): Positions {
  try {
    const parsed: unknown = JSON.parse(store?.getItem(key) ?? "{}");
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) return {};
    return Object.fromEntries(Object.entries(parsed).filter(([, p]) => isPoint(p)).map(([id, p]) => [id, { x: (p as Point).x, y: (p as Point).y }]));
  } catch {
    return {};
  }
}

export function writePositions(key: string, positions: Positions, store: PositionStore | undefined = browserStore()): void {
  try {
    store?.setItem(key, JSON.stringify(positions));
  } catch {
    // A browser that keeps nothing lays the canvas out afresh on the next visit.
  }
}

/** "Lay out again" forgets what the author placed. */
export function clearPositions(key: string, store: PositionStore | undefined = browserStore()): void {
  try {
    store?.removeItem(key);
  } catch {
    // Nothing was kept, or it cannot be removed, and the next write replaces it.
  }
}

/**
 * Where each node sits. A node the author or an edit already placed stays where it is, so a link dropped where a node was still
 * lands on it, then the author's saved position, then the layout's. Only a new node is laid out. Laying out again ignores what is
 * placed on the canvas now, and the caller clears what was saved.
 */
export function resolvePositions(ids: readonly string[], laid: ReadonlyMap<string, Point>, saved: Positions, current?: ReadonlyMap<string, Point>): Map<string, Point> {
  return new Map(ids.map((id) => [id, current?.get(id) ?? saved[id] ?? laid.get(id) ?? { x: 0, y: 0 }]));
}
