import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { pollJob } from "./poll";
import type { JobView } from "./types";

function job(status: JobView["status"]): JobView {
  return {
    jobId: "00000001-0000-4000-8000-000000000099",
    documentId: "00000001-0000-4000-8000-000000000000",
    revision: 1,
    status,
    error: null,
  };
}

describe("pollJob", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("resolves once completed, after polling three times", async () => {
    const getJob = vi
      .fn<(jobId: string) => Promise<JobView>>()
      .mockResolvedValueOnce(job("queued"))
      .mockResolvedValueOnce(job("queued"))
      .mockResolvedValueOnce(job("completed"));

    const promise = pollJob({ getJob }, "job-1", { intervalMs: 100, timeoutMs: 10000 });
    await vi.advanceTimersByTimeAsync(300);

    await expect(promise).resolves.toEqual(job("completed"));
    expect(getJob).toHaveBeenCalledTimes(3);
  });

  it("rejects with a timeout when the job never leaves queued", async () => {
    const getJob = vi.fn<(jobId: string) => Promise<JobView>>().mockResolvedValue(job("queued"));

    const promise = pollJob({ getJob }, "job-1", { intervalMs: 100, timeoutMs: 500 });
    const assertion = expect(promise).rejects.toThrow("timeout");
    await vi.advanceTimersByTimeAsync(600);

    await assertion;
  });

  it("resolves a failed job at once, without waiting an interval", async () => {
    const getJob = vi.fn<(jobId: string) => Promise<JobView>>().mockResolvedValue(job("failed"));

    const result = await pollJob({ getJob }, "job-1", { intervalMs: 100000, timeoutMs: 100000 });

    expect(result.status).toBe("failed");
    expect(getJob).toHaveBeenCalledTimes(1);
  });
});
