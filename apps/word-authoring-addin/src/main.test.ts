import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

describe("main.tsx: the WordApi requirement check (S9-12)", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.resetModules();
  });

  afterEach(() => {
    delete (globalThis as { Office?: unknown }).Office;
  });

  it("renders the unsupported message and no App when WordApi 1.4 is not supported", async () => {
    (globalThis as { Office?: unknown }).Office = {
      onReady: vi.fn(),
      context: { requirements: { isSetSupported: () => false } },
    };

    const { render } = await import("./main");
    const container = document.createElement("div");
    document.body.appendChild(container);

    render(container);
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(container.textContent).toContain("requires a newer version of Word");
    expect(container.querySelector(".tab-bar")).toBeNull();
  });

  it("reads the WordApi 1.4 requirement directly", async () => {
    (globalThis as { Office?: unknown }).Office = {
      onReady: vi.fn(),
      context: { requirements: { isSetSupported: (name: string, version: string) => name === "WordApi" && version === "1.4" } },
    };

    const { isWordApiSupported } = await import("./main");

    expect(isWordApiSupported()).toBe(true);
  });
});
