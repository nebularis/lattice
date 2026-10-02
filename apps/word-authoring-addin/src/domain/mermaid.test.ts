import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { toMermaid } from "./mermaid";
import type { Analysis } from "./types";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "../../../..");
const GOLDEN = path.join(REPO_ROOT, "workers/tests/fixtures/wording_le/facility-agreement.analysis.json");

describe("toMermaid", () => {
  it("renders the facility graph view deterministically, with n0... node ids", () => {
    const analysis = JSON.parse(readFileSync(GOLDEN, "utf-8")) as Analysis;

    const first = toMermaid(analysis.graphView);
    const second = toMermaid(analysis.graphView);

    expect(first).toBe(second);
    expect(first.split("\n")[0]).toBe("flowchart LR");
    expect(first).toContain("n0");
    expect(first).toContain(`n${analysis.graphView.nodes.length - 1}`);
  });

  it("escapes a double quote in a label as #quot;, not a literal quote", () => {
    const output = toMermaid({
      nodes: [{ id: "a", label: 'say "hi"', kind: "element" }],
      edges: [],
    });

    expect(output).toContain("#quot;");
    expect(output).not.toContain('"hi"');
  });

  it("throws when an edge references a node outside the view", () => {
    expect(() =>
      toMermaid({ nodes: [{ id: "a", label: "A", kind: "element" }], edges: [{ from: "a", to: "missing", label: "x" }] }),
    ).toThrow();
  });
});
