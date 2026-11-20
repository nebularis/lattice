// SPDX-License-Identifier: MPL-2.0
// The run pane (SVA-R4, ADR-A154): a shell for the right-hand dock that every mode's runs use. The controls are on the left and the displays on
// the right, a status line and each part of the result, which the output explorer (SVA-M4) shows in the renderings its media type allows.

import { createContext, useCallback, useContext, useEffect, useMemo, useState, useSyncExternalStore, type ReactNode } from "react";
import { Download, Play, RotateCcw } from "lucide-react";
import { Graph, PREFIXES, compact } from "@lattice/authoring-domain";
import { api, awaitJob, jobId } from "../api";
import { onRunFrame, connected, tabId } from "../events";
import { SAMPLE_FORMATS, exampleSources, schemesOf, type SampleFormat } from "../rdf/mapping";
import { createRunController, pageClock, pageTimers, type RunController, type RunPart, type RunState } from "../runs";
import { finished } from "../rdf/report";
import { IDLE_SAMPLE, createSampleSession, engineOf, schemeReading, type SampleSession, type SampleState } from "../sample";
import { OutputExplorer } from "./OutputExplorer";
import { Spinner, download, go } from "./kit";
import { useStudio } from "./Workspace";

/** The sample session of the workspace, which mapping mode's pane and view share. Undefined until the workspace has made it. */
export const SampleContext = createContext<SampleSession | undefined>(undefined);

/** The browser's storage, which keeps the sample a workspace was last given. A browser that keeps nothing still runs the sample for this visit. */
const browserStorage = {
  get(key: string): string | undefined {
    try {
      return localStorage.getItem(key) ?? undefined;
    } catch {
      return undefined;
    }
  },
  set(key: string, value?: string): void {
    try {
      if (value) localStorage.setItem(key, value);
      else localStorage.removeItem(key);
    } catch {
      // The sample is kept for this visit only.
    }
  },
};

/** One sample session a workspace, made when it opens and ended when it closes, over the studio's own service. */
export function useSampleSession(workspace: string): SampleSession | undefined {
  const [session, setSession] = useState<SampleSession>();
  useEffect(() => {
    const made = createSampleSession({
      workspace,
      async compile(graph) {
        const id = await api.submit(workspace, "compile", "mapping", graph);
        const done = await awaitJob(id);
        if (done.status === "Failed") throw new Error(done.failure ?? "The compilation failed.");
        return { job: id, artefacts: done.artefacts };
      },
      async latest() {
        const row = (await api.compileJobs(workspace)).find((j) => j.target === "Mapping" && finished(j) && j.status === "Succeeded");
        if (!row) return undefined;
        const job = await awaitJob(jobId(row.iri));
        return job.status === "Succeeded" ? { job: jobId(row.iri), artefacts: job.artefacts } : undefined;
      },
      forget: (job) => void api.deleteJob(job).catch(() => undefined),
      controller: createRunController({ api, events: { connected, onRunFrame, tabId }, clock: pageClock, timers: pageTimers }),
      storage: browserStorage,
    });
    setSession(made);
    return () => made.dispose();
  }, [workspace]);
  return session;
}

/** The workspace's sample session and its state, or the state of one that has no sample yet. */
export function useSample(): { session?: SampleSession; state: SampleState } {
  const session = useContext(SampleContext);
  const subscribe = useCallback((listener: () => void) => (session ? session.subscribe(listener) : () => undefined), [session]);
  const state = useSyncExternalStore(subscribe, () => session?.getState() ?? IDLE_SAMPLE);
  return { session, state };
}

const IDLE: RunState = { phase: "idle" };

/** A controller for the pane, made when it mounts and disposed when it goes, with its state. */
export function useRunController(): { controller?: RunController; state: RunState } {
  const [controller, setController] = useState<RunController>();
  useEffect(() => {
    const made = createRunController({ api, events: { connected, onRunFrame, tabId }, clock: pageClock, timers: pageTimers });
    setController(made);
    return () => made.dispose();
  }, []);
  const subscribe = useCallback((listener: () => void) => (controller ? controller.subscribe(listener) : () => undefined), [controller]);
  const state = useSyncExternalStore(subscribe, () => controller?.getState() ?? IDLE);
  return { controller, state };
}

