/**
 * Polls `GET /api/jobs/{jobId}` until it leaves the `queued` status (plan WA8, used by the
 * Analyse panel added in WA9).
 */
import type { JobStatus } from "./types";

export interface PollableJob {
  status: JobStatus;
}

export interface JobApi<T extends PollableJob> {
  getJob(jobId: string): Promise<T>;
}

export interface PollOptions {
  intervalMs?: number;
  timeoutMs?: number;
}

const DEFAULT_INTERVAL_MS = 500;
const DEFAULT_TIMEOUT_MS = 20000;

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Resolves with the final (non-`queued`) job, or rejects with an error named `timeout`. */
export async function pollJob<T extends PollableJob>(
  api: JobApi<T>,
  jobId: string,
  options: PollOptions = {},
): Promise<T> {
  const intervalMs = options.intervalMs ?? DEFAULT_INTERVAL_MS;
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const deadline = Date.now() + timeoutMs;

  for (;;) {
    const job = await api.getJob(jobId);
    if (job.status !== "queued") {
      return job;
    }
    const remaining = deadline - Date.now();
    if (remaining <= 0) {
      throw new Error("timeout");
    }
    await delay(Math.min(intervalMs, remaining));
  }
}
