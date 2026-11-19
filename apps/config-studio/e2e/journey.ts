// SPDX-License-Identifier: MPL-2.0
// The simulator's journey over the facility sample (SVA-P4), shared by the unit test that builds its requests and by the Playwright journey that types
// it, so that both mean the same steps. The frames the fake service gives for each step are in fixtures/simulator-facility-journey.json, which the run
// worker's own test writes from what the worker does with the steps (SimulatorJourneyTest).

export const ROOT = "https://example.org/lending#facility-1";
export const EX = "https://example.org/lending#";

/** What the author types into the form to create the facility. */
export const FACILITY = {
  facilityReference: "FAC-2026-001",
  commitment: "120000000.0",
  margin: "3.25",
  arrangedBy: `${EX}branch-london`,
  borrower: `${EX}acme-foods`,
  lender: [`${EX}lender-north`, `${EX}lender-south`],
  drawdown: { amount: "40000000.0", date: "2026-03-15" },
};

export interface JourneyStep {
  label: string;
  /** The margin the form holds when the step runs. */
  margin: string;
  /** Whether the step is sent as another writer. */
  anotherWriter: boolean;
  /** The write the pane runs. */
  write: "create" | "replace";
  /** The outcome the worker is expected to give, and which the worker's test checks. */
  outcome: "applied" | "lostRace";
}

/** Create the facility, change its margin, and lose a race as another writer. The author then steps back from the change. */
export const STEPS: JourneyStep[] = [
  { label: "create the facility", margin: "3.25", anotherWriter: false, write: "create", outcome: "applied" },
  { label: "change the margin", margin: "3.5", anotherWriter: false, write: "replace", outcome: "applied" },
  { label: "change the margin as another writer", margin: "3.75", anotherWriter: true, write: "replace", outcome: "lostRace" },
];

/**
 * The generated facility (SVA-P5), a journey of its own that starts from an empty sample world, so that the root is the same one. The author presses
 * Generate from the shape and then Run, and nothing is typed. The facility sample's boundary shape states no minimum, so the object is the root alone.
 */
export const GENERATED_STEP: JourneyStep = { label: "create the generated facility", margin: "", anotherWriter: false, write: "create", outcome: "applied" };

/** Every step the fixture holds, in the order of its steps. */
export const FIXTURE_STEPS: JourneyStep[] = [...STEPS, GENERATED_STEP];

export const FIXTURE = "fixtures/simulator-facility-journey.json";

export interface Recorded {
  steps: { label: string; outcome: string; body: string; frames: unknown[] }[];
}
