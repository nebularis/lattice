// SPDX-License-Identifier: MPL-2.0
import { describe, expect, it } from "vitest";
import { Parser } from "n3";
import { Graph } from "@lattice/authoring-domain";
import { PATCH_ADD, PATCH_DEL, patchOf, patchTrig } from "./patch";

const P = "@prefix ex: <https://example.org/> .\n";

describe("patchOf", () => {
  it("gives what a save added and removed, and nothing it kept", () => {
    const saved = Graph.parse(P + 'ex:a ex:q "old" . ex:b ex:q "kept" .');
    const current = Graph.parse(P + 'ex:a ex:q "new" . ex:b ex:q "kept" .');
    const patch = patchOf(saved, current)!;
    expect(patch.add.map((q) => q.object.value)).toEqual(["new"]);
    expect(patch.del.map((q) => q.object.value)).toEqual(["old"]);
  });

  it("declines a change that holds a blank node, which is saved whole", () => {
    expect(patchOf(Graph.parse(P + "ex:a ex:q ex:b ."), Graph.parse(P + "ex:a ex:q [] ."))).toBeUndefined();
  });

  it("names both graphs in its TriG, an empty one too", () => {
    const trig = patchTrig(patchOf(Graph.parse(P + "ex:a ex:q ex:b ."), Graph.parse(P + "ex:a ex:q ex:b . ex:a ex:r ex:c ."))!);
    expect(trig).toContain(`<${PATCH_ADD}>`);
    expect(trig).toContain(`<${PATCH_DEL}>`);
    const quads = new Parser({ format: "application/trig" }).parse(trig);
    expect(quads.map((q) => q.graph.value)).toEqual([PATCH_ADD]);
  });
});
