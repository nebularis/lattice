// SPDX-License-Identifier: MPL-2.0
import { describe, expect, it } from "vitest";
import { Graph } from "@lattice/authoring-domain";
import { heldImportsKey, validationSummary, type Validation } from "./state";

describe("heldImportsKey", () => {
  it("is empty for no imports and for a summary not yet read", () => {
    expect(heldImportsKey([])).toBe("");
    expect(heldImportsKey(undefined)).toBe("");
  });

  it("changes when an import is held or released", () => {
    const one = heldImportsKey([{ digest: "a" }]);
    expect(heldImportsKey([{ digest: "a" }, { digest: "b" }])).not.toBe(one);
    expect(heldImportsKey([])).not.toBe(one);
  });

  it("is the same for any order of the imports, and does not read what else the summary holds", () => {
    expect(heldImportsKey([{ digest: "b" }, { digest: "a" }])).toBe(heldImportsKey([{ digest: "a" }, { digest: "b" }]));
    expect(heldImportsKey([{ digest: "a", label: "x" } as { digest: string }])).toBe(heldImportsKey([{ digest: "a", label: "y" } as { digest: string }]));
  });
});

describe("validationSummary", () => {
  const v = (state: Validation["state"], message?: string): Validation => ({ state, issues: [], message });
  const config = (validation: Validation) => ({ saved: Graph.empty(), current: Graph.empty(), revision: "1", past: [], future: [], validation, saving: false });

  it("reports nothing running and nothing failed when every validation is done or idle", () => {
    expect(validationSummary({ configs: { persistence: config(v("done")) }, baselineValidation: v("done") })).toEqual({ running: false, failed: undefined });
    expect(validationSummary({ configs: {}, baselineValidation: undefined })).toEqual({ running: false, failed: undefined });
  });

  it("takes the baseline's validation into account as a part's", () => {
    expect(validationSummary({ configs: { persistence: config(v("done")) }, baselineValidation: v("running") }).running).toBe(true);
    expect(validationSummary({ configs: { persistence: config(v("running")) }, baselineValidation: v("done") }).running).toBe(true);
    expect(validationSummary({ configs: { persistence: config(v("done")) }, baselineValidation: v("failed", "no worker") }).failed?.message).toBe("no worker");
    expect(validationSummary({ configs: { persistence: config(v("failed", "part")) }, baselineValidation: v("failed", "baseline") }).failed?.message).toBe("part");
  });
});
