import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { pollJob, type JobStatus } from "./poll";

const job = (status: JobStatus) => ({ status });

describe("pollJob", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("resolves once succeeded, after polling three times", async () => {
    const read = vi
      .fn<() => Promise<{ status: JobStatus }>>()
      .mockResolvedValueOnce(job("queued"))
      .mockResolvedValueOnce(job("running"))
      .mockResolvedValueOnce(job("succeeded"));

    const promise = pollJob(read, { intervalMs: 100, timeoutMs: 10000 });
    await vi.advanceTimersByTimeAsync(300);

    await expect(promise).resolves.toEqual(job("succeeded"));
    expect(read).toHaveBeenCalledTimes(3);
  });

  it("rejects with a timeout when the job never ends", async () => {
    const read = vi.fn<() => Promise<{ status: JobStatus }>>().mockResolvedValue(job("running"));

    const promise = pollJob(read, { intervalMs: 100, timeoutMs: 500 });
    const assertion = expect(promise).rejects.toThrow("timeout");
    await vi.advanceTimersByTimeAsync(600);

    await assertion;
  });

  it("resolves a failed job at once, without waiting an interval", async () => {
    const read = vi.fn<() => Promise<{ status: JobStatus }>>().mockResolvedValue(job("failed"));

    const result = await pollJob(read, { intervalMs: 100000, timeoutMs: 100000 });

    expect(result.status).toBe("failed");
    expect(read).toHaveBeenCalledTimes(1);
  });
});
