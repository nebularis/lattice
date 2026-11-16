// SPDX-License-Identifier: MPL-2.0
// How the page's width is shared (SVA-U1). The navigation, the mode's list column and the dock each collapse to a rail, and the list
// and the dock are resized by the author. Each column's state is kept in this browser under a key and never enters a graph, since how
// wide a column is says nothing about what a configuration means. A browser that keeps nothing starts each visit from the defaults,
// and the page still lays out. This module is pure, so a test can give it a fake store.

import { browserStore, type PositionStore } from "../canvas/positions";

/** The width of a collapsed column, which shows only the button that brings it back. */
export const RAIL = 36;
/** The navigation's width when it is open. It is collapsed and expanded, never resized. */
export const NAV_WIDTH = 236;
/** The room the middle column keeps, so a drag stops before it pushes the content off the page. */
export const MIDDLE_MIN = 360;
/** The room the middle keeps for the dock to start wide, so a wide default never squeezes a canvas. */
export const MIDDLE_ROOMY = 700;
/** What a keyboard step on a handle moves its column by. */
export const STEP = 16;

export type Column = "nav" | "list" | "dock";

export interface Limits {
  min: number;
  default: number;
}

/** A list column's usual limits. A view whose list holds an outline gives a wider default and minimum. */
export const LIST: Limits = { min: 220, default: 280 };
/** The dock's limits, and the wider default for the run pane's two columns. */
export const DOCK: Limits & { wide: number } = { min: 300, default: 340, wide: 620 };

/** What is kept for a column. A value that is absent takes its default. */
export interface ColumnState {
  collapsed?: boolean;
  width?: number;
}

const PREFIX = "lattice.studio.columns";

/** The key a column's state is kept under. The list column is kept per view, since a view's list holds different things. */
export function columnKey(column: Column, view?: string): string {
  return column === "list" ? `${PREFIX}.list.${view ?? ""}` : `${PREFIX}.${column}`;
}

/** The state kept under a key, ignoring any part that is not valid and everything where the browser keeps nothing or holds nonsense. */
export function readColumn(key: string, store: PositionStore | undefined = browserStore()): ColumnState {
  try {
    const parsed: unknown = JSON.parse(store?.getItem(key) ?? "null");
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) return {};
    const { collapsed, width } = parsed as Record<string, unknown>;
    return {
      ...(typeof collapsed === "boolean" ? { collapsed } : {}),
      ...(typeof width === "number" && Number.isFinite(width) && width > 0 ? { width } : {}),
    };
  } catch {
    return {};
  }
}

export function writeColumn(key: string, state: ColumnState, store: PositionStore | undefined = browserStore()): void {
  try {
    store?.setItem(key, JSON.stringify(state));
  } catch {
    // A browser that keeps nothing starts the next visit from the defaults.
  }
}

/** A width within its limits. Where the room allows less than the minimum, the minimum stands and the middle yields. */
export function clampWidth(width: number, min: number, max: number): number {
  return Math.round(Math.min(Math.max(width, min), Math.max(min, max)));
}

/** The most a column may take, given the window and the width the other columns hold, rails included. */
export function maxWidth(windowWidth: number, others: number): number {
  return windowWidth - others - MIDDLE_MIN;
}

/** A column's width, the stored one or the default, within its minimum and what the window allows. */
export function resolveWidth(stored: number | undefined, limits: Limits, windowWidth: number, others: number): number {
  return clampWidth(stored ?? limits.default, limits.min, maxWidth(windowWidth, others));
}

/** The dock's default width, the wide one only where the middle would still have room to spare, `MIDDLE_ROOMY`, beside it. */
export function dockDefaultWidth(windowWidth: number, others: number, wide: boolean): number {
  return wide && maxWidth(windowWidth, others) - (MIDDLE_ROOMY - MIDDLE_MIN) >= DOCK.wide ? DOCK.wide : DOCK.default;
}

/** The dock starts collapsed only where the window cannot give the middle its minimum beside an open dock, the navigation and a list. */
export function dockDefaultCollapsed(windowWidth: number): boolean {
  return windowWidth < NAV_WIDTH + LIST.default + DOCK.min + MIDDLE_MIN;
}

/** Where a key moves a handle's column, or undefined for a key that does nothing. `grows` is the direction of the arrow that widens the column. */
export function keyedWidth(key: string, width: number, min: number, max: number, grows: "ArrowLeft" | "ArrowRight"): number | undefined {
  const shrinks = grows === "ArrowLeft" ? "ArrowRight" : "ArrowLeft";
  if (key === grows) return clampWidth(width + STEP, min, max);
  if (key === shrinks) return clampWidth(width - STEP, min, max);
  if (key === "Home") return clampWidth(min, min, max);
  if (key === "End") return clampWidth(max, min, max);
  return undefined;
}
