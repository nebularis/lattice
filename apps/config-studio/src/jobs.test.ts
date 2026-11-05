// SPDX-License-Identifier: MPL-2.0
import { afterEach, describe, expect, it, vi } from "vitest";
import { awaitJob } from "./api";

const RUNNING = `@prefix cst: <https://www.nebularis.org/neuro-semantic/lattice/config-studio#> .
<urn:lattice:studio:job:j1> a cst:Job ; cst:kind cst:Propose ; cst:target cst:LanguageModelProposer ; cst:status cst:Running .
`;

function serve(body: () => string) {
  const fetchMock = vi.fn(async () => new Response(body(), { status: 200, headers: { "Content-Type": "text/turtle", ETag: '"1"' } }));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => vi.unstubAllGlobals());

describe("awaitJob", () => {
  it("ends with an AbortError as soon as its signal aborts, and reads the job no more", async () => {
    const fetchMock = serve(() => RUNNING);
    const controller = new AbortController();
    const waiting = awaitJob("j1", controller.signal);
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const reads = fetchMock.mock.calls.length;
    const started = Date.now();
    controller.abort();
    await expect(waiting).rejects.toMatchObject({ name: "AbortError" });
    expect(Date.now() - started).toBeLessThan(300);
    await new Promise((r) => setTimeout(r, 400));
    expect(fetchMock.mock.calls.length).toBe(reads);
  });

  it("ends at once for a signal that has already aborted", async () => {
    serve(() => RUNNING);
    const controller = new AbortController();
    controller.abort();
    await expect(awaitJob("j1", controller.signal)).rejects.toMatchObject({ name: "AbortError" });
  });

  it("returns the job once it has finished", async () => {
    let reads = 0;
    serve(() => (++reads < 2 ? RUNNING : RUNNING.replace("cst:Running", "cst:Succeeded")));
    const job = await awaitJob("j1", new AbortController().signal);
    expect(job.status).toBe("Succeeded");
    expect(job.target).toBe("LanguageModelProposer");
  });
});
