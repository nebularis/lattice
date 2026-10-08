import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, HttpApiClient } from "./client";

describe("HttpApiClient", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("sends a PUT with the right URL, method, headers and body", async () => {
    const calls: Array<{ url: string; init: RequestInit }> = [];
    const fetchImpl = vi.fn(async (url: string, init: RequestInit) => {
      calls.push({ url, init });
      return new Response(JSON.stringify({ documentId: "doc-1" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });

    const client = new HttpApiClient("http://127.0.0.1:8088", fetchImpl as unknown as typeof fetch);
    await client.submitSnapshot("00000001-0000-4000-8000-000000000000", {
      baseRevision: null,
      snapshot: {
        schemaVersion: "0.1.0",
        documentId: "00000001-0000-4000-8000-000000000000",
        templateId: "facility-agreement",
        title: "t",
        sections: [],
        variables: [],
        unmarked: [],
      },
    });

    expect(calls).toHaveLength(1);
    expect(calls[0].url).toBe("http://127.0.0.1:8088/api/documents/00000001-0000-4000-8000-000000000000/snapshot");
    expect(calls[0].init.method).toBe("PUT");
    expect((calls[0].init.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
    expect(JSON.parse(calls[0].init.body as string).baseRevision).toBeNull();
  });

  it("rejects with an ApiError carrying the status on a non-2xx answer", async () => {
    const fetchImpl = vi.fn(async () =>
      new Response(JSON.stringify({ error: "the latest revision is 3", details: [] }), {
        status: 409,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const client = new HttpApiClient("http://127.0.0.1:8088", fetchImpl as unknown as typeof fetch);

    await expect(
      client.submitSnapshot("00000001-0000-4000-8000-000000000000", {
        baseRevision: 1,
        snapshot: {
          schemaVersion: "0.1.0",
          documentId: "00000001-0000-4000-8000-000000000000",
          templateId: "facility-agreement",
          title: "t",
          sections: [],
          variables: [],
          unmarked: [],
        },
      }),
    ).rejects.toMatchObject({ status: 409, message: "the latest revision is 3" } satisfies Partial<ApiError>);
  });

  it("rejects with a timeout when the fetch never settles", async () => {
    const fetchImpl = vi.fn(() => new Promise<Response>(() => {}));
    const client = new HttpApiClient("http://127.0.0.1:8088", fetchImpl as unknown as typeof fetch, 1000);

    const promise = client.health();
    const assertion = expect(promise).rejects.toThrow("timeout");
    await vi.advanceTimersByTimeAsync(1100);

    await assertion;
  });
});
