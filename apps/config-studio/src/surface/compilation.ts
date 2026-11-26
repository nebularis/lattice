// SPDX-License-Identifier: MPL-2.0
// The latest finished compilation of the surface part, which the canvas reads the lowered schemes from (SVA-Q62), as the persistence canvas reads the
// latest compilation of its part (persistence/compilation.ts). A compilation that holds no `projections` group is a compilation of a configuration with no
// projection, or one that predates the group, and the canvas says which projections it has no scheme for.

import { api, awaitJob, jobId } from "../api";
import { finished, type Job } from "../rdf/report";
import { readProjections, type Projections } from "./scheme";

export type SurfaceLoad =
  | { state: "loading" }
  | { state: "none" }
  | { state: "refused"; job: Job }
  | { state: "ready"; job: Job; projections: Projections }
  | { state: "error"; message: string };

/** The latest finished surface compilation of the workspace, newest first by when it was submitted. */
export function latestSurface(jobs: Job[]): Job | undefined {
  return jobs
    .filter((j) => j.kind === "Compile" && j.target === "Surface" && finished(j))
    .sort((a, b) => (b.submittedAt ?? "").localeCompare(a.submittedAt ?? "") || b.iri.localeCompare(a.iri))[0];
}

export async function readSurface(workspace: string): Promise<SurfaceLoad> {
  const row = latestSurface(await api.compileJobs(workspace));
  if (!row) return { state: "none" };
  const job = await awaitJob(jobId(row.iri));
  if (job.status !== "Succeeded" || !job.conforms) return { state: "refused", job };
  return { state: "ready", job, projections: readProjections(job) ?? { schemes: [] } };
}
