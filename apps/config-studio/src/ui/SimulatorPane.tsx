// SPDX-License-Identifier: MPL-2.0
// The persistence simulator's pane (SVA-P4, sketch section 8.2). The controls are on the left and the four displays on the right, in the run pane's
// shell (SVA-R4). The author gives an object and an operation, and nothing runs until Run is pressed. The browser builds the step from the sample
// world, the object and the operation's declared parameters, the worker runs it, and the world moves forward only when the outcome is applied. The
// delta lights the landing places it wrote on the canvas beside the pane.

import { useEffect, useMemo, useRef, useState } from "react";
import { Play, RotateCcw, Undo2, Plus, Trash2 } from "lucide-react";
import { jobId } from "../api";
import { readFiles, Spinner } from "./kit";
import { OutputExplorer } from "./OutputExplorer";
import { RunPane, useRunController } from "./RunPane";
import { useStudio } from "./Workspace";
import { generateObject, instancesIn } from "../persistence/objectGenerate";
import { read, useCompilationEpoch, type Load } from "../persistence/compilation";
import type { LandingPlaces, LandingTarget } from "../persistence/landing";
import { localName, targetLabel } from "../persistence/landing";
import {
  EMPTY_FORM, formSpec, formTriples, formValues, newMemberId, turtleTriples,
  type FieldSpec, type FormSpec, type FormValues, type OwnedSpec, type OwnedValues, type Triples,
} from "../persistence/objectForm";
import {
  REQUEST_LIMIT_BYTES, TIME, WRITES, aggregateLines, applyDelta, buildStep, graphsOf, initialWorld, litOf, operationsFor, placesByIri, positionOf, readDelta, readOutcome, worldSize, worldTrig,
  type Delta, type StepRecord, type StepOutcome, type WriteKind,
} from "../persistence/simulator";
import { draftOf, setSim, stepBack, useSim, type Draft } from "../persistence/simulatorStore";
import type { RunPart } from "../runs";

const kib = (n: number) => (n < 1024 ? `${n} bytes` : n < 1024 * 1024 ? `${(n / 1024).toFixed(1)} KiB` : `${(n / 1024 / 1024).toFixed(2)} MiB`);

/** The root a new object starts with, the class's name in lower case after the class's own namespace, and a number. */
function defaultRoot(cls: string): string {
  const cut = Math.max(cls.lastIndexOf("#"), cls.lastIndexOf("/"));
  const name = cls.slice(cut + 1).replace(/([a-z0-9])([A-Z])/g, "$1-$2").toLowerCase();
  return `${cls.slice(0, cut + 1)}${name}-1`;
}

// --- the object form ------------------------------------------------------------------------------------------------------------

function FieldInput({ field, value, onChange }: { field: FieldSpec; value: string; onChange: (value: string) => void }) {
  const hint = field.kind === "iri" ? `IRI${field.cls ? ` of a ${localName(field.cls)}` : ""}, one to a line` : field.datatype ? localName(field.datatype) : "text";
  return (
    <label className="sim-field">
      <span className="small">{field.label}</span>
      <textarea className="input mono" rows={Math.max(1, value.split("\n").length)} value={value} aria-label={field.label} placeholder={hint} onChange={(e) => onChange(e.target.value)} />
    </label>
  );
}

function OwnedForm({ specs, values, parent, onChange }: { specs: readonly OwnedSpec[]; values: Record<string, OwnedValues[]>; parent: string; onChange: (next: Record<string, OwnedValues[]>) => void }) {
  return (
    <>
      {specs.map((spec) => {
        const members = values[spec.property] ?? [];
        const set = (next: OwnedValues[]) => onChange({ ...values, [spec.property]: next });
        return (
          <fieldset key={spec.property} className="sim-owned" aria-label={`Owned ${spec.member}`}>
            <legend className="small">{spec.member}, owned</legend>
            {members.map((member, i) => (
              <div key={i} className="sim-member">
                <label className="sim-field">
                  <span className="small">identifier</span>
                  <input className="input mono" value={member.id} aria-label={`${spec.member} ${i + 1} identifier`} onChange={(e) => set(members.map((m, j) => (j === i ? { ...m, id: e.target.value } : m)))} />
                </label>
                {spec.fields.map((f) => (
                  <FieldInput key={f.path} field={f} value={member.fields[f.path] ?? ""} onChange={(v) => set(members.map((m, j) => (j === i ? { ...m, fields: { ...m.fields, [f.path]: v } } : m)))} />
                ))}
                <OwnedForm specs={spec.owned} values={member.owned} parent={member.id} onChange={(next) => set(members.map((m, j) => (j === i ? { ...m, owned: next } : m)))} />
                <button className="btn sm ghost" onClick={() => set(members.filter((_, j) => j !== i))}>
                  <Trash2 size={12} /> Remove this {spec.member}
                </button>
              </div>
            ))}
            <button className="btn sm" onClick={() => set([...members, { id: newMemberId(parent, spec, members), fields: {}, owned: {} }])}>
              <Plus size={12} /> Add a {spec.member}
            </button>
          </fieldset>
        );
      })}
    </>
  );
}

