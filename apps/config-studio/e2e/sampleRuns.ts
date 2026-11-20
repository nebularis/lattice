// SPDX-License-Identifier: MPL-2.0
// The sample runs of the Playwright journeys (SVA-M3b), shared by the unit test that builds what the browser sends and by the fake service that answers it.
// The fixture, fixtures/sample-runs.json, holds for each workspace the body the browser submits to compile its mapping part and the compilation a worker
// gave for it, and for each run the sample the author gives and the frames a worker gave for it. Each side keeps what it owns current and fails when it
// is stale: sample.journey.test.ts the bodies and samples, test_config_studio_sample_runs.py the compilations and the Turtle runs' frames, and
// SampleRunsTest the XML and JSON runs' frames. Frames are never written by hand.

export const FIXTURE = "fixtures/sample-runs.json";

export interface RecordedArtefact {
  path: string;
  mediaType: string;
  group: string;
  content: string;
}

export interface RecordedWorkspace {
  id: string;
  /** What the browser submits to compile the workspace's mapping part, and the baseline and the other parts the service reads beside it. Written by the unit test. */
  compileBody: string;
  baseline: string;
  context: string;
  /** Written by the Python worker's test. */
  conforms: boolean;
  compiled: RecordedArtefact[];
}

export interface RecordedRun {
  id: string;
  workspace: string;
  /** The worker whose test writes the frames. */
  worker: "python" | "java";
  mediaType: string;
  /** The sample the author gives. Written by the unit test. */
  sample: string;
  frames: unknown[];
}

export interface Recorded {
  workspaces: RecordedWorkspace[];
  runs: RecordedRun[];
}

/** A workspace of the journeys, made from a staged sample or from files in the repository, with its mapping part as the browser holds it. */
export type WorkspaceSource = { id: string; sample: string } | { id: string; files: string[] };

export const WORKSPACES: WorkspaceSource[] = [
  { id: "policies", sample: "policies-transforms" },
  { id: "catalogue", files: ["tools/mork_rdf/tests/fixtures/catalogue-mapping.ttl"] },
];

/** Where a run's sample comes from: a file of the repository, or the example a source concept of the workspace carries. */
export interface RunSource {
  id: string;
  workspace: string;
  worker: "python" | "java";
  mediaType: string;
  from: { file: string } | { example: string };
}

export const RUNS: RunSource[] = [
  { id: "turtle", workspace: "catalogue", worker: "python", mediaType: "text/turtle", from: { file: "tools/mork_rdf/tests/fixtures/catalogue-source.ttl" } },
  { id: "xml", workspace: "policies", worker: "java", mediaType: "application/xml", from: { example: "urn:example:source/xml#Source" } },
  { id: "json", workspace: "policies", worker: "java", mediaType: "application/json", from: { example: "urn:example:source/json#Source" } },
];
