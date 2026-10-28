/**
 * Polls a studio job until it has ended (CS12d, used by the Analyse panel).
 */
export type JobStatus = "queued" | "running" | "succeeded" | "failed";

export interface PollableJob {
  status: JobStatus;
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

/** Resolves with the job once it has succeeded or failed, or rejects with an error named `timeout`. */
export async function pollJob<T extends PollableJob>(read: () => Promise<T>, options: PollOptions = {}): Promise<T> {
  const intervalMs = options.intervalMs ?? DEFAULT_INTERVAL_MS;
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const deadline = Date.now() + timeoutMs;

  for (;;) {
    const job = await read();
    if (job.status === "succeeded" || job.status === "failed") {
      return job;
    }
    const remaining = deadline - Date.now();
    if (remaining <= 0) {
      throw new Error("timeout");
    }
    await delay(Math.min(intervalMs, remaining));
  }
}