// --- the displays ---------------------------------------------------------------------------------------------------------------

interface CheckReport {
  operation?: string;
  template?: string;
  kind?: string;
  note?: string;
  checks: { name: string; verdict: string; reasons: { code?: string; where?: string; reason?: string }[] }[];
}

function readChecks(text: string | undefined): CheckReport | undefined {
  if (text === undefined) return undefined;
  try {
    const o = JSON.parse(text) as Record<string, unknown>;
    if (!Array.isArray(o.checks)) return undefined;
    return {
      operation: typeof o.operation === "string" ? o.operation : undefined,
      template: typeof o.template === "string" ? o.template : undefined,
      kind: typeof o.kind === "string" ? o.kind : undefined,
      note: typeof o.note === "string" ? o.note : undefined,
      checks: o.checks.flatMap((c) => {
        if (typeof c !== "object" || c === null) return [];
        const e = c as Record<string, unknown>;
        return [{ name: String(e.name ?? ""), verdict: String(e.verdict ?? ""), reasons: Array.isArray(e.reasons) ? (e.reasons as { code?: string; where?: string; reason?: string }[]) : [] }];
      }),
    };
  } catch {
    return undefined;
  }
}

const OUTCOME_WORDS: Record<string, string> = { applied: "Applied", lostRace: "Lost race", refused: "Refused" };

function Raw({ part }: { part: RunPart }) {
  return (
    <details className="sim-raw">
      <summary className="small muted">The part as received, {part.mediaType}</summary>
      <OutputExplorer part={part} />
    </details>
  );
}

function ChecksDisplay({ part }: { part: RunPart }) {
  const report = readChecks(part.text);
  if (!report) return <OutputExplorer part={part} />;
  return (
    <div className="sim-checks">
      {report.operation && (
        <p className="small">
          {report.operation}
          {report.template ? <span className="muted"> by {report.template}</span> : null}
          {report.kind ? <span className="muted">, {report.kind}</span> : null}
        </p>
      )}
      <ul className="sim-list">
        {report.checks.map((c) => (
          <li key={c.name}>
            <span className={`chip verdict ${c.verdict}`}>{c.verdict}</span> <strong>{c.name}</strong>
            {c.reasons.map((r, i) => (
              <div key={i} className="small sim-reason">
                <span className="mono">{r.code}</span> {r.where ? <span className="muted">at {r.where}. </span> : null}
                {r.reason}
              </div>
            ))}
          </li>
        ))}
      </ul>
      {report.note && <p className="small muted">{report.note}</p>}
      <Raw part={part} />
    </div>
  );
}

function Lines({ sign, lines }: { sign: "+" | "-"; lines: string[] }) {
  if (lines.length === 0) return null;
  return (
    <pre className={`run-part-text sim-lines ${sign === "+" ? "added" : "removed"}`} aria-label={sign === "+" ? "Added" : "Removed"}>
      {lines.map((l) => `${sign} ${l}`).join("\n")}
    </pre>
  );
}

