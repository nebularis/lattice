// SPDX-License-Identifier: MPL-2.0
// Where a node an edit added is drawn when the place the layout gives it is already taken. A node that kept its place never moves,
// so the new node moves, to the nearest place where its box covers no other node's. The search is pure and deterministic, so the
// same nodes give the same places for any order of the input, and it is bounded, so a crowded canvas still gets an answer.

import type { Point } from "./positions";

export interface Size {
  width: number;
  height: number;
}

export interface PlaceBox extends Point, Size {}

export interface Spacing {
  /** The direction the layout runs. A step along it is one column gap, a step across it is one row gap. */
  direction: "LR" | "TB";
  columnGap: number;
  rowGap: number;
  /** The space kept between two boxes, so a node is not drawn touching another. */
  margin?: number;
  /** How many steps away in each direction a place is looked for, before the layout's place is kept. */
  reach?: number;
}

/** The space kept between two boxes where not given. */
export const PLACE_MARGIN = 8;
/** How many steps are tried each way where not given, 6 in each direction, so 169 places at most for each node. */
export const PLACE_REACH = 6;

const compare = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);

const covers = (a: PlaceBox, b: PlaceBox, margin: number) => a.x < b.x + b.width + margin && b.x < a.x + a.width + margin && a.y < b.y + b.height + margin && b.y < a.y + a.height + margin;

/**
 * The place of each new node. A node whose wanted place covers no node of `kept` and no new node placed before it keeps its wanted
 * place. Any other takes the nearest place, by the distance it is moved, among the places a whole step away in each direction, a step
 * across the layout being the node's own size and a row gap, and a step along it the node's size and a column gap. Places at one
 * distance are tried by the lower side across the layout first, then the further side along it. New nodes are placed in order of
 * id, each seeing the ones placed before it. Where no place within `reach` steps is free the node keeps its wanted place.
 */
export function placeClear(wanted: ReadonlyMap<string, Point>, sizeOf: (id: string) => Size, kept: Iterable<PlaceBox>, spacing: Spacing): Map<string, Point> {
  const { direction, columnGap, rowGap, margin = PLACE_MARGIN, reach = PLACE_REACH } = spacing;
  const taken: PlaceBox[] = [...kept];
  const out = new Map<string, Point>();
  for (const id of [...wanted.keys()].sort(compare)) {
    const at = wanted.get(id)!;
    const size = sizeOf(id);
    const lr = direction === "LR";
    const alongStep = lr ? size.width + columnGap : size.height + columnGap;
    const acrossStep = lr ? size.height + rowGap : size.width + rowGap;
    const offsets: { along: number; across: number; distance: number }[] = [];
    for (let along = -reach; along <= reach; along++) {
      for (let across = -reach; across <= reach; across++) offsets.push({ along, across, distance: (along * alongStep) ** 2 + (across * acrossStep) ** 2 });
    }
    offsets.sort((p, q) => p.distance - q.distance || q.across - p.across || q.along - p.along);
    let chosen: PlaceBox | undefined;
    for (const o of offsets) {
      const box = { x: at.x + (lr ? o.along * alongStep : o.across * acrossStep), y: at.y + (lr ? o.across * acrossStep : o.along * alongStep), ...size };
      if (taken.every((t) => !covers(box, t, margin))) {
        chosen = box;
        break;
      }
    }
    const box = chosen ?? { x: at.x, y: at.y, ...size };
    taken.push(box);
    out.set(id, { x: box.x, y: box.y });
  }
  return out;
}
