// SPDX-License-Identifier: MPL-2.0
// The latest finished persistence compilation of a workspace, read for the canvas and for the simulator beside it (SVA-P1, SVA-P4). Both draw or run
// what that compilation holds, so they read it the same way and the simulator reads it again when the canvas has compiled.

import { useSyncExternalStore } from "react";
import { api, awaitJob, jobId } from "../api";
import { finished, type Job } from "../rdf/report";
import { COMPILED_PROFILE, readLanding, type LandingPlaces } from "./landing";

export type Load =
  | { state: "loading" }
  | { state: "none" }
  | { state: "refused"; job: Job }
  | { state: "old"; job: Job }
  | { state: "ready"; job: Job; doc: LandingPlaces }
  | { state: "error"; message: string };

/** The latest finished persistence compilation of the workspace, newest first by when it was submitted. */
export function latest(jobs: Job[]): Job | undefined {
  return jobs
    .filter((j) => j.kind === "Compile" && j.target === "Persistence" && finished(j))
    .sort((a, b) => (b.submittedAt ?? "").localeCompare(a.submittedAt ?? "") || b.iri.localeCompare(a.iri))[0];
}

export async function read(workspace: string): Promise<Load> {
  const row = latest(await api.compileJobs(workspace));
  if (!row) return { state: "none" };
  const job = await awaitJob(jobId(row.iri));
  if (job.status !== "Succeeded" || !job.conforms) return { state: "refused", job };
  const file = job.artefacts.find((a) => a.path === COMPILED_PROFILE);
  if (!file) return { state: "old", job };
  const reading = readLanding(file.content);
  return reading.state === "ready" ? { state: "ready", job, doc: reading.doc } : { state: "old", job };
}

// A count that moves when a compilation finishes in this tab, so that a pane reading the latest one reads it again.
let epoch = 0;
const listeners = new Set<() => void>();

export function noteCompiled(): void {
  epoch++;
  listeners.forEach((l) => l());
}

export function useCompilationEpoch(): number {
  return useSyncExternalStore(
    (listener) => (listeners.add(listener), () => void listeners.delete(listener)),
    () => epoch,
    () => 0,
  );
}