function DeltaDisplay({ part, doc }: { part: RunPart; doc?: LandingPlaces }) {
  const delta = readDelta(part.text);
  const index = useMemo(() => (doc ? placesByIri(doc) : undefined), [doc]);
  if (!delta) return <OutputExplorer part={part} />;
  const empty = delta.places.length === 0 && delta.unplaced.length === 0;
  return (
    <div className="sim-delta">
      {empty && <p className="small muted">The step changed no graph.</p>}
      {delta.places.map((p) => {
        const known = index?.get(p.place);
        return (
          <section key={p.place} className="sim-place" aria-label={`Landing place ${known?.place.label ?? p.place}`}>
            <div className="small">
              <strong>{known?.place.label ?? p.place}</strong> <span className="chip persist">{p.role || "place"}</span>
            </div>
            {p.graphs.map((g) => (
              <div key={g.graph ?? ""}>
                <div className="mono small sim-graph">{g.graph ?? "the default graph"}</div>
                <Lines sign="+" lines={g.added} />
                <Lines sign="-" lines={g.removed} />
              </div>
            ))}
          </section>
        );
      })}
      {delta.unplaced.length > 0 && (
        <section className="sim-place unplaced" aria-label="Graphs no landing place states">
          <div className="small">
            <strong>No landing place states these graphs</strong>
          </div>
          {delta.unplaced.map((g) => (
            <div key={g.graph ?? ""}>
              <div className="mono small sim-graph">{g.graph ?? "the default graph"}</div>
              <Lines sign="+" lines={g.added} />
              <Lines sign="-" lines={g.removed} />
            </div>
          ))}
        </section>
      )}
      <Raw part={part} />
    </div>
  );
}

function OutcomeDisplay({ part }: { part: RunPart }) {
  const outcome: StepOutcome | undefined = readOutcome(part.text);
  if (!outcome) return <OutputExplorer part={part} />;
  return (
    <div className="sim-outcome">
      <p>
        <span className={`chip outcome ${outcome.outcome}`}>{OUTCOME_WORDS[outcome.outcome] ?? outcome.outcome}</span> <strong>{outcome.classification}</strong>
      </p>
      <p className="small">{outcome.reason}</p>
      <dl className="small sim-facts">
        {outcome.revision && (
          <>
            <dt>Revision</dt>
            <dd className="mono">{outcome.revision}</dd>
          </>
        )}
        <dt>Engine</dt>
        <dd>{outcome.engine ?? "none, nothing was evaluated"}</dd>
      </dl>
      <Raw part={part} />
    </div>
  );
}

const SECTIONS: { role: string; title: string }[] = [
  { role: "check", title: "The checks" },
  { role: "request", title: "The request" },
  { role: "delta", title: "The delta" },
  { role: "outcome", title: "The outcome" },
];

function Displays({ parts, doc }: { parts: RunPart[]; doc?: LandingPlaces }) {
  return (
    <div className="run-parts sim-displays" role="list" aria-label="Simulator displays">
      {SECTIONS.map(({ role, title }) => {
        const part = parts.find((p) => p.role === role);
        return (
          <div role="listitem" key={role}>
            <section className="run-part" aria-label={title}>
              <div className="run-part-head">
                <strong>{title}</strong>
                {part && <div className="small muted">{part.mediaType}</div>}
              </div>
              {part ? role === "check" ? <ChecksDisplay part={part} /> : role === "delta" ? <DeltaDisplay part={part} doc={doc} /> : role === "outcome" ? <OutcomeDisplay part={part} /> : <OutputExplorer part={part} /> : <p className="small muted sim-none">Nothing yet.</p>}
            </section>
          </div>
        );
      })}
    </div>
  );
}

// --- the pane -------------------------------------------------------------------------------------------------------------------