function PartBlock({ part }: { part: RunPart }) {
  const where = [part.path, part.group && part.group !== part.path ? part.group : undefined].filter(Boolean).join(" in ");
  return (
    <section className="run-part" aria-label={`Part ${part.index + 1}, ${part.role}`}>
      <div className="run-part-head">
        <strong>{part.role}</strong>
        {part.step !== undefined && <span className="muted"> step {part.step}</span>}
        {where && <div className="small run-part-where">{where}</div>}
        <div className="small muted">{part.mediaType}</div>
      </div>
      <OutputExplorer part={part} />
    </section>
  );
}

/** One line for the state. */
function statusText(state: RunState): string {
  switch (state.phase) {
    case "idle":
      return "Nothing has run yet.";
    case "queued":
      return "Queued behind the run in progress.";
    case "running":
      return `Running, ${state.parts.length} ${state.parts.length === 1 ? "part" : "parts"} so far.`;
    case "complete":
      return `Complete, ${state.parts.length} ${state.parts.length === 1 ? "part" : "parts"}${state.conforms === undefined ? "" : state.conforms ? ", conforms" : ", does not conform"}.`;
    case "failed":
      return `Failed. ${state.message}${state.partial ? " Frames were missing, so the parts shown are only those that arrived whole, as partial output." : ""}`;
    case "incomplete": {
      const gaps = state.missing.length ? `Frames ${state.missing.join(", ")} did not arrive.` : `The last frame did not arrive, after frame ${state.next - 1}.`;
      return `Incomplete, the run did not finish before its deadline. ${state.received} ${state.received === 1 ? "frame" : "frames"} arrived. ${gaps}${state.message ? ` The service said: ${state.message}` : ""}`;
    }
    case "refused":
      return `Refused${state.status ? ` (${state.status})` : ""}. ${state.message}${state.retryAfter ? ` Try again in ${state.retryAfter} seconds.` : ""}`;
  }
}

