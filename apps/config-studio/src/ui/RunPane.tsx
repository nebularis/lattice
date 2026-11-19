// SPDX-License-Identifier: MPL-2.0
// The run pane (SVA-R4, ADR-A154): a shell for the right-hand dock that every mode's runs use. The controls are on the left and the displays on
// the right, a status line and each part of the result, which the output explorer (SVA-M4) shows in the renderings its media type allows.

import { createContext, useCallback, useContext, useEffect, useState, useSyncExternalStore, type ReactNode } from "react";
import { Play, RotateCcw } from "lucide-react";
import { api, jobId } from "../api";
import { onRunFrame, connected, tabId } from "../events";
import { createRunController, pageClock, pageTimers, type RunController, type RunPart, type RunState } from "../runs";
import { OutputExplorer } from "./OutputExplorer";
import { Spinner } from "./kit";

/** What the mapping view keeps for the pane to run: the sample, its media type, and a way to find or make the compilation of the part as it is. */
export interface RunSource {
  workspace: string;
  scheme?: string;
  sample?: string;
  mediaType: string;
  ensureCompiled: () => Promise<string>;
}

interface RunSourceHolder {
  source?: RunSource;
  set: (source?: RunSource) => void;
}

export const RunSourceContext = createContext<RunSourceHolder | null>(null);

/** Where a view says what the pane may run. Null outside a workspace. */
export function useRunSource(): RunSourceHolder | null {
  return useContext(RunSourceContext);
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

export function RunPane({ title, controls, state, onRunAgain, display, className }: { title: string; controls: ReactNode; state: RunState; onRunAgain?: () => void; display?: (parts: RunPart[]) => ReactNode; className?: string }) {
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

/** The dock's Sample tab for mapping mode: which scheme and sample it runs, and Run. Nothing runs until Run is pressed. */
export function SamplePane() {
  const holder = useRunSource();
  const source = holder?.source;
  const { controller, state } = useRunController();
  const [preparing, setPreparing] = useState(false);
  const [problem, setProblem] = useState<string>();
  const run = async () => {
    if (!source?.sample?.trim() || !controller) return;
    setProblem(undefined);
    setPreparing(true);
    try {
      const job = await source.ensureCompiled();
      controller.start({ workspace: source.workspace, kind: "sample", target: "mapping", job, body: source.sample, mediaType: source.mediaType });
    } catch (error) {
      setProblem(error instanceof Error ? error.message : String(error));
    } finally {
      setPreparing(false);
    }
  };
  const format = source?.mediaType === "application/xml" ? "XML" : source?.mediaType === "application/json" ? "JSON" : "Turtle";
  const controls = (
    <>
      <div className="small">
        <div className="muted">Scheme</div>
        <div>{source?.scheme ?? "None"}</div>
      </div>
      <div className="small">
        <div className="muted">Sample</div>
        <div>{source?.sample?.trim() ? `${format}, ${source.sample.length.toLocaleString()} characters` : "None yet"}</div>
      </div>
      <button className="btn primary sm" disabled={!source?.sample?.trim() || !controller || preparing} onClick={() => void run()}>
        {preparing ? <Spinner size={12} /> : <Play size={13} />} Run
      </button>
      {problem && (
        <div className="small run-problem" role="alert">
          {problem}
        </div>
      )}
    </>
  );
  return <RunPane title="Sample" controls={controls} state={state} onRunAgain={() => void run()} />;
}
