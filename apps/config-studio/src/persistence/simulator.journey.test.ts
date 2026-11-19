// SPDX-License-Identifier: MPL-2.0
// The simulator's journey (SVA-P4): the requests the browser builds for the steps of e2e/journey.ts, held against the fixture the Playwright journey's fake
// service answers them from. The fixture holds each request's body and the frames the run worker gave for it, and the worker's test, SimulatorJourneyTest,
// runs each body and fails when the frames differ, so a fixture that is current here and there is what the worker does with what the browser sends.
// To rewrite it after a change, run this test with UPDATE_JOURNEY=1, then the worker's test with -Djourney.update=true, and repeat until neither
// changes a file, at most once for each step. Frames are never written by hand.

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { Graph } from "@lattice/authoring-domain";
import { FACILITY, FIXTURE, FIXTURE_STEPS, GENERATED_STEP, ROOT, EX, type Recorded } from "../../e2e/journey";
import { assemble } from "../runs";
import { readLanding } from "./landing";
import { formSpec, formTriples, type FormValues } from "./objectForm";
import { generateObject, instancesIn } from "./objectGenerate";
import { applyDelta, buildStep, initialWorld, operationsFor, readDelta, readOutcome, type Built, type World } from "./simulator";
import { DEFAULT_TIME } from "./simulatorStore";

const file = new URL(`../../e2e/${FIXTURE}`, import.meta.url);
const profile = readFileSync(new URL("../../e2e/fixtures/compiled-profile-facility.ttl", import.meta.url), "utf-8");
const reading = readLanding(profile);
if (reading.state !== "ready") throw new Error("predates");
const facility = reading.doc.targets.find((t) => t.id === "Facility")!;
const baseline = Graph.parse(readFileSync(new URL("../../../../contracts/config-studio/samples/facility-baseline.ttl", import.meta.url), "utf-8"));
const spec = formSpec(baseline, facility.aggregate.rootShape, facility.aggregate.rootClass)!;

function form(margin: string): FormValues {
  return {
    fields: {
      [`${EX}facilityReference`]: FACILITY.facilityReference,
      [`${EX}commitment`]: FACILITY.commitment,
      [`${EX}margin`]: margin,
      [`${EX}arrangedBy`]: FACILITY.arrangedBy,
      [`${EX}borrower`]: FACILITY.borrower,
      [`${EX}lender`]: FACILITY.lender.join("\n"),
    },
    owned: { [`${EX}hasDrawdown`]: [{ id: `${ROOT}-drawdown-1`, fields: { [`${EX}drawnAmount`]: FACILITY.drawdown.amount, [`${EX}drawdownDate`]: FACILITY.drawdown.date }, owned: {} }] },
  };
}

const recorded = (): Recorded => (existsSync(file) ? (JSON.parse(readFileSync(file, "utf-8")) as Recorded) : { steps: [] });

/** The requests the journey sends, each built from the world the frames of the step before moved forward. A step whose frames are not recorded for its body ends the replay. */
function replay(known: Recorded): { bodies: string[]; ended?: string } {
  let world: World = initialWorld(facility);
  let taken = 0;
  const bodies: string[] = [];
  for (const [i, step] of FIXTURE_STEPS.entries()) {
    // The generated facility is a journey of its own, from an empty sample world.
    if (step === GENERATED_STEP) {
      world = initialWorld(facility);
      taken = 0;
    }
    const values = step === GENERATED_STEP ? generateObject(spec, ROOT, instancesIn(world)).form : form(step.margin);
    const object = formTriples(spec, values, ROOT);
    if (!("lines" in object)) throw new Error(object.problem);
    const operation = operationsFor(facility, step.write)[0];
    const built: Built = buildStep({ target: facility, operation, root: ROOT, object: object.lines, world, steps: taken, time: DEFAULT_TIME, asAnotherWriter: step.anotherWriter });
    if ("problem" in built) throw new Error(`${step.label}: ${built.problem}`);
    bodies.push(built.trig);
    const entry = known.steps[i];
    if (!entry || entry.body !== built.trig || entry.frames.length === 0) return { bodies, ended: step.label };
    const run = assemble(entry.frames);
    if (run.state !== "complete") throw new Error(`${step.label}: the frames are not a complete run`);
    const outcome = readOutcome(run.parts.find((p) => p.role === "outcome")?.text);
    const delta = readDelta(run.parts.find((p) => p.role === "delta")?.text);
    if (outcome?.outcome === "applied" && delta) {
      world = applyDelta(world, delta);
      taken++;
    }
  }
  return { bodies };
}

describe("the simulator journey's requests", () => {
  it("are the bodies of the fixture the fake service answers from, each with the frames the run worker gave for it", () => {
    const known = recorded();
    const { bodies, ended } = replay(known);
    if (process.env.UPDATE_JOURNEY) {
      const next: Recorded = {
        steps: bodies.map((body, i) => ({ label: FIXTURE_STEPS[i].label, outcome: FIXTURE_STEPS[i].outcome, body, frames: known.steps[i]?.body === body ? known.steps[i].frames : [] })),
      };
      writeFileSync(file, `${JSON.stringify(next, null, 2)}\n`);
      return;
    }
    expect(known.steps.map((s) => s.label)).toEqual(FIXTURE_STEPS.map((s) => s.label));
    expect(ended, `the fixture has no current frames for the step "${ended}". Run SimulatorJourneyTest with -Djourney.update=true`).toBeUndefined();
    expect(known.steps.map((s) => s.body)).toEqual(bodies);
    expect(known.steps.map((s) => s.outcome)).toEqual(FIXTURE_STEPS.map((s) => s.outcome));
  });

  it("send the stored position as expected and an earlier one as another writer, and mint from the step count", () => {
    const known = recorded();
    if (known.steps.length < FIXTURE_STEPS.length) return;
    const parameter = (body: string, name: string) => new RegExp(`cst:parameterName "${name}" ; cst:parameterValue "([^"]*)"`).exec(body)?.[1];
    expect(parameter(known.steps[0].body, "txnId")).toBe("urn:txn:facility-1-1");
    expect(parameter(known.steps[1].body, "expectedSeq")).toBe("1");
    expect(parameter(known.steps[1].body, "newRev")).toBe("urn:rev:facility-1/2");
    expect(parameter(known.steps[2].body, "expectedSeq")).toBe("1");
    expect(parameter(known.steps[2].body, "txnId")).toBe("urn:txn:facility-1-3");
    // The generated facility is the first step of a world of its own.
    expect(parameter(known.steps[3].body, "txnId")).toBe("urn:txn:facility-1-1");
  });
});