export function RunPane({ title, controls, state, onRunAgain, display, above, className }: { title: string; controls: ReactNode; state: RunState; onRunAgain?: () => void; display?: (parts: RunPart[]) => ReactNode; above?: ReactNode; className?: string }) {
  const parts = "parts" in state ? state.parts : [];
  const busy = state.phase === "running" || state.phase === "queued";
  return (
    <section className={`run-pane${className ? ` ${className}` : ""}`} aria-label={title}>
      <div className="run-controls" role="group" aria-label={`${title} controls`}>
        {controls}
      </div>
      <div className="run-display">
        <div className={`run-status ${state.phase}`} role="status" aria-label={`${title} status`} data-phase={state.phase}>
          {busy && <Spinner size={12} />} {statusText(state)}
          {state.phase !== "idle" && <div className="small muted">Compile job {jobId(state.job)}</div>}
          {state.phase === "incomplete" && onRunAgain && (
            <div>
              <button className="btn sm" onClick={onRunAgain}>
                <RotateCcw size={13} /> Run again
              </button>
            </div>
          )}
        </div>
        {above}
        {display ? (
          display(parts)
        ) : (
          <div className="run-parts" role="list" aria-label={`${title} parts`}>
            {parts.map((p) => (
              <div role="listitem" key={p.index}>
                <PartBlock part={p} />
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

/** The dock's Sample tab for mapping mode (sketch 10.3): the scheme, the form it was compiled to, the sample and Run on the left, and the run on the right. Nothing runs until Run is pressed. */
export function SamplePane() {
  const { session, state } = useSample();
  const studio = useStudio();
  const [draft, setDraft] = useState(state.sample ?? "");
  useEffect(() => setDraft(state.sample ?? ""), [state.sample]);
  useEffect(() => void session?.refresh(), [session]);
  const schemes = useMemo(() => (state.graph ? schemesOf(state.graph) : []), [state.graph]);
  const examples = useMemo(() => (state.graph ? exampleSources(state.graph) : []), [state.graph]);
  const label = schemes.find((s) => s.iri === state.scheme)?.label;
  const prefixes = useMemo(() => ({ ...PREFIXES, ...state.graph?.prefixes }), [state.graph]);
  const format = SAMPLE_FORMATS.find(([f]) => f === state.format)![1];
  const run = state.run;
  const complete = run.phase === "complete";
  const engine = complete ? engineOf(run.parts, Graph.parse) : undefined;
  const load = async (file?: File) => file && session?.setSample(await file.text(), file.name);
  const applyExample = (e: (typeof examples)[number]) => {
    session?.setSample(e.text);
    session?.setFormat(e.format);
    // The example belongs to the scheme that reads its source, so that scheme is the one the pane runs.
    const scheme = state.graph && schemeReading(state.graph, e.scheme);
    if (scheme) {
      session?.setScheme(scheme);
      go("w", studio.id, "mapping");
    }
  };
  const controls = (
    <>
      <div className="sample-field">
        <div className="muted small">Scheme</div>
        <div>{label ?? "None"}</div>
        {state.scheme && <div className="small mono sample-form-path">{compact(state.scheme, prefixes)}</div>}
        {state.libraries.length > 0 && (
          <ul className="small sample-libraries" aria-label="Template libraries">
            {state.libraries.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        )}
      </div>
      <fieldset className="sample-field sample-forms" aria-label="Compiled form">
        <legend className="muted small">Compiled form</legend>
        {!state.compilation && <div className="small muted">Not compiled yet. Run compiles the scheme first.</div>}
        {state.compilation && state.forms.length === 0 && <div className="small muted">The last compilation wrote no form for this scheme.</div>}
        {state.forms.map((f) => (
          <div key={f.kind + f.path} className="sample-form">
            <label className="row" style={{ gap: 6 }}>
              <input type="radio" name="sample-form" checked={state.form?.kind === f.kind} onChange={() => session?.chooseForm(f.kind)} aria-label={f.label} />
              <span>{f.label}</span>
            </label>
            <div className="small mono sample-form-path">{f.path}</div>
            <div className="small">
              <span className={`chip ${f.runtime ? "ok" : "warn"}`}>{f.runtime ? "Runs here" : "No runtime yet"}</span>
              <button className="btn ghost sm" aria-label={`Download ${f.path}`} onClick={() => download(f.path, f.content, f.mediaType)}>
                <Download size={13} />
              </button>
            </div>
          </div>
        ))}
        {state.compilation && !state.compilationCurrent && <div className="small muted">The scheme may have changed since this compilation. Run compiles it again.</div>}
      </fieldset>
      <div className="sample-field">
        <div className="muted small">Sample</div>
        <textarea
          className="mono small"
          rows={5}
          value={draft}
          placeholder="Paste a source in Turtle, XML or JSON to run the mappings over it"
          aria-label={`Sample source in ${format}`}
          onChange={(e) => {
            setDraft(e.target.value);
            session?.setSample(e.target.value || undefined);
          }}
        />
        <div className="row" style={{ gap: 6, flexWrap: "wrap" }}>
          <select className="sm" aria-label="Sample format" value={state.format} onChange={(e) => session?.setFormat(e.target.value as SampleFormat)}>
            {SAMPLE_FORMATS.map(([f, name]) => (
              <option key={f} value={f}>
                {name}
              </option>
            ))}
          </select>
          <label className="btn sm">
            Load a file
            <input type="file" accept=".ttl,.nt,.xml,.json" hidden onChange={(e) => void load(e.target.files?.[0])} />
          </label>
          {state.sample && (
            <button className="btn sm ghost" onClick={() => session?.setSample(undefined)}>
              Clear
            </button>
          )}
        </div>
        {!state.sample &&
          examples.map((e) => (
            <button key={e.scheme} className="btn sm ghost" title={`The example source of ${e.scheme}`} onClick={() => applyExample(e)}>
              Use the {SAMPLE_FORMATS.find(([f]) => f === e.format)![1]} example
            </button>
          ))}
      </div>
      <button className="btn primary sm" disabled={!state.canRun} title={state.blocked} onClick={() => void session?.run()}>
        {state.preparing ? <Spinner size={12} /> : <Play size={13} />} Run
      </button>
      {state.blocked && state.sample?.trim() && (
        <div className="small sample-blocked" role="note" aria-label="Why Run is off">
          {state.blocked}
        </div>
      )}
      {state.note && !state.blocked && (
        <div className="small muted" role="note" aria-label="About this run">
          {state.note}
        </div>
      )}
      {state.problem && (
        <div className="small run-problem" role="alert">
          {state.problem}
        </div>
      )}
    </>
  );
  const above = (
    <>
      {state.preparing && <div className="small muted">Compiling the scheme, then running.</div>}
      {engine && <div className="small run-engine">Evaluated by {engine}.</div>}
      {complete && state.stale && (
        <div className="small run-note" role="note" aria-label="Out of date">
          The scheme, another part or the sample has changed since this run. The counts on the canvas and the tree are out of date until you run again.
        </div>
      )}
    </>
  );
  return <RunPane title="Sample" className="sample" controls={controls} state={state.run} onRunAgain={() => void session?.run()} above={above} />;
}