/** The dock's Simulator tab for the persistence view. */
export function SimulatorPane() {
  const studio = useStudio();
  const workspace = studio.id;
  const sim = useSim(workspace);
  const { controller, state } = useRunController();
  const compiledElsewhere = useCompilationEpoch();
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [refresh, setRefresh] = useState(0);
  const baselineGraph = studio.model.state.baseline?.graph;

  useEffect(() => {
    let live = true;
    read(workspace).then(
      (next) => live && setLoad(next),
      (e: unknown) => live && setLoad({ state: "error", message: e instanceof Error ? e.message : String(e) }),
    );
    return () => {
      live = false;
    };
  }, [workspace, refresh, compiledElsewhere]);

  const doc = load.state === "ready" ? load.doc : undefined;
  const targets = useMemo(() => (doc?.targets ?? []).filter((t) => t.operations.some((o) => WRITES.some((w) => operationsFor(t, w.write).includes(o)))), [doc]);
  const target: LandingTarget | undefined = targets.find((t) => t.id === sim.target) ?? targets[0];
  const world = sim.world ?? initialWorld(target);
  // The world starts when a target first gives it a dataset, and is the tab's from then on.
  useEffect(() => {
    if (!sim.world && target) setSim(workspace, { world: initialWorld(target) });
  }, [sim.world, target, workspace]);

  const available = target ? WRITES.filter((w) => operationsFor(target, w.write).length > 0) : [];
  const write: WriteKind = available.find((w) => w.write === sim.write)?.write ?? available[0]?.write ?? "create";
  const operations = target ? operationsFor(target, write) : [];
  const operation = operations.find((o) => o.operation === sim.operation) ?? operations[0];
  const root0 = target ? defaultRoot(target.class) : "";
  const draft: Draft = target ? draftOf(sim, target.id, root0) : { root: "", mode: "form", form: EMPTY_FORM, turtle: "" };
  const setDraft = (patch: Partial<Draft>) => target && setSim(workspace, (s) => ({ drafts: { ...s.drafts, [target.id]: { ...draftOf(s, target.id, root0), ...patch } } }));
  const spec: FormSpec | undefined = useMemo(() => (baselineGraph && target ? formSpec(baselineGraph, target.aggregate.rootShape, target.aggregate.rootClass) : undefined), [baselineGraph, target]);

  const needsObject = write === "create" || write === "replace";
  const object: Triples | undefined = !needsObject ? undefined : draft.mode === "form" ? (spec ? formTriples(spec, draft.form, draft.root) : { problem: "The baseline holds no boundary shape for this target, so there is no form. Give the object as Turtle." }) : turtleTriples(draft.turtle, draft.root);
  const stored = target ? positionOf(world, target, draft.root) : undefined;
  const another = sim.asAnotherWriter && write !== "create";
  const built = useMemo(() => {
    if (!target || !operation) return { problem: "There is no operation to run." };
    if (object && "problem" in object) return { problem: object.problem };
    return buildStep({ target, operation, root: draft.root, object: object?.lines ?? [], world, steps: sim.steps.length, time: sim.time, asAnotherWriter: another });
  }, [target, operation, draft.root, object, world, sim.steps.length, sim.time, another]);
  const size = worldSize(world);
  const overLimit = "trig" in built && built.bytes > REQUEST_LIMIT_BYTES;

  // What was sent, so that the result is read against the world it was built from and a step is recorded once.
  const sent = useRef<{ world: typeof world; record: Omit<StepRecord, "before" | "revision"> } | null>(null);
  const handled = useRef(0);
  const busy = state.phase === "running" || state.phase === "queued";
  const partsByRole = useMemo(() => {
    const parts = "parts" in state ? state.parts : [];
    return Object.fromEntries(parts.map((p) => [p.role, p.text])) as Record<string, string | undefined>;
  }, [state]);

  useEffect(() => {
    if (state.phase === "idle" || state.phase === "running" || state.phase === "queued") return;
    if (handled.current === state.number) return;
    handled.current = state.number;
    const was = sent.current;
    if (state.phase !== "complete" || !was) {
      setSim(workspace, { lit: [] });
      return;
    }
    const outcome = readOutcome(partsByRole.outcome);
    const delta: Delta | undefined = readDelta(partsByRole.delta);
    if (outcome?.outcome === "applied" && delta) {
      setSim(workspace, (s) => ({
        world: applyDelta(was.world, delta),
        steps: [...s.steps, { ...was.record, ...(outcome.revision ? { revision: outcome.revision } : {}), before: was.world }],
        lit: litOf(delta),
      }));
    } else setSim(workspace, { lit: delta ? litOf(delta) : [] });
  }, [state, partsByRole, workspace]);

  const run = () => {
    if (!controller || !target || !operation || !("trig" in built) || load.state !== "ready") return;
    sent.current = { world, record: { number: sim.steps.length + 1, write, operation: operation.operation, root: draft.root, time: sim.time } };
    setSim(workspace, { lit: [] });
    controller.start({ workspace, kind: "simulate", target: "persistence", job: jobId(load.job.iri), body: built.trig, mediaType: "application/trig" });
  };

  const fillFromWorld = () => {
    if (!spec || !target) return;
    const { data } = graphsOf(target, draft.root);
    const lines = aggregateLines(world, data, draft.root, target.aggregate.owned);
    if (lines.length > 0) setDraft({ mode: "form", form: formValues(spec, lines, draft.root), left: undefined });
  };

  const generate = () => {
    if (!spec) return;
    const made = generateObject(spec, draft.root, instancesIn(world));
    setDraft({ mode: "form", form: made.form, left: made.left });
  };

  const controls = (
    <>
      {load.state === "loading" && <p className="small muted">Reading the latest compilation.</p>}
      {load.state === "error" && <p className="small run-problem">{load.message}</p>}
      {(load.state === "none" || load.state === "refused" || load.state === "old") && (
        <p className="small">
          {load.state === "none" ? "The simulator runs the latest compilation of the persistence configuration, and there is none yet. Compile it on the canvas." : load.state === "refused" ? "The latest compilation was refused. Compile again once its findings are resolved." : "The latest compilation did not describe where data lands. Compile again."}
        </p>
      )}
      {load.state === "ready" && targets.length === 0 && <p className="small">The compilation has no operation a step runs.</p>}
      {load.state === "ready" && target && (
        <>
          <label className="sim-field">
            <span className="small muted">Target</span>
            <select className="select" aria-label="Simulator target" value={target.id} onChange={(e) => setSim(workspace, { target: e.target.value, operation: undefined })}>
              {targets.map((t) => (
                <option key={t.id} value={t.id}>
                  {targetLabel(t)}
                </option>
              ))}
            </select>
          </label>

          <div className="sim-world" role="group" aria-label="Sample world">
            <div className="small muted">Sample world</div>
            <div className="small" aria-label="Size of the sample world">
              {size.quads} {size.quads === 1 ? "quad" : "quads"}, {kib(size.bytes)} as TriG, {(size.fraction * 100).toFixed(size.fraction < 0.001 ? 3 : 1)}% of the {kib(REQUEST_LIMIT_BYTES)} request limit
            </div>
            <div className="small" aria-label="Steps in the sample world">
              {sim.steps.length} {sim.steps.length === 1 ? "step" : "steps"}
            </div>
            <button className="btn sm" disabled={sim.steps.length === 0 || busy} onClick={() => stepBack(workspace)}>
              <Undo2 size={13} /> Step back
            </button>
            {sim.steps.length > 0 && (
              <ol className="small sim-steps" aria-label="Steps taken">
                {sim.steps.map((s) => (
                  <li key={s.number}>
                    {s.operation} on {localName(s.root)}
                    {s.revision ? <span className="muted"> to {s.revision}</span> : null}
                  </li>
                ))}
              </ol>
            )}
          </div>

          <div className="sim-op" role="group" aria-label="Operation">
            <div className="small muted">Operation</div>
            <div className="mode-switch" role="group" aria-label="Write" style={{ margin: 0 }}>
              {WRITES.map((w) => (
                <button key={w.write} aria-pressed={write === w.write} disabled={!available.some((a) => a.write === w.write)} title={available.some((a) => a.write === w.write) ? undefined : `The compiled profile has no ${w.label.toLowerCase()} operation a step runs`} onClick={() => setSim(workspace, { write: w.write, operation: undefined })}>
                  {w.label}
                </button>
              ))}
            </div>
            {operations.length > 1 && (
              <select className="select" aria-label="Operation by name" value={operation?.operation} onChange={(e) => setSim(workspace, { operation: e.target.value })}>
                {operations.map((o) => (
                  <option key={o.operation} value={o.operation}>
                    {o.operation}, {o.kind}
                  </option>
                ))}
              </select>
            )}
            {operation && <div className="small muted mono">{operation.templateId}</div>}
          </div>

          <div className="sim-object" role="group" aria-label="Object">
            <div className="small muted">Object</div>
            <label className="sim-field">
              <span className="small">root</span>
              <input className="input mono" aria-label="Root" value={draft.root} onChange={(e) => setDraft({ root: e.target.value })} />
            </label>
            {needsObject && (
              <>
                <div className="mode-switch" role="group" aria-label="Object source" style={{ margin: 0 }}>
                  <button aria-pressed={draft.mode === "form"} onClick={() => setDraft({ mode: "form" })}>
                    Form
                  </button>
                  <button aria-pressed={draft.mode === "turtle"} onClick={() => setDraft({ mode: "turtle" })}>
                    Turtle
                  </button>
                </div>
                {draft.mode === "form" && spec && (
                  <div className="sim-form">
                    {spec.fields.map((f) => (
                      <FieldInput key={f.path} field={f} value={draft.form.fields[f.path] ?? ""} onChange={(v) => setDraft({ form: { ...draft.form, fields: { ...draft.form.fields, [f.path]: v } } as FormValues })} />
                    ))}
                    <OwnedForm specs={spec.owned} values={draft.form.owned} parent={draft.root} onChange={(owned) => setDraft({ form: { ...draft.form, owned } })} />
                    <div className="row" style={{ gap: 6 }}>
                      <button className="btn sm" onClick={generate} title="Fill the form with the small object the boundary shape requires">
                        Generate from the shape
                      </button>
                      <button className="btn sm" disabled={stored === undefined} onClick={fillFromWorld}>
                        Fill from the sample world
                      </button>
                    </div>
                    {draft.left !== undefined && (
                      <div className="small" role="status" aria-label="Left for the author">
                        {draft.left.length === 0 ? (
                          <p className="muted">The shape's requirements are all met. Change anything before Run.</p>
                        ) : (
                          <>
                            <p className="muted">The shape requires these, and they are left for you.</p>
                            <ul className="sim-list">
                              {draft.left.map((l) => (
                                <li key={l}>{l}</li>
                              ))}
                            </ul>
                          </>
                        )}
                      </div>
                    )}
                  </div>
                )}
                {draft.mode === "form" && !spec && <p className="small muted">The baseline holds no boundary shape for this target. Give the object as Turtle.</p>}
                {draft.mode === "turtle" && (
                  <div className="sim-turtle">
                    <textarea className="input mono" rows={8} aria-label="Object as Turtle" value={draft.turtle} placeholder="Turtle with a prefix declared for each name" onChange={(e) => setDraft({ turtle: e.target.value })} />
                    <label className="btn sm">
                      Open a Turtle file
                      <input
                        type="file"
                        accept=".ttl,text/turtle"
                        hidden
                        aria-label="Object file"
                        onChange={async (e) => {
                          const files = e.target.files;
                          if (files?.length) setDraft({ turtle: (await readFiles(files))[0].text });
                          e.target.value = "";
                        }}
                      />
                    </label>
                  </div>
                )}
              </>
            )}
          </div>

          <label className="sim-field">
            <span className="small">transaction time</span>
            <input className="input mono" aria-label="Transaction time" value={sim.time} aria-invalid={!TIME.test(sim.time)} onChange={(e) => setSim(workspace, { time: e.target.value })} />
          </label>
          <label className="row small" style={{ gap: 6 }}>
            <input type="checkbox" checked={sim.asAnotherWriter} disabled={write === "create"} onChange={(e) => setSim(workspace, { asAnotherWriter: e.target.checked })} />
            As another writer
          </label>
          {another && "trig" in built && <p className="small muted">The step is sent from position {Number(built.parameters.expectedSeq)}, one before the sample world's, so the guard refuses it.</p>}

          {"problem" in built && (
            <p className="small run-problem" role="alert">
              {built.problem}
            </p>
          )}
          {overLimit && (
            <p className="small run-problem" role="alert">
              The request is over the {kib(REQUEST_LIMIT_BYTES)} the service takes. Step back to make the sample world smaller.
            </p>
          )}
          {"trig" in built && (
            <div className="small muted" aria-label="Size of the step">
              The step is {kib(built.bytes)} with the world.
            </div>
          )}
          <button className="btn primary sm" disabled={!controller || busy || !("trig" in built) || overLimit} onClick={run}>
            {busy ? <Spinner size={12} /> : <Play size={13} />} Run
          </button>
          <button className="btn sm ghost" onClick={() => setRefresh((n) => n + 1)} title="Read the latest compilation again">
            <RotateCcw size={13} /> Read the compilation again
          </button>
          <details className="sim-raw">
            <summary className="small muted">The sample world as TriG</summary>
            <OutputExplorer part={{ mediaType: "application/trig", text: worldTrig(world) || "# The sample world is empty.", role: "world" }} />
          </details>
        </>
      )}
    </>
  );

  return <RunPane title="Simulator" className="simulator" controls={controls} state={state} onRunAgain={run} display={(parts) => <Displays parts={parts} doc={doc} />} />;
}
