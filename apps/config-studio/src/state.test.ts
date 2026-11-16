// SPDX-License-Identifier: MPL-2.0
import { describe, expect, it } from "vitest";
import { heldImportsKey } from "./state";

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
