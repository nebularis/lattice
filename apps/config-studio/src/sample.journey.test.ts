// SPDX-License-Identifier: MPL-2.0
// The sample runs of the journeys (SVA-M3b): what the browser submits to compile a workspace's mapping part and the samples the author gives, held against the
// fixture the Playwright journeys' fake service answers from. The fixture also holds each compilation and each run's frames, which the workers' tests
// write and keep current, so a fixture that is current here and there is what the workers do with what the browser sends. To rewrite it after a change, run
// this test with UPDATE_SAMPLE_RUNS=1, then test_config_studio_sample_runs.py with LATTICE_WRITE_SAMPLE_RUNS=1, then SampleRunsTest with
// -Dsamples.update=true. Frames are never written by hand.

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { Graph } from "@lattice/authoring-domain";
import { FIXTURE, RUNS, WORKSPACES, type Recorded, type RecordedRun, type RecordedWorkspace } from "../e2e/sampleRuns";
import { exampleSources } from "./rdf/mapping";
import { CONFIG_PARTS, split } from "./rdf/split";
import { assemble } from "./runs";

const assets = process.env.LATTICE_STUDIO_ASSETS ?? join(import.meta.dirname, "../../../.build/config-studio");
const root = join(import.meta.dirname, "../../..");
const file = new URL(`../e2e/${FIXTURE}`, import.meta.url);
const recorded = (): Recorded => (existsSync(file) ? (JSON.parse(readFileSync(file, "utf-8")) as Recorded) : { workspaces: [], runs: [] });

/** What a workspace holds once it is saved and read again, which is what a compilation of its mapping part is sent. */
function partsOf(workspace: (typeof WORKSPACES)[number]): { mapping: Graph; baseline: string; context: string } {
  const graph =
    "sample" in workspace
      ? Graph.parse(readFileSync(join(assets, `samples/${workspace.sample}.ttl`), "utf-8"))
      : workspace.files.map((f) => Graph.parse(readFileSync(join(root, f), "utf-8"))).reduce((a, b) => a.merge(b));
  const parts = split(graph);
  const again = (g: Graph) => Graph.parse(g.toTurtle());
  const others = CONFIG_PARTS.filter((p) => p !== "mapping").reduce((all, p) => all.merge(again(parts[p])), Graph.empty());
  return { mapping: again(parts.mapping), baseline: again(parts.baseline).toTurtle(), context: others.toTurtle() };
}

function built(): { workspaces: { id: string; compileBody: string; baseline: string; context: string }[]; runs: { id: string; sample: string }[] } {
  const parts = new Map(WORKSPACES.map((w) => [w.id, partsOf(w)]));
  const mapping = new Map([...parts].map(([id, p]) => [id, p.mapping]));
  return {
    workspaces: WORKSPACES.map((w) => ({ id: w.id, compileBody: mapping.get(w.id)!.toTurtle(), baseline: parts.get(w.id)!.baseline, context: parts.get(w.id)!.context })),
    runs: RUNS.map((r) => {
      if ("file" in r.from) return { id: r.id, sample: readFileSync(join(root, r.from.file), "utf-8") };
      const example = r.from.example;
      const found = exampleSources(mapping.get(r.workspace)!).find((e) => e.scheme === example);
      if (!found) throw new Error(`the workspace ${r.workspace} carries no example for ${example}`);
      return { id: r.id, sample: found.text };
    }),
  };
}

describe("the sample runs of the journeys", () => {
  it("are the bodies and samples of the fixture the fake service answers from", () => {
    const now = built();
    const known = recorded();
    if (process.env.UPDATE_SAMPLE_RUNS) {
      const workspaces = now.workspaces.map((w): RecordedWorkspace => {
        const old = known.workspaces.find((k) => k.id === w.id);
        // A compilation given for other input is not carried over.
        const same = old?.compileBody === w.compileBody && old.baseline === w.baseline && old.context === w.context;
        return { ...w, conforms: same ? old.conforms : true, compiled: same ? old.compiled : [] };
      });
      const next: Recorded = {
        workspaces,
        runs: now.runs.map((r): RecordedRun => {
          const def = RUNS.find((d) => d.id === r.id)!;
          const old = known.runs.find((k) => k.id === r.id);
          // Frames given for another sample or another compilation are not carried over.
          const same = old?.sample === r.sample && workspaces.find((w) => w.id === def.workspace)!.compiled.length > 0;
          return { id: r.id, workspace: def.workspace, worker: def.worker, mediaType: def.mediaType, sample: r.sample, frames: same ? old!.frames : [] };
        }),
      };
      writeFileSync(file, `${JSON.stringify(next, null, 2)}\n`);
      return;
    }
    const stale = "Run this test with UPDATE_SAMPLE_RUNS=1, then the Python worker's test with LATTICE_WRITE_SAMPLE_RUNS=1 and SampleRunsTest with -Dsamples.update=true";
    expect(known.workspaces.map((w) => [w.id, w.compileBody, w.baseline, w.context]), stale).toEqual(now.workspaces.map((w) => [w.id, w.compileBody, w.baseline, w.context]));
    expect(known.runs.map((r) => [r.id, r.workspace, r.worker, r.mediaType, r.sample]), stale).toEqual(
      RUNS.map((d) => [d.id, d.workspace, d.worker, d.mediaType, now.runs.find((r) => r.id === d.id)!.sample]),
    );
  });

  it("each hold the frames of a whole run and the compilation the worker gave, and the report of each names its engine", () => {
    const known = recorded();
    for (const w of known.workspaces) expect(w.compiled.length, `the compilation of ${w.id}`).toBeGreaterThan(0);
    for (const r of known.runs) {
      const run = assemble(r.frames as never[]);
      expect(run.state, `the frames of ${r.id}`).toBe("complete");
      if (run.state !== "complete") continue;
      expect(run.status).toBe("succeeded");
      const report = run.parts.find((p) => p.role === "report");
      expect(report?.text, `the report of ${r.id}`).toMatch(/cst:engine "[^"]+"/);
      expect(run.parts.filter((p) => p.role === "artefact").length, `the artefacts of ${r.id}`).toBeGreaterThan(0);
    }
  });
});
