// SPDX-License-Identifier: MPL-2.0
// What the persistence simulator keeps for a workspace in this tab (SVA-Q3, SVA-Q13, ADR-A154 decision 11): the sample world and the steps that made
// it, what the author has typed, and the places the last step lit on the canvas. It is memory of the page and nothing else, so a reload starts
// the world again, no worker holds it, and the surface simulator reads the same world later. The canvas and the pane read it through `useSim`.

import { useSyncExternalStore } from "react";
import type { FormValues } from "./objectForm";
import { EMPTY_FORM } from "./objectForm";
import type { Lit, StepRecord, WriteKind, World } from "./simulator";

/** What the author has given for the object of a target. */
export interface Draft {
  root: string;
  mode: "form" | "turtle";
  form: FormValues;
  turtle: string;
}

export interface Sim {
  /** Undefined until the first target of a compilation gives it its starting point. */
  world?: World;
  steps: StepRecord[];
  target?: string;
  write: WriteKind;
  /** The operation by name where more than one serves the write. */
  operation?: string;
  asAnotherWriter: boolean;
  time: string;
  drafts: Record<string, Draft>;
  lit: Lit[];
}

/** The transaction time a step is stated at until the author states another. A fixed time, never the clock, so that a step sent twice is the same. */
export const DEFAULT_TIME = "2026-01-15T09:00:00Z";

export const INITIAL: Sim = { steps: [], write: "create", asAnotherWriter: false, time: DEFAULT_TIME, drafts: {}, lit: [] };

const sims = new Map<string, Sim>();
const listeners = new Set<() => void>();

export function getSim(workspace: string): Sim {
  return sims.get(workspace) ?? INITIAL;
}

export function setSim(workspace: string, change: Partial<Sim> | ((current: Sim) => Partial<Sim>)): void {
  const current = getSim(workspace);
  sims.set(workspace, { ...current, ...(typeof change === "function" ? change(current) : change) });
  listeners.forEach((l) => l());
}

export function subscribeSim(listener: () => void): () => void {
  listeners.add(listener);
  return () => void listeners.delete(listener);
}

export function useSim(workspace: string): Sim {
  return useSyncExternalStore(subscribeSim, () => getSim(workspace), () => INITIAL);
}

/** Removes the last step and restores the world before it. Nothing happens when there is no step. The places lit by that step go dark. */
export function stepBack(workspace: string): void {
  setSim(workspace, (s) => {
    const last = s.steps[s.steps.length - 1];
    return last ? { world: last.before, steps: s.steps.slice(0, -1), lit: [] } : {};
  });
}

export function draftOf(sim: Sim, target: string, root: string): Draft {
  return sim.drafts[target] ?? { root, mode: "form", form: EMPTY_FORM, turtle: "" };
}

/** Forgets everything of a workspace, for a test. */
export function forgetSims(): void {
  sims.clear();
  listeners.forEach((l) => l());
}
